"""DiagnosisService V2 —— 事实/观察/候选三段判定（FE-1406，评审 V0.2 §4）。

与 V1 的核心差异（评审点名）：
1. **移除无证据兜底**：V1 的 `_fallback_by_hints`（按 hint 依赖度猜 E01/E05）删除；
2. **移除"第一条错因"推断**：V1 `error_models[0]` 直取删除——资源错因规则只是候选来源，
   没有观察证据指向时不得选码；
3. **NULL 是合法结果**：top_level_code 可为 None（证据不足），不得写 0 置信度冒充已判断；
4. **correct=None（未评分）不判**：评分故障走工程异常，不写儿童数学误解；
5. **单题只到 candidate**：confirmed 需跨资源跨 session 聚合 + 反例排除——判定条件本身
   是评审 §6 的 OPEN 校准项，V2.0 不启用（status 枚举保留 confirmed 值位）。

三层模型（评审 §4.1）：
- 评分事实：correct（本服务只消费，不产出）
- 诊断观察 observations：局部可验证异常 + field_path
- 误解候选 candidates：tag + E01~E07 映射 + rule_id/rule_version/evidence_paths

E01~E07 顶层语义沿用冻结码表；LE-* 接口错误与教育码永不混用。
tag→观察匹配表与标签字典为保守缺省，正式版待内容/教学规则/后端共同审定进 ADR。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.education_rules import DIAGNOSIS_LABELS

DIAGNOSIS_VERSION = "diagnosis-v2"

# 资源侧 error_model tag → 顶层 E 码（候选分类缺省映射；沿用 V1 口径）
_TAG_TO_TOP_CODE = {
    "calc": "E06",
    "calculation": "E06",
    "strategy": "E05",
    "modeling": "E04",
    "math_lang": "E03",
    "reading": "E02",
    "check": "E07",
    "knowledge": "E01",
}

# 观察 code → 可支持的资源 tag（只有观察命中规则触发条件才形成候选；保守表）
_OBSERVATION_SUPPORTS_TAG = {
    "representation_missing": {"modeling"},
    "no_process_data": {"modeling", "strategy"},
}

# 面向儿童/家长的中性文案（top_level_code=None 时使用）
INSUFFICIENT_EVIDENCE_LABEL = "还在收集更多信息，暂时不下结论"


@dataclass
class Observation:
    code: str
    field_path: str
    detail: dict | None = None

    def to_dict(self) -> dict:
        out = {"code": self.code, "field_path": self.field_path}
        if self.detail:
            out["detail"] = self.detail
        return out


@dataclass
class Candidate:
    tag: str
    top_level_code: str
    rule_id: str
    rule_version: str
    evidence_paths: list[str]

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "top_level_code": self.top_level_code,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "evidence_paths": self.evidence_paths,
        }


@dataclass
class DiagnosisV2:
    """三段判定结果。top_level_code=None 表示证据不足（合法结论，非失败）。"""

    status: str  # observation_only | candidate | confirmed（confirmed 未启用）
    top_level_code: str | None
    label: str | None
    observations: list[Observation] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    process_evidence_status: str = "missing"  # complete | partial | missing
    diagnosis_version: str = DIAGNOSIS_VERSION

    def to_dict(self) -> dict:
        return {
            "diagnosis_version": self.diagnosis_version,
            "status": self.status,
            "top_level_code": self.top_level_code,
            "label": self.label,
            "observations": [o.to_dict() for o in self.observations],
            "candidates": [c.to_dict() for c in self.candidates],
            "process_evidence_status": self.process_evidence_status,
        }

    @property
    def v1_compat(self) -> dict:
        """V1 兼容外形（版本分流，评审 §4.1"V1/C 域既有响应保持兼容"）。

        关键：top_level_code=None 时 confidence 也是 None——不得用 0 冒充已判断。"""
        single = self.candidates[0] if len(self.candidates) == 1 and self.top_level_code else None
        return {
            "code": self.top_level_code,  # 可为 None（NULL 是合法诊断结果）
            "label": self.label,
            "confidence": 0.5 if single else None,
            "evidence_scope": "attempt_only",
        }


# ---- 观察提取（只记录可验证的局部事实，不猜原因）----

def extract_observations(
    *,
    correct: bool | None,
    response: dict,
    ui_schema: dict | None,
) -> list[Observation]:
    obs: list[Observation] = []
    if correct is not False:  # 只有"答错"才有异常观察
        return obs

    ui = ui_schema if isinstance(ui_schema, dict) else {}

    # V1 资源：representation_required 但未提交表征 → 建模观察
    resp_schema = ui.get("response_schema") if isinstance(ui.get("response_schema"), dict) else {}
    if resp_schema.get("representation_required") and not response.get("representation"):
        obs.append(Observation("representation_missing", "response.representation"))

    # V2 资源：workspaces 存在但 data 全空 → 无过程数据观察
    workspaces = response.get("workspaces")
    if isinstance(workspaces, list) and workspaces:
        if all(not (w.get("data") if isinstance(w, dict) else None) for w in workspaces):
            obs.append(Observation("no_process_data", "response.workspaces"))

    return obs


def _process_evidence_status(observations: list[Observation], response: dict) -> str:
    if observations:
        return "partial"
    if response.get("representation") or response.get("workspaces"):
        return "complete"
    return "missing"


# ---- 主入口 ----

def diagnose_v2(
    correct: bool | None,
    *,
    error_models: list | None = None,
    response: dict | None = None,
    ui_schema: dict | None = None,
    resource_version_id: str | None = None,
) -> DiagnosisV2 | None:
    """产出三段判定；答对或未评分返回 None（不产生误解记录）。

    - correct=None：评分不可用 = 工程异常场景，不写儿童数学误解（交调用方记工程日志）。
    - 答错但无观察支持任何资源规则 → candidates 空、top_level_code=None。
    """
    if correct is not False:
        return None

    response = response or {}
    observations = extract_observations(correct=correct, response=response, ui_schema=ui_schema)

    candidates: list[Candidate] = []
    obs_codes = {o.code for o in observations}
    for em in error_models or []:
        tag = (em.get("code") if isinstance(em, dict) else em) or ""
        tag = str(tag).strip().lower()
        if not tag:
            continue
        supported_by = {code for code, tags in _OBSERVATION_SUPPORTS_TAG.items() if tag in tags}
        hit = obs_codes & supported_by
        if not hit:
            continue  # 无观察支持：该资源规则不形成候选（"第一条错因"推断已移除）
        top = _TAG_TO_TOP_CODE.get(tag)
        if not top:
            continue
        candidates.append(
            Candidate(
                tag=tag,
                top_level_code=top,
                rule_id=f"{resource_version_id or 'resource'}:{tag}",
                rule_version=DIAGNOSIS_VERSION,
                evidence_paths=sorted({o.field_path for o in observations if o.code in hit}),
            )
        )

    # top_level_code：恰好一个候选才允许选码；多候选=仍有合理解释，保持 NULL
    unique_tops = {c.top_level_code for c in candidates}
    top_code = candidates[0].top_level_code if len(candidates) == 1 and len(unique_tops) == 1 else None

    return DiagnosisV2(
        status="candidate" if candidates else "observation_only",
        top_level_code=top_code,
        label=DIAGNOSIS_LABELS.get(top_code) if top_code else INSUFFICIENT_EVIDENCE_LABEL,
        observations=observations,
        candidates=candidates,
        process_evidence_status=_process_evidence_status(observations, response),
    )


# ---- 兼容层 ----

def diagnose(
    correct: bool | None,
    *,
    error_model: str | None = None,
    used_hint_levels: list[int] | None = None,
    repeated_pattern: bool = False,
) -> DiagnosisV2 | None:
    """旧签名适配（/v1/diagnosis 独立端点用）。hint 依赖不再决定错因（兜底已移除）。"""
    return diagnose_v2(
        correct,
        error_models=[{"code": error_model}] if error_model else None,
    )


# ---- HTTP 响应外形（版本分流：V2 完整记录进 event，对外只暴露有码结论）----

def response_shape(d: "DiagnosisV2 | None") -> dict | None:
    """对外 diagnosis 字段：仅当 top_level_code 非 NULL 时给出标签。

    评审 §4.1：证据不足是合法结果——对儿童不展示猜测性错因标签（diagnosis=None），
    但 LearningEvent 内保留完整三段判定供审计与后续 confirmed 聚合。"""
    if d is None or d.top_level_code is None:
        return None
    return {
        "code": d.top_level_code,
        "label": d.label,
        "confidence": 0.5,
        "evidence_scope": "attempt_only",
        "status": d.status,
    }


def response_shape_from_dict(diag: dict | None) -> dict | None:
    """幂等重放路径：从 event payload 的 V2 完整 dict 还原对外外形。"""
    if not isinstance(diag, dict) or not diag.get("top_level_code"):
        return None
    return {
        "code": diag["top_level_code"],
        "label": diag.get("label"),
        "confidence": 0.5,
        "evidence_scope": "attempt_only",
        "status": diag.get("status"),
    }
