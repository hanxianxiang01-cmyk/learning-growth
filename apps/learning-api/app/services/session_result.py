"""SessionResultService —— 一次学习 Session 的真实结果聚合（新增能力）。

对标前端 V1.2「Learning Result Closure」的 canonical contract，让结果页摆脱前端
sessionStorage 快照，改为后端作为学习结果的 Source of Truth。

输出字段对齐前端 `contracts.ts` 的 `SessionResult`（后端是权威，正常器零 alias 即可消费）：
- hint_usage: number[]（去重的 hint 级）
- learning_behaviors: [{code,label,achieved}]
- ability_changes: [{ability_id,name,after_level,confidence,trend,evidence_delta}]
- next_recommendation: {type,title,description,ability_id}

数据来源（纯读、可追溯）：
- learning_session：session 元信息、起止时间
- task_instance：本 session 下发的任务
- attempt：每次作答（correct / max_hint_level / submitted_at）
- learning_event：诊断结果（record_attempt 写入 payload.diagnosis）
- ability_state + ability_node：涉及能力的最新状态 + 中文名
- mastery_evidence：本 session 新增的有效证据（evidence_delta）

原则（对齐冻结基线）：
- 前端不计算 Mastery / 不实现 Diagnosis；本接口只「聚合」后端已有事实，不做教育决策推断。
- 诊断码 E01~E07 是教育诊断，绝不当 HTTP 错误返回。
- learning_behaviors 是「纯事实判定」（先错后对 / 提示未超 2 级 / 完成末题），非教育推断。
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.education_rules import DIAGNOSIS_LABELS
from app.models import (
    AbilityNode,
    AbilityState,
    Attempt,
    LearningEvent,
    LearningSession,
    MasteryEvidence,
    TaskInstance,
)


async def get_session_result(db: AsyncSession, *, session_id: uuid.UUID) -> dict:
    """聚合一次 session 的真实学习结果，输出对齐前端 SessionResult 的 canonical shape。"""
    session = await db.get(LearningSession, session_id)
    if session is None:
        raise ValueError(f"session {session_id} 不存在")

    # 1. 本 session 全部任务
    tasks = (
        await db.execute(
            select(TaskInstance).where(TaskInstance.session_id == session_id)
        )
    ).scalars().all()

    task_ids = [t.task_instance_id for t in tasks]

    # 2. 全部作答
    attempts: list[Attempt] = []
    if task_ids:
        attempts = (
            await db.execute(
                select(Attempt)
                .where(Attempt.task_instance_id.in_(task_ids))
                .order_by(Attempt.submitted_at.asc())
            )
        ).scalars().all()

    # 3. 诊断事件
    events: list[LearningEvent] = []
    if task_ids:
        events = (
            await db.execute(
                select(LearningEvent).where(
                    LearningEvent.session_id == session_id,
                    LearningEvent.event_type == "attempt_submitted",
                )
            )
        ).scalars().all()

    # 4. 本 session 新增的有效证据（evidence_delta 用）
    evidence_count = 0
    if task_ids:
        evidence_count = len(
            (
                await db.execute(
                    select(MasteryEvidence).where(
                        MasteryEvidence.task_instance_id.in_(task_ids),
                        MasteryEvidence.valid.is_(True),
                    )
                )
            ).scalars().all()
        )

    # 5. session 涉及的能力（按 task 去重）
    ability_ids = list({t.ability_id for t in tasks})

    # ---------- 聚合计算 ----------

    # 正确/完成判定：一个 task 只要有任意一次 correct=True 即视为「已完成」
    correct_by_task: dict[uuid.UUID, bool] = {}
    for a in attempts:
        if a.correct:
            correct_by_task[a.task_instance_id] = True

    completed_tasks = sum(1 for t in tasks if correct_by_task.get(t.task_instance_id))
    correct_count = sum(1 for a in attempts if a.correct)
    attempt_count = len(attempts)

    elapsed_ms = _session_duration_ms(session, attempts)

    # hint_usage：number[]（去重的 hint 级，1~4）
    hint_levels = sorted(
        {a.max_hint_level for a in attempts if a.max_hint_level and a.max_hint_level > 0}
    )

    # 诊断汇总（从 event payload.diagnosis.code 聚合）
    diagnosis_counter: dict[str, int] = {}
    for e in events:
        payload = e.payload or {}
        d = payload.get("diagnosis")
        if isinstance(d, dict) and d.get("code"):
            code = d["code"]
            diagnosis_counter[code] = diagnosis_counter.get(code, 0) + 1

    # 能力变化（对齐 AbilityChange：ability_id/name/after_level/confidence/trend/evidence_delta）
    ability_changes = []
    for aid in ability_ids:
        state = await db.get(AbilityState, {"child_id": session.child_id, "ability_id": aid})
        node = await db.get(AbilityNode, aid)
        if state is None:
            continue
        ability_changes.append(
            {
                "ability_id": aid,
                "name": node.name if node else None,
                "after_level": state.level,
                "confidence": float(state.confidence),
                "trend": state.trend,
                "evidence_delta": evidence_count,
            }
        )

    # 学习行为（LearningBehavior[]：code/label/achieved）
    learning_behaviors = _learning_behaviors(tasks, attempts, correct_by_task)

    # 下一阶段重点（NextRecommendation：type/title/description/ability_id）
    next_recommendation = _next_recommendation(ability_changes)

    return {
        "session_id": session.session_id,
        "child_id": session.child_id,
        "status": session.status,
        "duration_ms": elapsed_ms,
        "task_count": len(tasks),
        "attempt_count": attempt_count,
        "correct_count": correct_count,
        "hint_usage": hint_levels,
        "diagnosis_summary": [
            {"code": code, "label": DIAGNOSIS_LABELS.get(code, code), "count": cnt}
            for code, cnt in sorted(diagnosis_counter.items())
        ],
        "ability_changes": ability_changes,
        "learning_behaviors": learning_behaviors,
        "next_recommendation": next_recommendation,
    }


def _session_duration_ms(session: LearningSession, attempts: list[Attempt]) -> int:
    """session 用时：优先 ended_at，否则取末次作答时间，再兜底 started_at。"""
    end = session.ended_at
    if end is None and attempts:
        end = attempts[-1].submitted_at
    if end is None:
        end = session.started_at

    start = session.started_at
    if start is None:
        return 0
    delta = (end - start).total_seconds() * 1000 if end >= start else 0
    return int(delta)


def _learning_behaviors(
    tasks: list[TaskInstance],
    attempts: list[Attempt],
    correct_by_task: dict[uuid.UUID, bool],
) -> list[dict]:
    """前端 LearningBehaviorChecklist 的三条「事实判定」，输出 code/label/achieved。"""
    # 遇到困难后继续尝试：存在某个 task 先错后对
    wrong_then_correct = False
    for a in attempts:
        if not a.correct and correct_by_task.get(a.task_instance_id):
            wrong_then_correct = True
            break

    # 合理使用提示：hint 最高级未超过 2（纯事实）
    hint_levels = [a.max_hint_level for a in attempts if a.max_hint_level]
    used_hints_reasonably = (max(hint_levels) <= 2) if hint_levels else True

    # 完成最终任务：最后一个 task 已完成
    completed_final = bool(tasks) and correct_by_task.get(tasks[-1].task_instance_id, False)

    completed = sum(1 for t in tasks if correct_by_task.get(t.task_instance_id))

    return [
        {
            "code": "SESSION_COMPLETED",
            "label": "完成了本次数学任务",
            "achieved": completed > 0,
        },
        {
            "code": "RETRY_AFTER_ERROR",
            "label": "遇到困难后继续尝试",
            "achieved": wrong_then_correct,
        },
        {
            "code": "HINT_USED_APPROPRIATELY",
            "label": "合理使用提示",
            "achieved": used_hints_reasonably,
        },
        {
            "code": "COMPLETED_FINAL_TASK",
            "label": "完成了最后一道任务",
            "achieved": completed_final,
        },
    ]


def _next_recommendation(ability_changes: list[dict]) -> dict:
    """下一阶段重点：level 最低的能力（发展中项），输出 NextRecommendation shape。"""
    if not ability_changes:
        return {
            "type": "NEXT",
            "title": "返回数学首页",
            "description": "系统会根据当前学习状态安排下一项任务。",
            "ability_id": None,
        }
    lowest = min(ability_changes, key=lambda a: (a["after_level"], a["confidence"]))
    name = lowest.get("name") or lowest["ability_id"]
    return {
        "type": "CONTINUE_ABILITY",
        "title": f"继续练习{name}",
        "description": "系统会根据当前学习状态继续安排合适任务。",
        "ability_id": lowest["ability_id"],
    }