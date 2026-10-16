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
from app.core.education_rules import (
    EXPOSURE_WINDOW_SESSIONS,
    NEW_ABILITY_INTRO_PER_SESSION,
    REMEDIATION_TRENDS,
    RULE_VERSION,
    SESSION_TASK_GOAL,
)
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


# FE-1453 R2 裁决⑤：app_transfer 属观察项能力——题池稀疏（8 题全难度≥3，L0 带[1,1]
# 恒空），且迁移证据语义特殊（transfer_distance 角色）。**不自动纳入未开启能力的
# 虚拟引入范围**；但已有真实 ability_state 行的孩子继续正常参与排序，显式指定
# （挑战卡 plan.target / ability_id）与 QA pin 通道不受本约束——"除非正式策略
# 明确允许"的口子保留在调用方显式意图里。
AUTO_INTRODUCE_EXCLUDED_ABILITIES = frozenset({"app_transfer"})


async def _published_assignable_abilities(db: AsyncSession) -> set[str]:
    """存在 ≥1 条 published 且 V2 可下发资源的能力集合（FE-1453 候选宇宙）。

    与生产下发门控同一 `_v2_assignable` 判定；扫描 published 全量（当前 225 版本级，
    每请求一次、应用层过滤，与 `_first_assignable` 同口径，不用方言表达式）。
    """
    rows = (
        await db.execute(
            select(Resource.ability_id, ResourceVersion.ui_schema)
            .join(ResourceVersion, ResourceVersion.resource_id == Resource.resource_id)
            .where(ResourceVersion.review_status == "published")
        )
    ).all()
    return {aid for aid, ui in rows if _v2_assignable(ui)}


async def _plan_target_set(db: AsyncSession, *, session_id: uuid.UUID) -> set[str]:
    """本 session 管理计划强制指定的目标能力集（FE-1454 复审检查点2）。

    plan.target 是**显式例外通道**：其中的能力不受普通 Auto 新能力配额约束、
    也不计入配额事件数（独立 new_ability_source="plan_target" 落日志）——
    课程计划指定练什么就练什么，与自适应拓展分账。
    """
    session = await db.get(LearningSession, session_id)
    if session and session.plan_id:
        plan = await db.get(LearningPlan, session.plan_id)
        if plan and plan.target_ability_ids:
            return set(plan.target_ability_ids)
    return set()


async def _candidate_abilities(
    db: AsyncSession, *, child_id: uuid.UUID, session_id: uuid.UUID
) -> list[tuple[str, bool]]:
    """候选能力（有序）：优先 plan.target，否则 FE-1453 统一修复 ITEM01-01/02——

    候选宇宙 = 已有 ability_state 行 ∪ 有已发布可下发资源但未开启的能力（**虚拟 L0**），
    观察项能力（AUTO_INTRODUCE_EXCLUDED_ABILITIES）不参与虚拟引入、真实行不受限。
    共同根因是"已有行≠完整候选集"：零行账号 auto 分支原永远空池（冷启动死锁），
    已有行的孩子又只会训练已开启能力（视野锁死）。虚拟能力按 level 0 / confidence 0
    参与排序（真实行 (0,0) 在前保可解释性，其后按 ability_id 稳定终序）——
    **不写 ability_state、不产 Mastery 证据**；孩子首次作答由
    persist_mastery_state 既有逻辑自然落行，转为真实状态参与后续排序。
    返回 [(ability_id, is_virtual)]。
    """
    session = await db.get(LearningSession, session_id)
    if session and session.plan_id:
        plan = await db.get(LearningPlan, session.plan_id)
        if plan and plan.target_ability_ids:
            states = {
                row.ability_id: (row.level, float(row.confidence))
                for row in (
                    await db.execute(
                        select(AbilityState).where(AbilityState.child_id == child_id)
                    )
                ).scalars().all()
            }
            out = []
            for aid in plan.target_ability_ids:
                lvl, conf = states.get(aid, (0, 0.0))
                out.append((aid, (lvl, conf), aid not in states))
            return [(aid, virt) for aid, _, virt in out]

    rows = (
        await db.execute(
            select(AbilityState.ability_id, AbilityState.level, AbilityState.confidence)
            .where(AbilityState.child_id == child_id)
        )
    ).all()
    real = [(aid, (level, float(conf)), False) for aid, level, conf in rows]
    # 虚拟引入宇宙 = 有已发布可下发资源的未开启能力，减去观察项排除集（R2 裁决⑤）
    virtual_universe = (
        await _published_assignable_abilities(db)
        - {r[0] for r in real}
        - AUTO_INTRODUCE_EXCLUDED_ABILITIES
    )
    virtual = [(aid, (0, 0.0), True) for aid in sorted(virtual_universe)]
    # 真实 (0,0) 行在前、虚拟 (0,0) 其后，终序 ability_id 稳定
    ordered = sorted(real + virtual, key=lambda t: (t[1][0], t[1][1], t[2], t[0]))
    return [(aid, virt) for aid, _, virt in ordered]


async def _pick_ability(db: AsyncSession, *, child_id: uuid.UUID, session_id: uuid.UUID) -> str | None:
    """从候选能力里选「有已发布资源」的第一个（不考虑难度带，仅保证有题）。"""
    candidates = await _candidate_abilities(db, child_id=child_id, session_id=session_id)
    for aid, _virt in candidates:
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
    exclude_resource_ids: set | None = None,
) -> ResourceVersion | None:
    """取某能力「fit_band 内」的已发布资源；带内无题且 fallback_to_lowest 时，
    退到该能力「最低难度」已发布资源（保证指定能力一定有题可练）。

    exclude_resource_version_ids：本 session 已出过的题，取下一题时排除，
    避免「答对后点下一题仍是同一道题」。
    exclude_resource_ids：FE-1454 跨 Session 近期曝光集（**resource 级**——
    同一资源换版本不能绕过去重，R2 §四）。

    V2 门控：planned renderer 的 V2 资源不可下发（多取候选后在应用层过滤）。"""
    exclude = exclude_resource_version_ids or set()
    base_where = [
        Resource.ability_id == ability_id,
        ResourceVersion.review_status == "published",
    ]
    if exclude:
        base_where.append(ResourceVersion.resource_version_id.notin_(exclude))
    if exclude_resource_ids:
        base_where.append(ResourceVersion.resource_id.notin_(exclude_resource_ids))

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
            # FE-1441：金题恒先 + 确定性排序。首要键=非 [T155] 交付题（金题/其它）排前；
            # E2E spec 依赖 catalog[renderer][0]=金题——155 交付题 published 后与金题
            # 同 (ability,difficulty) 或 difficulty 更小时会顶掉金题首位（实锤 20 组全顶），
            # 故金题优先必须成排序硬约束，created_at/rvid 终序保确定性。
            .order_by(Resource.title.notlike("[T155]%").desc(),
                      Resource.ability_id.asc(), ResourceVersion.difficulty.asc(),
                      ResourceVersion.created_at.asc(), ResourceVersion.resource_version_id.asc())
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


async def _recent_exposure(db: AsyncSession, *, child_id: uuid.UUID,
                           session_id: uuid.UUID) -> tuple[set, set, set]:
    """FE-1454 跨 Session 近期曝光集（R2 §四）。

    返回 (exposed_resource_ids, exposed_resource_version_ids, exposed_ability_ids)：
    - 窗口 = 该 child **最近 EXPOSURE_WINDOW_SESSIONS 个 session**（含当前）内
      所有 TaskInstance 触达过的资源；
    - **去重主键 = resource_id**（裁决红线：同一资源不同版本不能靠换
      resource_version_id 绕过去重）；resource_version_id 集另作精确排除；
    - ability 集用于"已引入过"判定（重复推送已曝光能力≠新引入事件）。

    与既有 session 内 assigned_rvs 排除互补：session 内排除照旧（防"下一题同题"），
    本函数把视野扩到跨 session；窗口内全部命中过的资源都算"已曝光"。
    """
    recent_sessions = list(
        (
            await db.execute(
                select(LearningSession.session_id)
                .where(LearningSession.child_id == child_id)
                .order_by(LearningSession.started_at.desc(),
                          LearningSession.session_id.desc())
                .limit(EXPOSURE_WINDOW_SESSIONS)
            )
        ).scalars().all()
    )
    if not recent_sessions:
        recent_sessions = [session_id]
    rows = (
        await db.execute(
            select(TaskInstance.resource_version_id, Resource.resource_id,
                   TaskInstance.ability_id)
            .join(ResourceVersion,
                  ResourceVersion.resource_version_id == TaskInstance.resource_version_id)
            .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
            .where(TaskInstance.session_id.in_(recent_sessions))
        )
    ).all()
    exposed_rids = {r[1] for r in rows}
    exposed_rvs = {r[0] for r in rows}
    exposed_aids = {r[2] for r in rows}
    return exposed_rids, exposed_rvs, exposed_aids


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
    selection_reason: str | None = None

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

    # FE-1454：跨 session 近期曝光集（resource 级，窗口=EXPOSURE_WINDOW_SESSIONS）。
    # pin 分支不使用（QA 确定性通道语义不变）。
    exposed_rids: set = set()
    exposed_aids: set = set()
    if pin_resource_version_id is None:
        exposed_rids, _exposed_rvs, exposed_aids = await _recent_exposure(
            db, child_id=child_id, session_id=session_id)

    if pin_resource_version_id is not None:
        # QA 钉题路径：不看 band、不看排除；只守可下发状态 + V2 门控红线。
        # published=金题/正式题；qa_staged（FE-1438）=未过 M→app 审批的 QA 抽样批——
        # 仅本路径放行（路由层 403 保证真实 child 无法 pin），catalog/生产选题池不可见。
        pinned = await db.get(ResourceVersion, pin_resource_version_id)
        if pinned is None or pinned.review_status not in ("published", "qa_staged") or not _v2_assignable(pinned.ui_schema):
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
        # FE-1454：显式能力同样避开跨 session 近期曝光资源（resource 级去重）；
        # 全部曝光耗尽时回落允许重复，但 reason 记 pool_exhausted（无依据重复率 0%）。
        rv = await _published_resource_for_ability(
            db,
            ability_id=ability_id,
            band_min=band_min,
            band_max=band_max,
            fallback_to_lowest=True,
            exclude_resource_version_ids=assigned_rvs,
            exclude_resource_ids=exposed_rids,
        )
        if rv is None:
            selection_reason = "pool_exhausted"
            rv = await _published_resource_for_ability(
                db,
                ability_id=ability_id,
                band_min=band_min,
                band_max=band_max,
                fallback_to_lowest=True,
            )
        else:
            selection_reason = "new_item"
        if rv is not None:
            selected_ability = ability_id
    else:
        # ---- FE-1454 auto 选题策略（R2 §三/§四冻结口径）----
        # 优先级：先尊重 Session 目标（plan.target 在 _candidate_abilities 内已优先）
        # → 按能力状态排序（level asc 弱项优先）→ 覆盖需求（虚拟新能力受配额约束）。
        # 两趟：第一趟只要"带内合格未曝光新题"；全域无新题时第二趟才允许重复，
        # 且必须落受控原因（spaced_review=趋势走低触发 / pool_exhausted=新题耗尽）。
        #
        # 配额（决策③）统一口径：**引入事件按瞬间记录**——任务策略 is_new_ability
        # （选中时无 state 行）即一次引入。本 session 引入事件数 ≤ 配额；已引入
        # 能力继续练习不重复计数；真实行能力永不占配额。**作答建档后事件记忆不丢**
        # （否则"引入→答对建档→又引下一个"会连穿 2 个新能力）。两趟共用同一道门。
        candidates = await _candidate_abilities(db, child_id=child_id, session_id=session_id)
        all_states = {
            row.ability_id: row
            for row in (
                await db.execute(
                    select(AbilityState).where(AbilityState.child_id == child_id)
                )
            ).scalars().all()
        }
        sess_tasks = (
            await db.execute(
                select(TaskInstance).where(TaskInstance.session_id == session_id)
            )
        ).scalars().all()
        # 复审检查点2：plan.target=管理计划强制指定 → **显式例外通道**，
        # 不受配额约束、不占配额事件数（new_ability_source="plan_target" 独立分账，
        # 配额事件只统计 source=="auto"）。is_new_ability 保留第一轮口径兼容：
        # 选中瞬间无 state 行=引入事件。
        plan_targets = await _plan_target_set(db, session_id=session_id)
        auto_introduced = {
            t.ability_id for t in sess_tasks
            if isinstance(t.strategy_policy, dict)
            and t.strategy_policy.get("is_new_ability")
            and t.strategy_policy.get("new_ability_source", "auto") == "auto"
        }

        def _quota_blocked(aid: str) -> bool:
            # plan.target 例外永不受配额约束（管理意志优先，R2 §三"先尊重 Session 目标"）
            if aid in plan_targets:
                return False
            # 真实行能力永不占配额；本 session 已 auto 引入能力继续练习不重复计数；
            # 全新（无行、未 auto 引入）能力在事件数达配额后拦截——两趟共用此门
            if aid in all_states or aid in auto_introduced:
                return False
            return len(auto_introduced) >= NEW_ABILITY_INTRO_PER_SESSION

        def _intro_flag(aid: str) -> tuple[bool, str]:
            if aid in all_states:
                return (False, "existing")
            return (True, "plan_target" if aid in plan_targets else "auto")

        # 第一趟：新题（resource 级排除近期曝光 + session 级排除已发版本）
        for aid, is_virtual in candidates:
            if _quota_blocked(aid):
                continue
            st = all_states.get(aid)
            level = st.level if st else 0
            confidence = float(st.confidence) if st else 0.0
            bmin, bmax = compute_fit_band(level=level, confidence=confidence)

            row = await _published_resource_for_ability(
                db,
                ability_id=aid,
                band_min=bmin,
                band_max=bmax,
                fallback_to_lowest=False,
                exclude_resource_version_ids=assigned_rvs,
                exclude_resource_ids=exposed_rids,
            )
            if row is not None:
                selected_ability = aid
                rv = row
                band_min, band_max = bmin, bmax
                selection_reason = "new_item"
                break

        # 第二趟：全域无合格新题 → 受控重复（区分必要复习与耗尽兜底）
        if selected_ability is None:
            for aid, is_virtual in candidates:
                if _quota_blocked(aid):
                    continue  # 配额门不因"重复趟"旁路
                st = all_states.get(aid)
                if st is None and aid not in auto_introduced and aid not in exposed_aids \
                        and aid not in plan_targets:
                    # 无任何历史（无行、本 session 未引入、窗口内未曝光）：
                    # "重复"推它没有可复习对象=无依据——跳过（配额门另有其责）
                    continue
                level = st.level if st else 0
                confidence = float(st.confidence) if st else 0.0
                trend = st.trend if st else None
                bmin, bmax = compute_fit_band(level=level, confidence=confidence)
                row = await _published_resource_for_ability(
                    db,
                    ability_id=aid,
                    band_min=bmin,
                    band_max=bmax,
                    fallback_to_lowest=False,
                    exclude_resource_version_ids=None,
                )
                if row is not None:
                    selected_ability = aid
                    rv = row
                    band_min, band_max = bmin, bmax
                    selection_reason = (
                        "remediation_review" if trend in REMEDIATION_TRENDS
                        else "pool_exhausted"
                    )
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

    # FE-1454 推荐原因落日志（R2 §四：任何重复必须可解释；无依据重复率硬门槛=0%）。
    # selection_reason ∈ new_item / remediation_review / pool_exhausted
    #（remediation_review=趋势走低的补救练习，**非间隔复习**——无时间调度依据时
    #  不得冒用 spaced_review 之名，R2 FE-1454 复审检查点3 改名）；
    # is_new_ability=选中瞬间无 state 行（引入事件，第一轮口径兼容）；
    # new_ability_source=引入来源分账：existing（已有行）/ auto（自适应配额事件）/
    # plan_target（管理计划强制，**不占配额、独立日志**）/ explicit（挑战卡显式指定）。
    policy = {
        "hint_max_level": 4,
        "fit_band": [band_min, band_max],
        "evidence_role": evidence_role,
        "task_purpose": task_purpose,
        **({"pinned": True} if pin_resource_version_id is not None else {}),
    }
    if pin_resource_version_id is None and selection_reason is not None:
        policy["selection_reason"] = selection_reason
        if ability_id is not None:
            # 显式挑战卡=用户/前端意志，不算自适应引入事件（也不占配额统计）
            is_new = state is None
            source = "explicit" if is_new else "existing"
        else:
            is_new, source = _intro_flag(selected_ability)
        policy["is_new_ability"] = is_new
        policy["new_ability_source"] = source
    task = TaskInstance(
        session_id=session_id,
        child_id=child_id,
        ability_id=selected_ability,
        resource_version_id=rv.resource_version_id,
        assigned_difficulty=rv.difficulty,
        strategy_policy=policy,
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


async def trace_next_selection(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    session_id: uuid.UUID,
    ability_id: str | None = None,
) -> dict:
    """QA-ITEM-01 只读选题追踪（QA-only 端点消费）：镜像生产自选分支的过滤/排序决策，
    输出候选池、逐能力 fit_band、排除集与预测选中项。**不落 TaskInstance、零写入**。

    对账语义：QA 侧比较 trace.predicted_selected 与随后真实 tasks/next 的返回，
    一致=追踪可信（生产分支未漂移）；不一致=以实发为准并标记 mismatch（追踪只读承诺不破）。
    """
    assigned_rvs = set(
        (
            await db.execute(
                select(TaskInstance.resource_version_id).where(
                    TaskInstance.session_id == session_id
                )
            )
        ).scalars().all()
    )

    if ability_id:
        candidate_abilities = [ability_id]
        mode = "explicit_ability"
    else:
        candidate_abilities = await _candidate_abilities(db, child_id=child_id, session_id=session_id)
        mode = "auto"

    states = {
        row.ability_id: row
        for row in (
            await db.execute(select(AbilityState).where(AbilityState.child_id == child_id))
        ).scalars().all()
    }

    per_ability: list[dict] = []
    predicted = None
    predicted_band = None
    for aid in candidate_abilities:
        st = states.get(aid)
        level = st.level if st else 0
        confidence = float(st.confidence) if st else 0.0
        trend = st.trend if st else None
        bmin, bmax = compute_fit_band(level=level, confidence=confidence)

        # 与 _published_resource_for_ability(auto 分支) 同条件取带内候选（limit 对齐 50）
        rows = (
            await db.execute(
                select(ResourceVersion, Resource.title)
                .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
                .where(
                    Resource.ability_id == aid,
                    ResourceVersion.review_status == "published",
                    *([ResourceVersion.resource_version_id.notin_(assigned_rvs)] if assigned_rvs else []),
                    ResourceVersion.difficulty >= bmin,
                    ResourceVersion.difficulty <= bmax,
                )
                .order_by(ResourceVersion.difficulty.asc(), ResourceVersion.created_at.asc())
                .limit(50)
            )
        ).all()
        assignable = [(rv, title) for rv, title in rows if _v2_assignable(rv.ui_schema)]
        first = assignable[0] if assignable else None
        entry = {
            "ability_id": aid,
            "level": level,
            "confidence": confidence,
            "trend": trend,
            "fit_band": [bmin, bmax],
            "eligible_pool_size": len(assignable),
            "eligible_head": [
                {
                    "resource_version_id": str(rv.resource_version_id),
                    "difficulty": rv.difficulty,
                    "title": title,
                    "transfer_distance": rv.transfer_distance,
                }
                for rv, title in assignable[:8]
            ],
            "filtered_out_of_band": len(rows) - len(assignable),
        }
        per_ability.append(entry)
        if predicted is None and first is not None:
            rv, title = first
            predicted = {
                "resource_version_id": str(rv.resource_version_id),
                "ability_id": aid,
                "difficulty": rv.difficulty,
                "title": title,
            }
            predicted_band = [bmin, bmax]

    return {
        "mode": mode,
        "session_id": str(session_id),
        "recent_assigned_excluded": [str(x) for x in sorted(assigned_rvs, key=str)],
        "policy_version": RULE_VERSION,
        "per_ability": per_ability,
        "predicted_selected": predicted,
        "predicted_fit_band": predicted_band,
        "predicted_reason": (
            f"first ability in candidate order with band-eligible assignable resource; "
            f"ordered by difficulty asc, created_at asc"
        ) if predicted else "no_published_resource_in_band",
        "read_only": True,
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