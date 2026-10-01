"""一次性回填：resource_version.mastery_rule.context_family + 历史证据 ctx（AC-04 执行）。

幂等：已回填（值一致）的行跳过；REVIEW 题保持 NULL，不猜测。
执行：python scripts/backfill_context_family.py
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.content.context_family import canonicalize_context_family
from app.content.context_family_map import STEM_CONTEXT_FAMILY
from app.models import MasteryEvidence, Resource, ResourceVersion, TaskInstance


async def main():
    url = None
    import os
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # 1. mastery_rule 回填（保留已有键，只增 context_family / transfer_capable）
        rows = (
            await db.execute(
                select(ResourceVersion, Resource.ability_id)
                .join(Resource, Resource.resource_id == ResourceVersion.resource_id)
                .where(ResourceVersion.review_status == "published")
            )
        ).all()

        updated = skipped = review_null = 0
        for rv, _aid in rows:
            stem = rv.content.get("stem") if isinstance(rv.content, dict) else None
            if stem not in STEM_CONTEXT_FAMILY:
                print(f"WARN: 未匹配到映射 stem={str(stem)[:30]}")
                skipped += 1
                continue
            raw = STEM_CONTEXT_FAMILY[stem]
            family = canonicalize_context_family(raw)  # 非法值直接抛错终止
            rule = dict(rv.mastery_rule) if isinstance(rv.mastery_rule, dict) else {}
            if family is None:
                review_null += 1
                # REVIEW 题：不写 context_family（保持无判定），只确保 transfer_capable 存在
                rule.setdefault("transfer_capable", rv.transfer_distance is not None)
            else:
                if rule.get("context_family") == family:
                    continue
                rule["context_family"] = family
                rule.setdefault("transfer_capable", rv.transfer_distance is not None)
            rv.mastery_rule = rule
            updated += 1
        await db.commit()
        print(f"mastery_rule 回填：updated={updated} review_null={review_null} skipped={skipped}")

        # 2. 历史原子证据 context_family 回补（valid=true 且 ctx 为 NULL 的行，经 task→rv 联查）
        await db.execute(text("""
            UPDATE mastery_evidence e
            SET context_family = NULLIF(rv.mastery_rule->>'context_family', '')
            FROM task_instance t
            JOIN resource_version rv ON rv.resource_version_id = t.resource_version_id
            WHERE e.task_instance_id = t.task_instance_id
              AND e.valid = true
              AND e.context_family IS NULL
              AND rv.mastery_rule->>'context_family' IS NOT NULL
        """))
        r2 = await db.execute(text(
            "select count(*) from mastery_evidence where valid=true and context_family is not null"
        ))
        print(f"历史证据 ctx 回补后非空数: {r2.scalar()}")

        # 3. 验收检查（§7 硬性）
        r3 = await db.execute(text("""
            select rv.mastery_rule->>'context_family' as fam, count(*)
            from resource_version rv join resource r on r.resource_id = rv.resource_id
            where rv.review_status='published'
            group by 1 order by 2 desc
        """))
        print("=== family → question count ===")
        for fam, cnt in r3.fetchall():
            print(f"  {fam or '(NULL/REVIEW)'}: {cnt}")
        r4 = await db.execute(text("""
            select rv.mastery_rule->>'context_family' as fam, count(*)
            from resource_version rv join resource r on r.resource_id = rv.resource_id
            where rv.review_status='published' and rv.transfer_distance is not null
            group by 1
        """))
        print("=== family → transfer 迁移题覆盖 ===")
        for fam, cnt in r4.fetchall():
            print(f"  {fam or '(NULL/REVIEW)'}: {cnt}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
