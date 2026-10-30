#!/usr/bin/env python3
"""FE-1445 复审：精确清理本轮 E2E 造出来的游客（零残留）。

**为什么不用「按基线差集全清」那一版**：那种写法会把「今天新产生的任何
child」一并删掉。本轮复核跑在生产库上，只能删自己刚造的那几个 id。

删除顺序不手写——直接调用应用的 `purge_one_guest()`（它的顺序是对
pg_constraint 外键图拓扑核过的）。手抄一份顺序等于凭记忆写，必然漂移。

依赖主分支的后端代码（V6 分支没有 guest 实现），所以要用 PYTHONPATH 指过去：

    export DATABASE_URL="postgresql://..."
    PYTHONPATH=<主仓库>/apps/learning-api \\
      python scripts/iqc/v6_review/db_purge.py --from-run output/v6_review/real_flow_run.json

rc：0 = 全部清理成功；1 = 有游客清理失败（会列出来）；2 = 参数/环境问题。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid

try:
    from app.core.database import AsyncSessionLocal
    from app.services.guest_cleanup import purge_one_guest
except ImportError:
    print(
        "FATAL: 需要 PYTHONPATH 指向主分支的 apps/learning-api（guest 实现在那里）",
        file=sys.stderr,
    )
    sys.exit(2)


async def _purge(child_ids: list[uuid.UUID]) -> int:
    failed = 0
    async with AsyncSessionLocal() as db:
        for cid in child_ids:
            try:
                counts = await purge_one_guest(db, child_id=cid)
                await db.commit()
                nonzero = {k: v for k, v in counts.items() if v}
                print(f"[PASS] purge {cid} -> {json.dumps(nonzero, ensure_ascii=False)}")
            except Exception as e:  # noqa: BLE001
                await db.rollback()
                failed += 1
                print(f"[FAIL] purge {cid} -> {type(e).__name__}: {e}", file=sys.stderr)
    return failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--child-id", action="append", default=[])
    ap.add_argument("--from-run", action="append", default=[])
    args = ap.parse_args()

    if not os.environ.get("DATABASE_URL"):
        print("FATAL: 未设置 DATABASE_URL", file=sys.stderr)
        return 2

    ids = [uuid.UUID(x) for x in args.child_id]
    for path in args.from_run:
        try:
            with open(path, encoding="utf-8") as f:
                run = json.load(f)
        except Exception as e:  # noqa: BLE001
            print(f"FATAL: 读 {path} 失败 {e}", file=sys.stderr)
            return 2
        if run.get("guestId"):
            ids.append(uuid.UUID(run["guestId"]))

    # 去重且保序
    seen, uniq = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            uniq.append(i)

    if not uniq:
        print("没有需要清理的游客 id（--child-id / --from-run 都没给到）", file=sys.stderr)
        return 2

    print(f"待清理 {len(uniq)} 个游客：{', '.join(str(i) for i in uniq)}")
    failed = asyncio.run(_purge(uniq))
    print(f"\n结果：{len(uniq) - failed}/{len(uniq)} 清理成功")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
