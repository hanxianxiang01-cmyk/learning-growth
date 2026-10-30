#!/usr/bin/env python3
"""FE-1445 复审：生产库快照与零残留对账（QA 池除外）。

用法：
    export DATABASE_URL="postgresql://..."
    python scripts/iqc/v6_review/db_snapshot.py guard
    python scripts/iqc/v6_review/db_snapshot.py capture --out before.json
    ...跑真实数据 E2E / 视觉采集...
    python scripts/iqc/v6_review/db_snapshot.py capture --out after.json
    python scripts/iqc/v6_review/db_snapshot.py compare before.json after.json

设计约束（为什么这么写）：
1. **只读**：capture 全程 `SET TRANSACTION READ ONLY`，不做任何 DML。
2. **rc 三值**：0 = 对账通过；1 = 对账不通过；2 = 无法判定（环境/参数问题）。
   所有断言都参与最终 rc —— 出现过「屏幕 FAIL 而 rc=0」的失效形态。
3. **表清单由目录推导**，不写字面量列表（写死的清单会在加表后静默漏检）。
4. **排除 QA 池**：`…0099` 是 19 个 E2E/视觉采集的基准池，
   `POST /v1/guest/qa-session` 会给它建百年有效期的身份，治理上由 QA 脚本管理、
   清理任务不得触碰。把它算进「零残留」只会导致两种坏结果：删掉 QA 池（越界），
   或永远红（判据作废）。因此计数一律取「非 QA 池」口径，同时**另存全量计数**备查。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

try:
    import psycopg
except ImportError:  # pragma: no cover
    print("FATAL: 需要 psycopg（用 learning-engine venv 的 python）", file=sys.stderr)
    sys.exit(2)

QA_CHILD_ID = "00000000-0000-0000-0000-000000000099"
ID_SET_TABLES = ("child", "guardian", "guest_identity")
PUBLISHED_KEY = "resource_version_by_review_status"
GUEST_TABLES = ("guest_identity", "guest_session", "guest_daily_quota")


def _connect(url: str):
    conn = psycopg.connect(url)
    conn.execute("SET TRANSACTION READ ONLY")
    return conn


def _tables_with_column(cur, column: str) -> set[str]:
    cur.execute(
        "select table_name from information_schema.columns "
        "where table_schema='public' and column_name=%s",
        (column,),
    )
    return {r[0] for r in cur.fetchall()}


def capture(url: str) -> dict:
    with _connect(url) as conn, conn.cursor() as cur:
        cur.execute("select current_user, current_database()")
        user, db = cur.fetchone()
        cur.execute(
            "select table_name from information_schema.tables "
            "where table_schema='public' and table_type='BASE TABLE' order by 1"
        )
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            print("FATAL: public schema 无表，连错库了？", file=sys.stderr)
            sys.exit(2)

        counts = {}
        for t in tables:
            cur.execute(f'select count(*) from "{t}"')
            counts[t] = int(cur.fetchone()[0])

        # 排除 QA 池后的计数（零残留判据用这一份）
        has_child = _tables_with_column(cur, "child_id")
        counts_ex_qa = {}
        for t in tables:
            if t in has_child:
                cur.execute(f'select count(*) from "{t}" where child_id <> %s', (QA_CHILD_ID,))
                counts_ex_qa[t] = int(cur.fetchone()[0])
            elif t == "attempt":
                cur.execute(
                    "select count(*) from attempt a join task_instance ti using(task_instance_id) "
                    "where ti.child_id <> %s",
                    (QA_CHILD_ID,),
                )
                counts_ex_qa[t] = int(cur.fetchone()[0])
            else:
                counts_ex_qa[t] = counts[t]

        ids = {}
        for t in ID_SET_TABLES:
            if t not in tables:
                continue
            pk = "guardian_id" if t == "guardian" else "child_id"
            if t == "guest_identity":
                cur.execute(
                    f'select {pk}::text from "{t}" where child_id <> %s order by 1', (QA_CHILD_ID,))
            elif t == "child":
                cur.execute(f'select {pk}::text from "{t}" where child_id <> %s order by 1', (QA_CHILD_ID,))
            else:
                cur.execute(f'select {pk}::text from "{t}" order by 1')
            ids[t] = [r[0] for r in cur.fetchall()]

        rv = {}
        if "resource_version" in tables:
            cur.execute("select review_status, count(*) from resource_version group by 1 order by 1")
            rv = {str(k): int(v) for k, v in cur.fetchall()}

        guest_detail = {}
        if "guest_identity" in tables:
            cur.execute(
                "select coalesce(status,'?'), count(*) from guest_identity "
                "where child_id <> %s group by 1 order by 1", (QA_CHILD_ID,))
            guest_detail["by_status_ex_qa"] = {str(k): int(v) for k, v in cur.fetchall()}

    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "db": db,
        "user": user,
        "qa_child_excluded": QA_CHILD_ID,
        "tables": counts,             # 全量（备查）
        "tables_ex_qa": counts_ex_qa,  # 判据口径
        PUBLISHED_KEY: rv,
        "id_sets": ids,
        "guest_identity_detail": guest_detail,
    }


def compare(before: dict, after: dict) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True

    def check(cond: bool, label: str, detail: str = "") -> None:
        nonlocal ok
        mark = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        lines.append(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))

    check(before.get("db") == after.get("db") and before.get("user") == after.get("user"),
          "同一库同一用户",
          f"{before.get('user')}@{before.get('db')} vs {after.get('user')}@{after.get('db')}")

    bt = before.get("tables_ex_qa") or before.get("tables", {})
    at = after.get("tables_ex_qa") or after.get("tables", {})
    all_tables = sorted(set(bt) | set(at))
    drift = [(t, bt.get(t), at.get(t)) for t in all_tables if bt.get(t) != at.get(t)]
    check(not drift, f"除 QA 池外 {len(all_tables)} 张表行数无漂移",
          "; ".join(f"{t}: {b}->{a}" for t, b, a in drift) if drift else "0 张表变化")

    b_pub = before.get(PUBLISHED_KEY, {}).get("published")
    a_pub = after.get(PUBLISHED_KEY, {}).get("published")
    check(b_pub == a_pub, "已发布题量未变", f"published {b_pub} -> {a_pub}")
    check(before.get(PUBLISHED_KEY) == after.get(PUBLISHED_KEY),
          "resource_version 各状态计数无漂移",
          json.dumps({"before": before.get(PUBLISHED_KEY), "after": after.get(PUBLISHED_KEY)},
                     ensure_ascii=False))

    for t in ID_SET_TABLES:
        b_ids, a_ids = before.get("id_sets", {}).get(t), after.get("id_sets", {}).get(t)
        if b_ids is None and a_ids is None:
            continue
        b_set, a_set = set(b_ids or []), set(a_ids or [])
        check(b_set == a_set, f"{t} 身份集合逐 id 一致",
              f"+{sorted(a_set - b_set)} -{sorted(b_set - a_set)}"
              if b_set != a_set else f"{len(b_set)} 个 id 全同")

    for t in GUEST_TABLES:
        n = at.get(t)
        if n is None:
            continue
        check(n == 0, f"{t} 除 QA 池外归零", f"{n} 行")

    return ok, lines


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capture")
    p_cap.add_argument("--out", required=True)

    p_cmp = sub.add_parser("compare")
    p_cmp.add_argument("before")
    p_cmp.add_argument("after")

    sub.add_parser("guard")

    args = ap.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("FATAL: 未设置 DATABASE_URL", file=sys.stderr)
        return 2

    if args.cmd == "guard":
        # 跑之前必须先确认没有遗留游客。否则 before 快照把遗留也算进去，
        # 之后的 compare 会「和遗留一起」比平——绿得毫无意义（假绿）。
        snap = capture(url)
        dirty = {t: snap["tables_ex_qa"].get(t, 0) for t in GUEST_TABLES}
        if any(dirty.values()):
            print(f"GUARD FAIL: 除 QA 池外还有遗留游客 {json.dumps(dirty)}，先清干净再跑", file=sys.stderr)
            print("  用 scripts/iqc/v6_review/db_purge.py --child-id <id> 精确清理", file=sys.stderr)
            return 1
        print(f"GUARD OK: 无遗留游客（QA 池已排除）；已发布题量 {snap[PUBLISHED_KEY].get('published')}")
        return 0

    if args.cmd == "capture":
        snap = capture(url)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        print(f"已写入 {args.out}  user={snap['user']} db={snap['db']} tables={len(snap['tables'])}")
        print("published =", snap[PUBLISHED_KEY].get("published"))
        return 0

    try:
        with open(args.before, encoding="utf-8") as f:
            before = json.load(f)
        with open(args.after, encoding="utf-8") as f:
            after = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"FATAL: 读快照失败 {e}", file=sys.stderr)
        return 2

    ok, lines = compare(before, after)
    print("\n".join(lines))
    passed = sum(1 for line in lines if line.startswith("[PASS]"))
    print(f"\n结果：{passed}/{len(lines)} PASS -> {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
