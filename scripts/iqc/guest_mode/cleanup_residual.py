"""清理本轮验收残留，恢复到基线快照状态。

锚点（两个都查，取并集，避免漏删）：
  1. guest_identity 里的所有 child_id（游客一定在表里）
  2. 不在基线名单里的 child_id（基线 = db_baseline_before.json 的 20 个）

删除顺序由 pg_constraint 的真实外键图拓扑排序得出（不是凭记忆写）：
  learning_event → mastery_evidence → attempt → audio_asset → growth_report
  → task_instance → learning_session → learning_plan/ability_state/consent_record
  → growth_snapshot/textbook_profile → guest_daily_quota/guest_session
  → guest_identity → child → guardian

关键：learning_event 与 mastery_evidence 都外键引用 attempt，
所以必须在 attempt 之前删——原 purge_one_guest 写反了，这就是崩溃原因。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg

REPO = Path(__file__).resolve().parents[3]
BASELINE = REPO / "output" / "guest_mode" / "db_baseline_before.json"

DSN = (
    f"host={os.environ['PGHOST']} port={os.environ['PGPORT']} user={os.environ['PGUSER']} "
    f"password={os.environ['PGPASSWORD']} dbname={os.environ['PGDATABASE']} connect_timeout=20"
)

# 拓扑序：先删引用别人的表
ORDER = [
    ("learning_event", "child_id"),
    ("mastery_evidence", "child_id"),
    ("attempt", None),           # 按 task_instance_id 删
    ("audio_asset", "child_id"),
    ("growth_report", "child_id"),
    ("task_instance", "child_id"),
    ("learning_session", "child_id"),
    ("learning_plan", "child_id"),
    ("ability_state", "child_id"),
    ("consent_record", "child_id"),
    ("growth_snapshot", "child_id"),
    ("textbook_profile", "child_id"),
    ("guest_daily_quota", "child_id"),
    ("guest_session", "child_id"),
    ("guest_identity", "child_id"),
    ("child", "child_id"),
]


def main() -> int:
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_child = set(base["ids"]["child"])
    base_guardian = set(base["ids"]["guardian"])
    print(f"基线：child {len(base_child)} 个 / guardian {len(base_guardian)} 个")

    with psycopg.connect(DSN, autocommit=False) as c, c.cursor() as cur:
        # 1. 锚点：guest_identity 里的 + 不在基线名单里的
        cur.execute("SELECT child_id::text FROM guest_identity")
        from_identity = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT child_id::text FROM child")
        all_child = {r[0] for r in cur.fetchall()}
        extra = all_child - base_child
        targets = sorted(from_identity | extra)
        print(f"guest_identity 内 {len(from_identity)} 个；超出基线 {len(extra)} 个")
        print(f"待删并集 {len(targets)} 个：{targets}")

        if not targets:
            print("无需清理")
        else:
            # 2. 按拓扑序删
            for tbl, col in ORDER:
                if tbl == "attempt":
                    cur.execute(
                        "DELETE FROM attempt WHERE task_instance_id IN "
                        "(SELECT task_instance_id FROM task_instance WHERE child_id = ANY(%s))",
                        ([t for t in targets],),
                    )
                elif col:
                    cur.execute(f"DELETE FROM {tbl} WHERE {col} = ANY(%s)", (targets,))
                print(f"   {tbl:<20} 删 {cur.rowcount} 行")

            # 3. 孤儿 guardian（名下已无 child）
            cur.execute(
                "DELETE FROM guardian WHERE guardian_id NOT IN (SELECT guardian_id FROM child)"
            )
            print(f"   {'guardian(孤儿)':<20} 删 {cur.rowcount} 行")

            # 4. 运行记录表也清（本轮验收产物）
            cur.execute("DELETE FROM guest_cleanup_run")
            print(f"   {'guest_cleanup_run':<20} 删 {cur.rowcount} 行")

        # 5. commit 前自检：必须与基线完全一致，否则回滚
        checks = []
        for t in ("child", "guardian", "guest_identity", "guest_session",
                  "guest_daily_quota", "guest_cleanup_run", "task_instance",
                  "attempt", "learning_event", "learning_session",
                  "mastery_evidence", "ability_state"):
            cur.execute(f"SELECT count(*) FROM {t}")
            checks.append((t, cur.fetchone()[0]))
        print("\n清理后计数：")
        for t, n in checks:
            b = base["tables"].get(t)
            mark = "OK" if b == n else ("(guest 表基线为 0)" if b is None else "!! 不一致")
            print(f"   {t:<20}{n:<8} 基线={b} {mark}")

        bad = [
            (t, n) for t, n in checks
            if base["tables"].get(t) is not None and base["tables"][t] != n
        ]
        guest_left = [
            (t, n) for t, n in checks
            if t.startswith("guest_") and t != "guest_cleanup_run" and n != 0
        ]
        if bad or guest_left:
            print(f"\n[ROLLBACK] 未达基线：{bad} guest残留={guest_left}")
            c.rollback()
            return 1
        c.commit()
        print("\n[COMMIT] 已恢复到基线")

    # 6. 复核：resource_version 分毫未动
    with psycopg.connect(DSN, autocommit=True) as c, c.cursor() as cur:
        cur.execute("SELECT count(*) FROM resource_version")
        rv = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM resource_version WHERE review_status='published'")
        pub = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM resource")
        res = cur.fetchone()[0]
    ok = (rv == base["tables"]["resource_version"]
          and pub == base["resource_version_by_status"]["published"]
          and res == base["tables"]["resource"])
    print(f"题库复核：resource_version={rv}（基线 {base['tables']['resource_version']}）"
          f" published={pub}（基线 {base['resource_version_by_status']['published']}）"
          f" resource={res}（基线 {base['tables']['resource']}）→ {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
