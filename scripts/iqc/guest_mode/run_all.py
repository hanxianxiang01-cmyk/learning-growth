"""游客模式门禁总入口。

为什么需要它（本项目形态 33 的教训）：判据算了但退出码没算它 → 屏幕打 FAIL、
rc 仍 0。所以这里显式收集每个子判据的退出码，任一非 0 即整体非 0，
并且把 rc=2（环境/解析失效）与 rc=1（判据失败）区分开——2 表示"没跑起来"，
不能当成"通过"也不能当成"代码有缺陷"。

包含：
  1. audit_ddl_orm.py        DDL ↔ ORM 双向对账（4 张游客表，纯静态）
  2. audit_endpoint_guard.py 对外 24 个端点的鉴权覆盖（纯静态）
  3. audit_purge_order.py    清理删除顺序 vs 数据库外键图（**需 DATABASE_URL**）

第 3 项标记 requires_db：未设 DATABASE_URL 时**明确 SKIP**，不算 rc=2——
「没配库」不是「判据没跑起来」，把它报成 2 会让纯静态运行永远失败。

**不包含** acceptance_ch9.py：它会真实写库（造游客/答题/触发清理），属验收而
非门禁，须显式带 DATABASE_URL 手动跑，不能进默认门禁（否则每次门禁都动生产库）。

退出码语义：
  0 = 全部通过（或需 DB 的项因未配库被 SKIP）
  1 = 至少一条判据失败
  2 = 至少一个脚本环境/解析失效（或本身缺失）

用法：
    # 纯静态（无 DB）
    ~/.workbuddy/binaries/python/envs/learning-engine/bin/python scripts/iqc/guest_mode/run_all.py
    # 含外键顺序审计（连只读库即可）
    DATABASE_URL=postgresql+psycopg://user:CHANGE_ME@HOST:PORT/DB \
      ~/.workbuddy/binaries/python/envs/learning-engine/bin/python scripts/iqc/guest_mode/run_all.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# (标题, 脚本, 是否需要 DATABASE_URL)
CHECKS = [
    ("DDL ↔ ORM 双向对账", "audit_ddl_orm.py", False),
    ("对外端点鉴权覆盖", "audit_endpoint_guard.py", False),
    ("清理删除顺序 vs 外键图", "audit_purge_order.py", True),
]

# 需要透传给子脚本的环境变量（用于变异验证：证明总入口真的传播子判据失败）
PASSTHROUGH = ("IQC_DDL_PATH", "DATABASE_URL")


def main() -> int:
    worst = 0  # 0 < 1 < 2 的严重度排序：2（没跑起来）最需要人介入
    env = dict(os.environ)
    has_db = bool(env.get("DATABASE_URL"))
    injected = {k: ("***" if k == "DATABASE_URL" else env[k]) for k in PASSTHROUGH if k in env}
    print(f"游客模式门禁：{len(CHECKS)} 项（DATABASE_URL {'已设' if has_db else '未设'}）")
    if injected:
        print(f"（透传：{sorted(injected)}）")
    print("#" * 72)

    skipped = 0
    for title, script, requires_db in CHECKS:
        path = HERE / script
        if not path.exists():
            print(f"\n[{title}] 脚本缺失：{path}")
            worst = max(worst, 2)
            continue
        if requires_db and not has_db:
            print(f"\n[{title}] SKIP（需 DATABASE_URL，本轮未配库）")
            skipped += 1
            continue
        print(f"\n[{title}] → {script}")
        print("-" * 72)
        proc = subprocess.run(
            [sys.executable, str(path)], cwd=str(HERE.parents[2]), env=env
        )
        rc = proc.returncode
        print(f"[{title}] rc={rc}")
        if rc == 0:
            continue
        if rc == 1:
            worst = max(worst, 1)
        else:
            # 非 0/1（含 2、崩溃码）一律按"环境/解析失效"处理
            worst = 2

    print("\n" + "#" * 72)
    ran = len(CHECKS) - skipped
    if worst == 0:
        print(f"总结论：PASS（实跑 {ran} 项通过，SKIP {skipped} 项需 DB）")
    elif worst == 1:
        print("总结论：FAIL（有判据不通过，见上方明细）")
    else:
        print("总结论：环境/解析失效 rc=2（有判据没能跑起来，不能视为通过）")
    return worst


if __name__ == "__main__":
    sys.exit(main())