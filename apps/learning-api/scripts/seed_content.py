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
from app.content.context_family import canonicalize_context_family
from app.content.context_family_map import STEM_CONTEXT_FAMILY
from app.content.resource_seed import GOLD_RESOURCES
from app.core.config import get_settings
from app.models import AbilityEdge, AbilityNode, Resource, ResourceVersion


def _mastery_rule_for(r: dict) -> dict:
    """按 Backfill 映射生成 mastery_rule，入口强校验（治理文档 §4 Seed Validation）。

    - 非法 context_family → canonicalize 抛 UNKNOWN_CONTEXT_FAMILY，seed 直接失败；
    - REVIEW 题（映射为 None）→ context_family 不写入（NULL 不得伪装成族）；
    - transfer_capable 由资源自身声明（is_transfer），实际 evidence_role 由 Assignment 决定。
    """
    stem = r["content"]["stem"]
    raw = STEM_CONTEXT_FAMILY.get(stem)
    family = canonicalize_context_family(raw)
    rule: dict = {"transfer_capable": bool(r.get("is_transfer"))}
    if family is not None:
        rule["context_family"] = family
    return rule


def _build_ui_schema_v1(r: dict) -> dict:
    """把 GOLD_RESOURCES 的 visual/tools 组装为 TaskUISchema V1。

    对齐前端 contracts.ts 的 ManipulativeTaskUiSchema / NumberTaskUiSchema：
    - 有 visual → kind="manipulative"，携带 visual + tools + response_schema
    - 无 visual → kind="number"，仅 prompt + response_schema
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


def _transfer_distance(r: dict) -> int | None:
    """迁移题 transfer_distance=1，其余 None。"""
    if r.get("is_transfer"):
        return 1
    if r["ability_id"] == "app_transfer":
        return 1
    return None


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
                    level_schema=a.get("level_schema") or {
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
                    task_type=r.get("task_type") or "word_problem",
                    content=r["content"],
                    ui_schema=_build_ui_schema_v1(r),
                    error_models=r["error_models"],
                    hint_policy={
                        "ladder": r["hint_ladder"],
                        "ui_actions": r.get("ui_actions", []),
                    },
                    mastery_rule=_mastery_rule_for(r),
                    transfer_distance=_transfer_distance(r),
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