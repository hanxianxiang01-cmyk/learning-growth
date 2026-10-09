"""FE-1438：155 题批 Gate 4~7 抽样实灌 ingest（QA 隔离入库 qa_staged）。

选样=每 renderer 各 1 题（19 renderer → ≥8 且全覆盖，任务单 §6 Gate 4~7 口径）。
隔离设计（未过 M→app 审批不得泄入生产池，docs/governance/QA_DATA_HYGIENE.md 精神）：
- Resource.status="draft" + ResourceVersion.review_status="qa_staged"
  → catalog（published 过滤）与生产选题（_published_resource_for_ability）双不可见；
- 仅 pin 路径放行 qa_staged（app/services/learning.py FE-1438 分支）+ 路由层 403
  （真实 child 无法 pin）——QA child …0099 专用。
幂等：按 content.question_id 判重（已存在跳过）。

用法：
  DATABASE_URL=... PYTHONPATH=apps/learning-api python scripts/qa_sample_ingest.py <final_155_dir>
  # final_155_dir 含 A_direct_reuse/ B_semantic_regeneration/ C_data_fix/ 三 questions.json
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, "apps/learning-api")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import Resource, ResourceVersion

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise SystemExit("需要 DATABASE_URL 环境变量")

BATCHES = ("A_direct_reuse", "B_semantic_regeneration", "C_data_fix")
DIFF_MAP = {"D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5}


def load_samples(root: str) -> list[dict]:
    qs = []
    for b in BATCHES:
        p = os.path.join(root, b, "questions.json")
        data = json.load(open(p, encoding="utf-8"))
        for q in data.get("questions", data if isinstance(data, list) else []):
            q["_batch"] = b
            qs.append(q)
    by: dict[str, dict] = {}
    for q in sorted(qs, key=lambda x: x["question_id"]):
        by.setdefault(q["renderer_id"], q)  # 每 renderer 取 ID 最小者，确定性选样
    return sorted(by.values(), key=lambda x: x["renderer_id"])


def to_rv_fields(q: dict) -> dict:
    ui = dict(q["task_ui_schema"])
    ws = dict(ui["workspaces"][0])
    ws["workspace_id"] = "main"
    ui["workspaces"] = [ws]
    content = {
        "stem": q["prompt"],
        "goal": q.get("goal") or q["prompt"],
        "answer": q["answer"],
        "question_id": q["question_id"],
        "batch": q["_batch"],
    }
    return {
        "title": f"[QA-Sample] {q['question_id']}",
        "ability_id": q["ability_id"],
        "difficulty": DIFF_MAP.get(str(q.get("difficulty_level")), 1),
        "content": content,
        "ui_schema": ui,
        "error_models": q.get("error_models", []),
        "hint_policy": {"ladder": q.get("hint_ladder", []), "ui_actions": []},
        "mastery_rule": {"context_family": q.get("context_family")},
        "response_type": q.get("response_type"),
    }


async def main(root: str) -> None:
    samples = load_samples(root)
    print(f"选样：{len(samples)} 题（renderer {sorted({s['renderer_id'] for s in samples})}")

    engine = create_async_engine(DB_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    added = skipped = 0
    async with Session() as db:
        for q in samples:
            f = to_rv_fields(q)
            exists = (await db.execute(
                select(ResourceVersion).join(Resource, Resource.resource_id == ResourceVersion.resource_id)
                .where(Resource.title == f["title"])
            )).scalar_one_or_none()
            if exists:
                skipped += 1
                continue
            res = Resource(
                resource_id=uuid.uuid4(),
                ability_id=f["ability_id"],
                resource_type="word_problem",
                title=f["title"],
                status="draft",          # 生产池不可见（双保险）
                created_by="FE-1438-sample",
            )
            db.add(res)
            await db.flush()
            db.add(ResourceVersion(
                resource_id=res.resource_id,
                version_no=1,
                difficulty=f["difficulty"],
                task_type="word_problem",
                content=f["content"],
                ui_schema=f["ui_schema"],
                error_models=f["error_models"],
                hint_policy=f["hint_policy"],
                mastery_rule=f["mastery_rule"],
                transfer_distance=None,
                review_status="qa_staged",   # 仅 pin 路径放行
                published_at=None,
            ))
            added += 1
        await db.commit()
    await engine.dispose()
    print(f"ingest 完成：新增 {added}，幂等跳过 {skipped}")
    print("下一步：QA child …0099 pin 实灌（Gate 4~7），全过后再走 FE-1433 replay（Gate 8）→ 审批后转 published 正式入库。")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/final_155"))
