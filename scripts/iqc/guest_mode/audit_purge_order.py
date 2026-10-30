"""清理删除顺序审计：以数据库外键图为唯一事实源，验证 purge_one_guest 的删除顺序合法。

**为什么需要这个判据**：10-29 实测发现 purge_one_guest 把 `DELETE attempt` 排在
`DELETE learning_event` 之前，而 learning_event.attempt_id 外键引用 attempt →
真实库上清理 100% 失败（且失败者保持 active 自动重试 → 永远失败永远重试）。
单元测试抓不到：它没有造真实的 event→attempt 关联行。

**判据**（形态 42：两个独立事实源互核）：
  事实源 A：live DB 的 pg_constraint 外键图（权威，不可辩驳）
  事实源 B：purge_one_guest 源码里的 delete() 调用顺序（AST 解析，不是文本猜测）
  要求：B 必须是 A 的一个合法拓扑序——每条外键 (child_tbl → parent_tbl)，
        若两表都在 B 中出现，则 child_tbl 必须先于 parent_tbl 被删。

另核（防「顺序对了但漏表」）：
  C. 每张按 child_id 可删的业务表都必须出现在 B 中（漏表 = 清理留残留）

用法：
    DATABASE_URL=postgresql+psycopg://user:CHANGE_ME@HOST:PORT/DB \
    ~/.workbuddy/binaries/python/envs/learning-engine/bin/python scripts/iqc/guest_mode/audit_purge_order.py

退出码：0 = 顺序合法；1 = 判据失败；2 = 环境/连不上库（不算判据失败）。
"""
from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
API = REPO / "apps" / "learning-api"
CLEANUP_PY = API / "app" / "services" / "guest_cleanup.py"

# 游客清理涉及的业务表（child 维度）。resource/resource_version 是题库，不在清理范围。
EXPECTED_TABLES = {
    "learning_event", "mastery_evidence", "attempt", "task_instance",
    "learning_session", "learning_plan", "ability_state", "audio_asset",
    "consent_record", "growth_report", "growth_snapshot", "textbook_profile",
    "guest_daily_quota", "guest_session", "guest_identity", "child", "guardian",
}

# ORM 类名 → 表名
CLASS2TABLE = {
    "LearningEvent": "learning_event",
    "MasteryEvidence": "mastery_evidence",
    "Attempt": "attempt",
    "TaskInstance": "task_instance",
    "LearningSession": "learning_session",
    "LearningPlan": "learning_plan",
    "AbilityState": "ability_state",
    "AudioAsset": "audio_asset",
    "ConsentRecord": "consent_record",
    "GrowthReport": "growth_report",
    "GrowthSnapshot": "growth_snapshot",
    "TextbookProfile": "textbook_profile",
    "GuestDailyQuota": "guest_daily_quota",
    "GuestSession": "guest_session",
    "GuestIdentity": "guest_identity",
    "Child": "child",
    "Guardian": "guardian",
}


def extract_order() -> list[str]:
    """AST 解析 purge_one_guest，按执行顺序抽出被 delete 的表名列表。

    注意 _PURGE_BY_CHILD 循环：`delete(model)` 里的 model 是变量，需展开成
    该列表里的实际表名（在它出现的位置）。
    """
    src = CLEANUP_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 先解析模块级 _PURGE_BY_CHILD 的内容（保序）
    loop_tables: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_PURGE_BY_CHILD" for t in node.targets
        ):
            for elt in node.value.elts:  # [(Model, "child_id"), ...]
                if isinstance(elt, ast.Tuple) and isinstance(elt.elts[0], ast.Name):
                    loop_tables.append(CLASS2TABLE.get(elt.elts[0].id, elt.elts[0].id))

    fn = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == "purge_one_guest":
            fn = node
            break
    if fn is None:
        raise SystemExit("[rc=2] 找不到 purge_one_guest")

    # ast.walk 不保证语句顺序 → 必须按 (lineno, col_offset) 重排，
    # 否则抽出来的"顺序"是遍历顺序而非执行顺序，判据会失真。
    calls = sorted(
        [n for n in ast.walk(fn)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "delete"],
        key=lambda n: (n.lineno, n.col_offset),
    )
    order: list[str] = []
    for n in calls:
        if not n.args:
            continue
        a = n.args[0]
        if isinstance(a, ast.Name):
            if a.id == "model":
                order.extend(loop_tables)  # 循环变量：就地展开成列表里的实际表名
            else:
                order.append(CLASS2TABLE.get(a.id, a.id))
        elif isinstance(a, ast.Attribute):
            order.append(CLASS2TABLE.get(a.attr, a.attr))
    return order


def fetch_fk_graph() -> list[tuple[str, str, str]]:
    """从 live DB 抽 (child_tbl, parent_tbl, on_delete)。连不上 → rc=2。"""
    import psycopg

    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    try:
        with psycopg.connect(url, autocommit=True, connect_timeout=20) as c, c.cursor() as cur:
            cur.execute("""
                SELECT conrelid::regclass::text, confrelid::regclass::text, confdeltype
                FROM pg_constraint WHERE contype='f'
            """)
            return [(r[0], r[1], r[2]) for r in cur.fetchall()]
    except Exception as e:
        print(f"[rc=2] 连不上数据库（环境问题，非判据失败）：{type(e).__name__}: {e}")
        raise SystemExit(2)


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("[rc=2] 未设 DATABASE_URL")
        return 2
    if not CLEANUP_PY.exists():
        print(f"[rc=2] 找不到 {CLEANUP_PY}")
        return 2

    order = extract_order()
    fks = fetch_fk_graph()

    print(f"purge_one_guest 删除顺序（AST 解析，{len(order)} 步）：")
    for i, t in enumerate(order, 1):
        print(f"  {i:>2}. {t}")
    print(f"\n外键图：{len(fks)} 条（事实源 A = live DB pg_constraint）")

    fails: list[str] = []
    # 首次出现位置 = 该表被删的时机
    first_pos = {}
    for i, t in enumerate(order):
        first_pos.setdefault(t, i)

    print("\n=== A/B 判据：每条相关外键，子表必须先于父表被删 ===")
    checked = 0
    for child_t, parent_t, on_del in sorted(fks):
        if child_t not in first_pos or parent_t not in first_pos:
            continue  # 有一方不在清理范围（如 resource_version）
        checked += 1
        if on_del == "c":  # CASCADE：父删时自动带走子，顺序不敏感
            print(f"  SKIP(cascade) {child_t} → {parent_t}")
            continue
        ok = first_pos[child_t] < first_pos[parent_t]
        if not ok:
            fails.append(
                f"顺序违规：{child_t}(第{first_pos[child_t]+1}步) 必须在 "
                f"{parent_t}(第{first_pos[parent_t]+1}步) 之前删"
            )
        print(f"  {'OK ' if ok else 'FAIL'} {child_t:<20}(#{first_pos[child_t]+1:<3}) "
              f"→ {parent_t:<20}(#{first_pos[parent_t]+1})")
    print(f"  共核 {checked} 条相关外键")

    # C. 漏表检查
    print("\n=== C 判据：清理范围内的表一个不漏 ===")
    in_order = set(order)
    missing = sorted(EXPECTED_TABLES - in_order)
    extra = sorted(in_order - EXPECTED_TABLES)
    if missing:
        fails.append(f"漏表（清理会留残留）：{missing}")
    if extra:
        fails.append(f"意外多出的表（核对 EXPECTED_TABLES 是否过期）：{extra}")
    print(f"  期望 {len(EXPECTED_TABLES)} 张，实际覆盖 {len(in_order & EXPECTED_TABLES)} 张")
    print(f"  漏={missing or '无'}  多={extra or '无'}")

    print("\n" + "=" * 66)
    if fails:
        print(f"结论：FAIL（{len(fails)} 项）")
        for f in fails:
            print("  - " + f)
        return 1
    print("结论：PASS（删除顺序是外键图的合法拓扑序，且无漏表）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
