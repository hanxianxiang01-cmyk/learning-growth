"""GrowthService（E2-07）—— GrowthSnapshot 生成 + GrowthReport 生成。

对齐 OpenAPI：
- GrowthSnapshot：child_id + period_type + period range + metrics + ability_states
- GrowthReport：report_id + period + summary + metrics + ability_changes + evidence_refs + next_focus

原则（基线）：样本不足显示"观察中"；所有结论必须有 evidence_refs；不凭空生成。
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AbilityNode,
    AbilityState,
    GrowthReport,
    GrowthSnapshot,
    MasteryEvidence,
)


async def build_snapshot(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    period_type: str,
    period_start: date,
    period_end: date,
) -> GrowthSnapshot:
    """从当前能力状态 + 周期内证据，聚合成一个快照。"""
    # 能力状态
    states = (
        await db.execute(
            select(AbilityState).where(AbilityState.child_id == child_id)
        )
    ).scalars().all()

    ability_states = {
        s.ability_id: {
            "level": s.level,
            "confidence": float(s.confidence),
            "evidence_count": s.evidence_count,
            "trend": s.trend,
        }
        for s in states
    }

    # 周期内证据数
    ev_count = (
        await db.execute(
            select(MasteryEvidence).where(
                MasteryEvidence.child_id == child_id,
                MasteryEvidence.valid.is_(True),
                MasteryEvidence.occurred_at >= period_start,
                MasteryEvidence.occurred_at < period_end,
            )
        )
    ).scalars().all()

    metrics = {
        "total_evidence": len(ev_count),
        "ability_count": len(states),
        "average_level": (
            round(sum(s.level for s in states) / len(states), 2) if states else 0.0
        ),
    }

    # 样本不足口径：用「周期内新增证据」判断；能力状态的 evidence_count 是累计值，两者区分开
    insufficient_period_sample = len(ev_count) < 8

    snap = GrowthSnapshot(
        child_id=child_id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        ability_states=ability_states,
    )
    db.add(snap)
    await db.flush()
    return snap


async def build_report(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    snapshot: GrowthSnapshot,
) -> GrowthReport:
    """从快照生成人类可读报告，结论均带 evidence_refs。"""
    states = snapshot.ability_states
    metrics = snapshot.metrics

    # 样本不足判定（对齐基线："样本不足显示观察中"，以本周期证据为准）
    insufficient = insufficient_period_sample

    # 能力变化：与上一快照对比（若存在）
    prev = (
        await db.execute(
            select(GrowthSnapshot)
            .where(
                GrowthSnapshot.child_id == child_id,
                GrowthSnapshot.period_type == snapshot.period_type,
                GrowthSnapshot.period_end <= snapshot.period_start,
            )
            .order_by(GrowthSnapshot.period_end.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    ability_changes = []
    for ability_id, cur in states.items():
        change = {
            "ability_id": ability_id,
            "level": cur["level"],
            "confidence": cur["confidence"],
            "evidence_count": cur["evidence_count"],
        }
        if prev and ability_id in prev.ability_states:
            change["level_delta"] = cur["level"] - prev.ability_states[ability_id]["level"]
        ability_changes.append(change)

    # 下一阶段重点：level 最低的能力（发展中项）
    sorted_abilities = sorted(states.items(), key=lambda kv: kv[1]["level"])
    next_focus = [aid for aid, _ in sorted_abilities[:3]] if states else []

    # evidence_refs：本周期证据 id 列表
    evs = (
        await db.execute(
            select(MasteryEvidence).where(
                MasteryEvidence.child_id == child_id,
                MasteryEvidence.valid.is_(True),
                MasteryEvidence.occurred_at >= snapshot.period_start,
                MasteryEvidence.occurred_at < snapshot.period_end,
            )
        )
    ).scalars().all()
    evidence_refs = {"evidence_ids": [str(e.evidence_id) for e in evs]}

    # summary
    if insufficient:
        summary = "样本不足，当前处于观察中，待积累更多学习证据后再评估。"
    elif next_focus:
        summary = f"孩子正在稳步学习中，下一阶段重点巩固：{', '.join(next_focus)}。"
    else:
        summary = "学习状态良好。"

    content = {
        "summary": summary,
        "metrics": metrics,
        "ability_changes": ability_changes,
        "next_focus": next_focus,
        "insufficient_sample": insufficient,
    }

    report = GrowthReport(
        child_id=child_id,
        snapshot_id=snapshot.snapshot_id,
        report_version=1,
        content=content,
        evidence_refs=evidence_refs,
    )
    db.add(report)
    await db.flush()
    return report


async def get_or_create_monthly_report(
    db: AsyncSession,
    *,
    child_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> dict:
    """月度报告入口：有快照则用，无则现生成（对齐 OpenAPI /v1/reports/monthly）。"""
    existing = (
        await db.execute(
            select(GrowthReport).where(
                GrowthReport.child_id == child_id,
                GrowthReport.created_at >= period_start,
                GrowthReport.created_at < period_end,
            )
        )
    ).scalars().first()

    if existing:
        return report_to_dict(existing)

    snap = await build_snapshot(
        db, child_id=child_id, period_type="monthly",
        period_start=period_start, period_end=period_end,
    )
    report = await build_report(db, child_id=child_id, snapshot=snap)
    await db.commit()
    return report_to_dict(report)


def report_to_dict(r: GrowthReport) -> dict:
    return {
        "report_id": r.report_id,
        "child_id": r.child_id,
        "snapshot_id": r.snapshot_id,
        "period": {
            "type": "monthly",
            "summary": r.content.get("summary", ""),
        },
        "summary": r.content.get("summary", ""),
        "metrics": r.content.get("metrics", {}),
        "ability_changes": r.content.get("ability_changes", []),
        "evidence_refs": r.evidence_refs,
        "next_focus": r.content.get("next_focus", []),
        "insufficient_sample": r.content.get("insufficient_sample", False),
    }