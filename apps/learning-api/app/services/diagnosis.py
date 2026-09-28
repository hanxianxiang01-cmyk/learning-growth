"""DiagnosisService V1 —— 规则引擎，产出 E01~E07 教育诊断（HTTP 2xx 业务载荷）。

E01~E07 是教育诊断码，绝不作为系统错误码返回（见冻结基线第 7 节）。
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.education_rules import DIAGNOSIS_LABELS

# 诊断码 → 触发规则（V1 规则引擎，MVP 初步规则，后续接 E4 能力图谱细化）
_DIAGNOSIS_RULES: dict[str, str] = {
    "E01": "knowledge_gap",
    "E02": "reading_comprehension_gap",
    "E03": "math_language_gap",
    "E04": "modeling_gap",
    "E05": "strategy_selection_gap",
    "E06": "calculation_error",
    "E07": "checking_validation_gap",
}


@dataclass
class Diagnosis:
    code: str
    label: str
    confidence: float
    evidence_scope: str  # attempt_only | repeated_pattern

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "evidence_scope": self.evidence_scope,
        }


def diagnose(
    correct: bool | None,
    *,
    error_model: str | None = None,
    used_hint_levels: list[int] | None = None,
    repeated_pattern: bool = False,
) -> Diagnosis | None:
    """根据作答结果 + 错误模型 + hint 使用情况，产出诊断。

    - correct=True 且无需诊断时返回 None。
    - error_model 是资源侧标注的错误类别（如 calc/strategy/modeling），映射到 E 码。
    - 若无 error_model，按 hint 依赖度给策略性诊断兜底。
    """
    if correct is True:
        return None

    code = _map_error_model(error_model) or _fallback_by_hints(used_hint_levels or [])

    return Diagnosis(
        code=code,
        label=DIAGNOSIS_LABELS[code],
        confidence=0.7 if not repeated_pattern else 0.9,
        evidence_scope="repeated_pattern" if repeated_pattern else "attempt_only",
    )


def _map_error_model(error_model: str | None) -> str | None:
    """资源侧错误模型 → 诊断码（MVP 映射表）。"""
    if not error_model:
        return None
    m = error_model.strip().lower()
    mapping = {
        "calc": "E06",
        "calculation": "E06",
        "strategy": "E05",
        "modeling": "E04",
        "math_lang": "E03",
        "reading": "E02",
        "check": "E07",
        "knowledge": "E01",
    }
    return mapping.get(m)


def _fallback_by_hints(used_hint_levels: list[int]) -> str:
    """无 error_model 时，按 hint 依赖度兜底：高依赖→策略选择类，否则知识缺口。"""
    if not used_hint_levels:
        return "E01"
    if max(used_hint_levels) >= 3:
        return "E05"
    return "E01"