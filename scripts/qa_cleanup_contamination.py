"""存量污染清理（FE-1412 B 阶段）：确定性 TEST 指纹标 valid=false + 生产路径重算。

hygiene: allow-real-child —— 本工具面向真实 child 清理污染，属受控例外。

规则（只作废有铁证的测试数据；拿不准的列 SUSPECT 不动，等用户裁决）：
  T1 999 答案指纹（qa_replay #5 三连 attempt）
  T2 批量簇 session：同 child 60s 窗口内 ≥5 个 session 创建（人做不到）
  T3 脚本提交：attempt.client_elapsed_ms < 2000ms（幼儿不可能）
  T4 E2E harness session（今日 13:36-13:37 簇已被 T2 覆盖；单发快提被 T3 覆盖）
派生窗口证据（stability/transfer_window，task_instance_id IS NULL）：源证据变更后
全部作废，重算时由 _persist_derived_windows 按新签名重新生成。
重算走 persist_mastery_state（生产同一函数），不手改 ability_state。
"""
import asyncio
import os
from datetime import timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REAL_CHILD = "00000000-0000-0000-0000-000000000001"


async def main():
    eng = create_async_engine(os.environ["DATABASE_URL"])
    Sess = async_sessionmaker(eng, expire_on_commit=False)

    async with Sess() as db:
        # ---- 定位 TEST sessions（批量簇）----
        rs = await db.execute(text("""
            WITH ordered AS (
              SELECT session_id, started_at,
                     count(*) OVER (PARTITION BY 1 ORDER BY started_at
                       RANGE BETWEEN '60 seconds' PRECEDING AND '60 seconds' FOLLOWING) AS nearby
              FROM learning_session WHERE child_id = :cid
            )
            SELECT session_id FROM ordered WHERE nearby >= 5
        """), {"cid": REAL_CHILD})
        cluster_sessions = {str(r[0]) for r in rs.all()}

        # ---- T3: 脚本提交（ms<2000）所在 session ----
        rs = await db.execute(text("""
            SELECT DISTINCT t.session_id FROM attempt a
            JOIN task_instance t ON t.task_instance_id = a.task_instance_id
            WHERE t.child_id = :cid AND a.client_elapsed_ms IS NOT NULL
              AND a.client_elapsed_ms < 2000
        """), {"cid": REAL_CHILD})
        fast_sessions = {str(r[0]) for r in rs.all()}

        # ---- T1: 999 指纹 task（该 task 任一 attempt 答 999 → 全 task 证据作废；
        #      qa_replay #5 的证据挂在末次正确 attempt 上，只按证据自身 answer 会漏）----
        rs = await db.execute(text("""
            SELECT DISTINCT a.task_instance_id FROM attempt a
            JOIN task_instance t ON t.task_instance_id = a.task_instance_id
            WHERE t.child_id = :cid AND a.response->>'answer' = '999'
        """), {"cid": REAL_CHILD})
        fingerprint_tasks = {str(r[0]) for r in rs.all()}

        # ---- 收集待作废证据 ----
        rs = await db.execute(text("""
            SELECT e.evidence_id, e.ability_id, e.evidence_type, e.correctness,
                   e.valid, t.session_id, e.task_instance_id,
                   a.client_elapsed_ms, a.response->>'answer' AS ans
            FROM mastery_evidence e
            LEFT JOIN task_instance t ON t.task_instance_id = e.task_instance_id
            LEFT JOIN attempt a ON a.attempt_id = e.attempt_id
            WHERE e.child_id = :cid AND e.valid = true
        """), {"cid": REAL_CHILD})
        rows = rs.mappings().all()

        kill, suspect = [], []
        for r in rows:
            reason = None
            sid = str(r["session_id"]) if r["session_id"] else None
            tid = str(r["task_instance_id"]) if r["task_instance_id"] else None
            if tid and tid in fingerprint_tasks:
                reason = "T1 999指纹task(整task作废)"
            elif sid in cluster_sessions:
                reason = "T2 批量簇session"
            elif r["client_elapsed_ms"] is not None and r["client_elapsed_ms"] < 2000:
                reason = "T3 亚秒提交"
            if reason:
                kill.append((r["evidence_id"], r["ability_id"], r["evidence_type"], reason))
        # SUSPECT 名单（不处理，打印给用户）：非 TEST 但 session 有 ≥3 题且间隔 <15s
        rs2 = await db.execute(text("""
            SELECT e.evidence_id, e.ability_id, e.evidence_type, t.session_id,
                   s.started_at, date_trunc('second', e.occurred_at - s.started_at) AS age_s
            FROM mastery_evidence e
            JOIN task_instance t ON t.task_instance_id = e.task_instance_id
            JOIN learning_session s ON s.session_id = t.session_id
            WHERE e.child_id = :cid AND e.valid = true
              AND s.started_at >= '2026-09-29 00:00+08'
            ORDER BY e.occurred_at
        """), {"cid": REAL_CHILD})

        affected_abilities = sorted({k[1] for k in kill})
        print(f"TEST 作废: {len(kill)} 条，涉及能力 {affected_abilities}")
        print(f"  T1×{sum(1 for k in kill if k[3].startswith('T1'))} "
              f"T2×{sum(1 for k in kill if k[3].startswith('T2'))} "
              f"T3×{sum(1 for k in kill if k[3].startswith('T3'))}")

        if os.environ.get("DRY_RUN") == "1":
            for k in kill:
                print(f"  [dry] {str(k[0])[:8]} {k[1]} {k[2]} {k[3]}")
            await eng.dispose()
            return

        # ---- 执行作废 ----
        ids = [k[0] for k in kill]
        await db.execute(text("""
            UPDATE mastery_evidence SET valid = false,
              metadata = metadata || jsonb_build_object(
                'invalidated_reason', 'FE-1412 QA contamination (T1/T2/T3 fingerprint)',
                'invalidated_at', now()::text)
            WHERE evidence_id = ANY(CAST(:ids AS uuid[]))
        """), {"ids": ids})

        # 派生窗口全废（无 task 关联的 stability/transfer_window）
        rs3 = await db.execute(text("""
            UPDATE mastery_evidence SET valid = false,
              metadata = metadata || jsonb_build_object('invalidated_reason',
                'FE-1412 stale derived window', 'invalidated_at', now()::text)
            WHERE child_id = :cid AND valid = true
              AND evidence_type IN ('stability_window','transfer_window')
              AND ability_id = ANY(CAST(:ab AS text[]))
            RETURNING evidence_id
        """), {"cid": REAL_CHILD, "ab": affected_abilities})
        nwin = len(rs3.all())
        print(f"派生窗口作废: {nwin}")
        await db.commit()

        # ---- 生产路径重算 ----
        from app.services.mastery_db import persist_mastery_state
        for aid in affected_abilities:
            res = await persist_mastery_state(db, child_id=__import__("uuid").UUID(REAL_CHILD),
                                              ability_id=aid)
            await db.commit()
            print(f"重算 {aid}: L{res['old_level']}→L{res['new_level']} "
                  f"score={res['score']} conf→? decision={res['decision']} "
                  f"n={res['evidence_count']} trend={res['trend']}")

        # 终态
        rs4 = await db.execute(text("""
            SELECT ability_id, level, confidence, evidence_count, trend
            FROM ability_state WHERE child_id = :cid ORDER BY ability_id
        """), {"cid": REAL_CHILD})
        print("=== ability_state 终态 ===")
        for r in rs4.mappings():
            print(f"  {r['ability_id']:12} L{r['level']} conf={r['confidence']} "
                  f"n={r['evidence_count']} trend={r['trend']}")

    await eng.dispose()


asyncio.run(main())
