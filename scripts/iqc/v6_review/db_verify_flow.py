#!/usr/bin/env python3
"""FE-1445 复审：核对真实作答在库里留下的证据链（只读）。

必须在**清理之前**跑——清理之后这些行就没了，届时无法再判断
「学习证据、成长状态是否正确」。

判据全部来自 run.json 里记录的实测值（task/rvid/答案）与数据库现状的比对，
不是「有行就算过」：数量、归属、内容三层都要对上。

用法：
    export DATABASE_URL="postgresql://..."
    python scripts/iqc/v6_review/db_verify_flow.py output/v6_review/real_flow_run.json

rc：0 全通过；1 有断言不通过；2 环境/参数问题。
"""
from __future__ import annotations

import json
import os
import sys
import uuid

import psycopg

CHECKS: list[tuple[bool, str, str]] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    CHECKS.append((bool(cond), label, detail))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: db_verify_flow.py <run.json>", file=sys.stderr)
        return 2
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("FATAL: 未设置 DATABASE_URL", file=sys.stderr)
        return 2

    with open(sys.argv[1], encoding="utf-8") as f:
        run = json.load(f)

    cid = uuid.UUID(run["guestId"])
    ti = uuid.UUID(run["taskInstanceId"])
    rvid = uuid.UUID(run["resourceVersionId"])
    truth_answer = str(run["truth"]["answer"])

    with psycopg.connect(url) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        with conn.cursor() as cur:
            def one(sql, params=()):
                cur.execute(sql, params)
                return cur.fetchone()

            def allrows(sql, params=()):
                cur.execute(sql, params)
                return cur.fetchall()

            # 归属：child 与 guest_identity 必须同时存在且 active
            row = one("select nickname, status from child where child_id=%s", (cid,))
            check(row is not None and row[1] == "active", "child 存在且 active", str(row))
            row = one("select status, expires_at from guest_identity where child_id=%s", (cid,))
            check(row is not None and row[0] == "active", "guest_identity active", str(row[0] if row else None))

            # 会话：1 个，math
            sess = allrows("select session_id, subject from learning_session where child_id=%s", (cid,))
            check(len(sess) == 1 and sess[0][1] == "math", "学习会话 1 个且为 math",
                  f"{len(sess)} 个 {[s[1] for s in sess]}")

            # 题目：1 个，且就是 E2E 拿到的那个 resource_version
            tasks = allrows(
                "select task_instance_id, resource_version_id, status from task_instance where child_id=%s",
                (cid,),
            )
            check(len(tasks) == 1 and tasks[0][1] == rvid, "task_instance 1 个且 rvid 与前端一致",
                  f"{len(tasks)} 个 rvid={tasks[0][1] if tasks else None}")

            # 作答：1 次，判分 true，答案与题库真值同，且带表示法
            att = allrows(
                """select a.attempt_no, a.correct, a.response
                   from attempt a join task_instance t using(task_instance_id)
                   where t.child_id=%s order by a.attempt_no""",
                (cid,),
            )
            check(len(att) == 1, "attempt 只有 1 次", f"{len(att)} 次")
            if att:
                _, correct, resp = att[0]
                got = str((resp or {}).get("answer"))
                check(correct is True, "判分 correct=true", str(correct))
                check(got == truth_answer, "落库答案 = 题库真值", f"{got!r} vs {truth_answer!r}")
                has_repr = isinstance((resp or {}).get("representation"), dict)
                check(has_repr, "作答带数学表示法（representation）", f"keys={list((resp or {}).keys())}")

            # 证据链
            ev = allrows("select event_type, count(*) from learning_event where child_id=%s group by 1", (cid,))
            ev_map = {k: int(v) for k, v in ev}
            check(ev_map.get("attempt_submitted") == 1, "learning_event 记录 attempt_submitted ×1", json.dumps(ev_map, ensure_ascii=False))

            me = allrows(
                "select ability_id, evidence_type, correctness, valid from mastery_evidence where child_id=%s",
                (cid,),
            )
            check(len(me) == 1, "mastery_evidence 1 条", f"{len(me)} 条 {me}")
            if me:
                ability, etype, correctness, valid = me[0]
                check(bool(valid) is True and correctness == 1,
                      "证据有效且判定为正确", f"ability={ability} type={etype} correctness={correctness} valid={valid}")

            st = allrows(
                "select ability_id, level, evidence_count from ability_state where child_id=%s",
                (cid,),
            )
            check(len(st) >= 1 and int(st[0][1]) >= 1, "ability_state 已推进（level>=1）",
                  f"{st}")

            # 配额：当天 1 条
            q = one("select count(*) from guest_daily_quota where child_id=%s", (cid,))
            check(q is not None and int(q[0]) == 1, "guest_daily_quota 当天 1 条", str(q[0]) if q else None)

            # 没有串到别的 child：本会话下不得出现属于别人的 task_instance
            # （第一版这里写成 `t.child_id <> cid and t.child_id = cid`，恒为空集，
            #  是「写了但永远通过」的假判据，已换掉。）
            if sess:
                leak = one(
                    "select count(*) from task_instance where session_id=%s and child_id <> %s",
                    (sess[0][0], cid),
                )
                check(leak is not None and int(leak[0]) == 0, "本会话下无他人 task_instance（防串用）",
                      str(leak[0]) if leak else None)
            else:
                check(False, "本会话下无他人 task_instance（防串用）", "会话缺失，无法判定")

    for ok, label, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    failed = [c for c in CHECKS if not c[0]]
    print(f"\n结果：{len(CHECKS) - len(failed)}/{len(CHECKS)} PASS -> {'OK' if not failed else 'FAIL'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
