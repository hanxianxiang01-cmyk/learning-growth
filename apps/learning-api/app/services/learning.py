"""Learning 编排服务 —— 严格对齐冻结 OpenAPI /v1/learning/* 接口。

接口签名以 02_openapi_v1.3.1.yaml 为准（前后端对齐评审 V1.0）：
- sessions：body {child_id, subject, requested_minutes?, plan_id?}
- tasks/next：body {child_id, session_id, subject, requested_minutes?}（无 ability_id，后端自选）
- attempts：body {task_instance_id, attempt_no, response, ...}（无 child_id，后端反查）
- hints：body {attempt_id, requested_level?}（attempt → 反查 task → 反查资源 hint_policy）
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AbilityState,
    Attempt,
    LearningPlan,
    LearningSession,
    Resource,
    ResourceVersion,
    TaskInstance,
)
from app.core.education_rules import SESSION_TASK_GOAL
from app.services.fitband import compute_fit_band
from app.services.turn_service import record_attempt


async def start_session(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    subject: str,
    requested_minutes: int | None = None,
    plan_id: uuid.UUID | None = None,
) -> dict:
    """创建 learning_session，返回 OpenAPI 201 结构。"""
    session = LearningSession(
        child_id=child_id,
        subject=subject,
        plan_id=plan_id,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {
        "session_id": session.session_id,
        "status": session.status,
        "plan_id": session.plan_id,
    }


async def _candidate_abilities(
    db: AsyncSession, *, child_id: uuid.UUID, session_id: uuid.UUID
) -> list[str]:
    """候选能力列表（有序）：优先 plan.target，兜底 child 按 level 升序的能力。"""
    session = await db.get(LearningSession, session_id)
    if session and session.plan_id:
        plan = await db.get(LearningPlan, session.plan_id)
        if plan and plan.target_ability_ids:
            return [aid for aid in plan.target_ability_ids]

    result = await db.execute(
        select(AbilityState.ability_id)
        .where(AbilityState.child_id == child_id)
        .order_by(AbilityState.level.asc(), AbilityState.confidence.asc())
    )
    return [row[0] for row in result.all()]


async def _pick_ability(db: AsyncSession, *, child_id: uuid.UUID, session_id: uuid.UUID) -> str | None:
    """从候选能力里选「有已发布资源」的第一个（不考虑难度带，仅保证有题）。"""
    candidates = await _candidate_abilities(db, child_id=child_id, session_id=session_id)
    for aid in candidates:
        has_published = (
            await db.execute(
                select(ResourceVersion.resource_version_id)
                .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
                .where(
                    Resource.ability_id == aid,
                    ResourceVersion.review_status == "published",
                )
                .limit(1)
            )
        ).first()
        if has_published:
            return aid
    return None


def _v2_assignable(ui_schema: object) -> bool:
    """V2 下发门控（FE-1404 §2 / 评审 §3.1 红线）：

    - V1（或缺 schema_version）资源不受影响；
    - V2 资源的主 workspace renderer 必须已 implemented，planned 受控拒绝（不降级）；
    - 协议外 renderer 同样拒绝下发。
    """
    if not isinstance(ui_schema, dict) or ui_schema.get("schema_version") != "2.0":
        return True
    from app.content.renderer_protocol import is_implemented, validate_renderer_id

    try:
        for ws in ui_schema.get("workspaces", []):
            rid = ws.get("renderer") if isinstance(ws, dict) else None
            if rid is None:
                return False
            validate_renderer_id(rid)
            if not is_implemented(rid):
                return False
    except ValueError:
        return False
    return True


async def _published_resource_for_ability(
    db: AsyncSession,
    *,
    ability_id: str,
    band_min: int,
    band_max: int,
    fallback_to_lowest: bool,
    exclude_resource_version_ids: set | None = None,
) -> ResourceVersion | None:
    """取某能力「fit_band 内」的已发布资源；带内无题且 fallback_to_lowest 时，
    退到该能力「最低难度」已发布资源（保证指定能力一定有题可练）。

    exclude_resource_version_ids：本 session 已出过的题，取下一题时排除，
    避免「答对后点下一题仍是同一道题」。

    V2 门控：planned renderer 的 V2 资源不可下发（多取候选后在应用层过滤）。"""
    exclude = exclude_resource_version_ids or set()
    base_where = [
        Resource.ability_id == ability_id,
        ResourceVersion.review_status == "published",
    ]
    if exclude:
        base_where.append(ResourceVersion.resource_version_id.notin_(exclude))

    async def _first_assignable(stmt) -> ResourceVersion | None:
        rows = (await db.execute(stmt.limit(50))).scalars().all()
        return next((rv for rv in rows if _v2_assignable(rv.ui_schema)), None)

    row = await _first_assignable(
        select(ResourceVersion)
        .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
        .where(
            *base_where,
            ResourceVersion.difficulty >= band_min,
            ResourceVersion.difficulty <= band_max,
        )
        .order_by(ResourceVersion.difficulty.asc(), ResourceVersion.created_at.asc())
    )
    if row is not None or not fallback_to_lowest:
        return row

    return await _first_assignable(
        select(ResourceVersion)
        .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
        .where(*base_where)
        .order_by(ResourceVersion.difficulty.asc(), ResourceVersion.created_at.asc())
    )


async def list_v2_catalog(db: AsyncSession) -> list[dict]:
    """published 且 V2-assignable 的资源目录（FE-1422a，QA 钉题发现端点）。

    只读；与 `_published_resource_for_ability` 用同一 `_v2_assignable` 门控，
    保证"目录里能查到的 = pin 一定能落题的"，两端语义不漂移。
    """
    rows = (
        await db.execute(
            select(ResourceVersion, Resource.ability_id, Resource.title)
            .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
            .where(ResourceVersion.review_status == "published")
            .order_by(Resource.ability_id.asc(), ResourceVersion.difficulty.asc())
        )
    ).all()
    out = []
    for rv, ability_id, title in rows:
        # schema_version 过滤在应用层（ui_schema 是通用 JSON 列，避免方言表达式）
        if not isinstance(rv.ui_schema, dict) or rv.ui_schema.get("schema_version") != "2.0":
            continue
        if not _v2_assignable(rv.ui_schema):
            continue
        renderer = None
        mode = None
        ws = (rv.ui_schema or {}).get("workspaces") or []
        if ws and isinstance(ws[0], dict):
            renderer = ws[0].get("renderer")
            mode = ws[0].get("mode")
        out.append({
            "resource_version_id": str(rv.resource_version_id),
            "resource_id": str(rv.resource_id),
            "ability_id": ability_id,
            "renderer": renderer,
            "mode": mode,
            "difficulty": rv.difficulty,
            "title": title,
            "transfer_distance": rv.transfer_distance,
        })
    return out


async def assign_next_task(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    session_id: uuid.UUID,
    subject: str,
    requested_minutes: int | None = None,
    ability_id: str | None = None,
    pin_resource_version_id: uuid.UUID | None = None,
) -> dict:
    """取下一题并落 task_instance，返回 OpenAPI TaskInstance 结构。

    - 显式 ability_id（前端挑战卡片 → 能力映射）：优先 fit_band 内选题，
      带内无题退到该能力最低难度（保证指定能力一定有题）。
    - 未指定：候选能力 level 升序，取「fit_band 内有已发布资源」的第一个（原行为）。
    - pin_resource_version_id（FE-1422a，QA 确定性钉题）：**仅 QA child 可用**
      （403 校验在路由层）；命中 published + V2-assignable 资源则直接落题，
      绕过 fit_band / session 排除。缺省时行为与原逻辑比特级一致。
    """
    selected_ability: str | None = None
    rv: ResourceVersion | None = None
    band_min = band_max = 1

    # 本 session 已出过的资源版本：取下一题时排除，避免「答对后点下一题仍是同一道」。
    assigned_rvs = set(
        (
            await db.execute(
                select(TaskInstance.resource_version_id).where(
                    TaskInstance.session_id == session_id
                )
            )
        ).scalars().all()
    )

    if pin_resource_version_id is not None:
        # QA 钉题路径：不看 band、不看排除；只守 published + V2 门控红线。
        pinned = await db.get(ResourceVersion, pin_resource_version_id)
        if pinned is None or pinned.review_status != "published" or not _v2_assignable(pinned.ui_schema):
            return {
                "task_instance_id": None,
                "ability_id": None,
                "difficulty": None,
                "ui_schema": None,
                "strategy_policy": None,
                "reason": "pinned_resource_not_assignable",
            }
        res = await db.get(Resource, pinned.resource_id)
        selected_ability = res.ability_id if res else ability_id
        rv = pinned
        band_min = band_max = pinned.difficulty
    elif ability_id:
        state = await db.get(AbilityState, {"child_id": child_id, "ability_id": ability_id})
        level = state.level if state else 0
        confidence = float(state.confidence) if state else 0.0
        band_min, band_max = compute_fit_band(level=level, confidence=confidence)
        rv = await _published_resource_for_ability(
            db,
            ability_id=ability_id,
            band_min=band_min,
            band_max=band_max,
            fallback_to_lowest=True,
            exclude_resource_version_ids=assigned_rvs,
        )
        # 该能力新题已耗尽（全部被排除）→ 解除排除，允许重复，避免死锁。
        if rv is None:
            rv = await _published_resource_for_ability(
                db,
                ability_id=ability_id,
                band_min=band_min,
                band_max=band_max,
                fallback_to_lowest=True,
            )
        if rv is not None:
            selected_ability = ability_id
    else:
        candidates = await _candidate_abilities(db, child_id=child_id, session_id=session_id)
        for aid in candidates:
            state = await db.get(AbilityState, {"child_id": child_id, "ability_id": aid})
            level = state.level if state else 0
            confidence = float(state.confidence) if state else 0.0
            bmin, bmax = compute_fit_band(level=level, confidence=confidence)

            row = await _published_resource_for_ability(
                db,
                ability_id=aid,
                band_min=bmin,
                band_max=bmax,
                fallback_to_lowest=False,
                exclude_resource_version_ids=assigned_rvs,
            )
            if row is not None:
                selected_ability = aid
                rv = row
                band_min, band_max = bmin, bmax
                break

    if selected_ability is None or rv is None:
        return {
            "task_instance_id": None,
            "ability_id": None,
            "difficulty": None,
            "ui_schema": None,
            "strategy_policy": None,
            "reason": "no_published_resource_in_band",
        }

    # evidence_role / task_purpose 属于 Task Assignment（不是 Resource 本身）：
    # - 迁移题（transfer_distance 非 None）→ transfer
    # - 否则默认 standard；若该能力 trend 走低（review/巩固）→ retention + review purpose
    state = await db.get(AbilityState, {"child_id": child_id, "ability_id": selected_ability})
    trend = state.trend if state else None

    evidence_role = "transfer" if rv.transfer_distance is not None else "standard"
    task_purpose = "normal"
    if rv.transfer_distance is None and trend in ("down_review", "watch"):
        evidence_role = "retention"
        task_purpose = "review"

    task = TaskInstance(
        session_id=session_id,
        child_id=child_id,
        ability_id=selected_ability,
        resource_version_id=rv.resource_version_id,
        assigned_difficulty=rv.difficulty,
        strategy_policy={
            "hint_max_level": 4,
            "fit_band": [band_min, band_max],
            "evidence_role": evidence_role,
            "task_purpose": task_purpose,
            **({"pinned": True} if pin_resource_version_id is not None else {}),
        },
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    session = await db.get(LearningSession, session_id)

    return {
        "task_instance_id": task.task_instance_id,
        "ability_id": selected_ability,
        "difficulty": rv.difficulty,
        "ui_schema": rv.ui_schema,
        "strategy_policy": task.strategy_policy,
        "resource_version_id": rv.resource_version_id,
        "goal": rv.content.get("goal") if isinstance(rv.content, dict) else None,
        "plan_id": session.plan_id if session else None,
    }


async def submit_attempt(
    db: AsyncSession,
    *,
    task_instance_id: uuid.UUID,
    attempt_no: int,
    response: dict,
    client_elapsed_ms: int | None = None,
    used_hint_levels: list[int] | None = None,
    submission_id: uuid.UUID | None = None,
) -> dict:
    """提交作答（无 child_id，从 task 反查），后端判分 → 诊断 → next_action。

    submission_id（V2 幂等键，docs/frontend/29 §3）：可空——V1 提交不带时回落
    (task_instance_id, attempt_no) 顺序号幂等（旧轨），V2 规模化前双轨并存。
    """
    task = await db.get(TaskInstance, task_instance_id)
    if task is None:
        raise ValueError(f"task_instance {task_instance_id} 不存在")

    rv = await db.get(ResourceVersion, task.resource_version_id)
    expected = rv.content.get("answer") if rv and isinstance(rv.content, dict) else None
    user_answer = response.get("answer") if isinstance(response, dict) else None

    # V2 提交：answer 为结构对象 {value:...}，判分提取 value；V1 answer 仍是标量。
    if isinstance(user_answer, dict):
        user_answer = user_answer.get("value")

    if expected is None or user_answer is None:
        correct = None
    else:
        correct = _judge(expected, user_answer)

    # 诊断候选来源：资源侧全部错因规则（不再取"第一条"当结论，交 V2 观察匹配）。
    error_models = rv.error_models if rv and rv.error_models else None

    max_hint_level = max(used_hint_levels) if used_hint_levels else 0

    result = await record_attempt(
        db,
        child_id=task.child_id,
        task_instance_id=task_instance_id,
        attempt_no=attempt_no,
        response=response,
        correct=correct,
        max_hint_level=max_hint_level,
        client_elapsed_ms=client_elapsed_ms,
        error_models=error_models,
        ui_schema=rv.ui_schema if rv else None,
        resource_version_id=task.resource_version_id,
        used_hint_levels=used_hint_levels,
        submission_id=submission_id,
    )

    # 答对时补齐 next_action（record_attempt 仅在答错时生成 HINT）。
    # 对齐 OpenAPI：答对 → NEXT_TASK（还有题）或 COMPLETE（本轮目标已达成）。
    if result["correct"] and result["next_action"] is None:
        # 该 session 下已答对（存在 correct=True attempt）的 task 去重计数
        completed_count = (
            await db.execute(
                select(func.count(func.distinct(Attempt.task_instance_id))).where(
                    Attempt.task_instance_id.in_(
                        select(TaskInstance.task_instance_id).where(
                            TaskInstance.session_id == task.session_id
                        )
                    ),
                    Attempt.correct.is_(True),
                )
            )
        ).scalar_one()
        result["next_action"] = (
            {"type": "COMPLETE", "policy_id": None}
            if completed_count >= SESSION_TASK_GOAL
            else {"type": "NEXT_TASK", "policy_id": None}
        )

    await db.commit()

    return result


async def request_hint(
    db: AsyncSession,
    *,
    attempt_id: uuid.UUID,
    requested_level: int | None = None,
) -> dict:
    """受控 Hint：由 attempt 反查 task → resource 的 hint_policy.ladder。

    返回 OpenAPI hints 结构（action_type + text + answer_revealed + ui_action）。
    ui_action 对齐前端 WorkspaceUiAction：根据 ui_schema.visual.type 驱动图示交互
    （highlight / align_groups / show_bar_relation / show_number_line_start）。
    """
    attempt = await db.get(Attempt, attempt_id)
    if attempt is None:
        raise ValueError(f"attempt {attempt_id} 不存在")

    task = await db.get(TaskInstance, attempt.task_instance_id)
    rv = await db.get(ResourceVersion, task.resource_version_id) if task else None

    ladder: list[str] = []
    if rv and isinstance(rv.hint_policy, dict):
        ladder = rv.hint_policy.get("ladder", []) or []

    # 阶梯级数 = 资源 hint 阶梯长度（无则默认 4）
    max_level = len(ladder) if ladder else 4
    level = max(1, min(requested_level if requested_level else attempt.attempt_no, max_level))

    action_type = {1: "QUESTION", 2: "STRUCTURE_HINT", 3: "STEP_HINT"}.get(level, "TEACH")
    text = ladder[level - 1] if ladder else f"第 {level} 步提示"

    return {
        "policy_id": f"hint-{level}",
        "hint_level": level,
        "action_type": action_type,
        "text": text,
        "answer_revealed": False,  # 红线：任何 Hint 不直接泄答案
        "ui_action": _build_ui_action(rv, level),
    }


def _build_ui_action(rv: ResourceVersion | None, level: int) -> dict | None:
    """返回该 Hint 级别对应的工作台 ui_action。

    优先取 hint_policy.ui_actions[level-1]（内容团队精确设计）；
    缺失时按 visual.type 推导兜底（highlight/align/show_bar_relation/show_number_line_start）。
    """
    if rv is None or level < 1:
        return None

    # 1. 首选：hint_policy.ui_actions 里内容侧配置的值
    if isinstance(rv.hint_policy, dict):
        ui_actions = rv.hint_policy.get("ui_actions") or []
        if isinstance(ui_actions, list) and level <= len(ui_actions):
            raw = ui_actions[level - 1]
            if isinstance(raw, str) and raw.strip():
                return _ui_action_from_hint_type(raw)

    # 2. 兜底：按 visual.type 推导
    if level < 2:
        return None
    ui_schema = rv.ui_schema if isinstance(rv.ui_schema, dict) else {}
    if ui_schema.get("kind") != "manipulative":
        return None
    visual = ui_schema.get("visual")
    if not isinstance(visual, dict):
        return None

    vtype = visual.get("type")
    if vtype == "objects":
        groups = visual.get("groups") or []
        if level == 3:
            return {"type": "align_groups"}
        return {"type": "highlight", "targets": [g.get("id") for g in groups if isinstance(g, dict)]}
    if vtype == "bar-model":
        bars = visual.get("bars") or []
        return {"type": "show_bar_relation", "targets": [b.get("id") for b in bars if isinstance(b, dict)]}
    if vtype == "number-line":
        return {"type": "show_number_line_start", "value": visual.get("start")}
    return None


def _ui_action_from_hint_type(hint_action: str) -> dict | None:
    """把 Excel 里的 ui_action 字符串映射为 WorkspaceUiAction dict。"""
    a = hint_action.strip().lower()
    mapping = {
        "highlight": {"type": "highlight"},
        "align_groups": {"type": "align_groups"},
        "focus": {"type": "focus"},
        "show_bar_relation": {"type": "show_bar_relation"},
        "show_number_line_start": {"type": "show_number_line_start"},
    }
    return mapping.get(a)


def _judge(expected: object, user_answer: object) -> bool:
    try:
        return float(expected) == float(user_answer)
    except (TypeError, ValueError):
        return str(expected).strip() == str(user_answer).strip()