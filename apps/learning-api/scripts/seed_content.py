"""资源导入工具 —— 校验 + 幂等 seed（能力节点 + 资源包）。

用法：python scripts/seed_content.py
幂等：已存在则跳过（按 ability_id / title 判重）。
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.content.ability_seed import ABILITY_EDGES, ABILITY_NODES
from app.content.resource_seed import GOLD_RESOURCES
from app.core.config import get_settings
from app.models import AbilityEdge, AbilityNode, Resource, ResourceVersion


def _build_ui_schema_v1(r: dict) -> dict:
    """把 GOLD_RESOURCES 的 visual/tools 组装为 TaskUISchema V1。

    对齐前端 contracts.ts 的 ManipulativeTaskUiSchema / NumberTaskUiSchema：
    - 有 visual → kind="manipulative"，携带 visual + tools + response_schema
    - 无 visual → kind="number"，仅 prompt + response_schema
    representation_required 由是否提供可视化操作区决定（manipulative 必填，number 免填）。
    """
    stem = r["content"]["stem"]
    visual = r.get("visual")
    if visual is not None:
        return {
            "schema_version": "1.0",
            "kind": "manipulative",
            "prompt": stem,
            "answer_placeholder": "输入数字",
            "visual": visual,
            "tools": r.get("tools", []),
            "response_schema": {
                "type": "structured",
                "answer_type": "number",
                "representation_required": True,
            },
        }
    return {
        "schema_version": "1.0",
        "kind": "number",
        "prompt": stem,
        "answer_placeholder": "输入数字",
        "response_schema": {
            "type": "structured",
            "answer_type": "number",
            "representation_required": False,
        },
    }


async def seed(content_only: bool = True) -> dict:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    stats = {"abilities": 0, "edges": 0, "resources": 0, "versions": 0}

    async with Session() as db:
        # 1. 能力节点
        for a in ABILITY_NODES:
            exists = await db.get(AbilityNode, a["ability_id"])
            if exists:
                continue
            db.add(
                AbilityNode(
                    ability_id=a["ability_id"],
                    subject=a["subject"],
                    domain_code=a["domain_code"],
                    name=a["name"],
                    definition=a["definition"],
                    level_schema={
                        "levels": ["L0", "L1", "L2", "L3", "L4"],
                        "description": "应用题能力等级",
                    },
                )
            )
            stats["abilities"] += 1

        # 2. 依赖边
        for frm, to, rel in ABILITY_EDGES:
            pk = (frm, to, rel)
            exists = await db.get(AbilityEdge, pk)
            if exists:
                continue
            db.add(
                AbilityEdge(
                    from_ability_id=frm,
                    to_ability_id=to,
                    relation_type=rel,
                    strength="medium",
                )
            )
            stats["edges"] += 1

        # 3. 资源 + 版本
        for r in GOLD_RESOURCES:
            # 判重：同 ability + title
            result = await db.execute(
                select(Resource).where(
                    Resource.ability_id == r["ability_id"],
                    Resource.title == r["title"],
                )
            )
            resource = result.scalar_one_or_none()
            if resource is None:
                resource = Resource(
                    resource_id=uuid.uuid4(),
                    ability_id=r["ability_id"],
                    resource_type="word_problem",
                    title=r["title"],
                    status="published",
                    created_by="seed",
                )
                db.add(resource)
                await db.flush()
                stats["resources"] += 1

            # 版本（每资源一版，幂等跳过）
            rv_exists = await db.execute(
                select(ResourceVersion).where(
                    ResourceVersion.resource_id == resource.resource_id,
                    ResourceVersion.version_no == 1,
                )
            )
            if rv_exists.scalar_one_or_none():
                continue

            db.add(
                ResourceVersion(
                    resource_id=resource.resource_id,
                    version_no=1,
                    difficulty=r["difficulty"],
                    task_type=r["task_type"],
                    content=r["content"],
                    ui_schema=_build_ui_schema_v1(r),
                    error_models=r["error_models"],
                    hint_policy={"ladder": r["hint_ladder"]},
                    mastery_rule=None,
                    transfer_distance=1 if r["ability_id"] == "app_transfer" else None,
                    review_status="published",
                    published_at=None,
                )
            )
            stats["versions"] += 1

        await db.commit()

    await engine.dispose()
    return stats


if __name__ == "__main__":
    s = asyncio.run(seed())
    print("Seed 完成：")
    for k, v in s.items():
        print(f"  {k}: {v}（新增，已存在的跳过）")