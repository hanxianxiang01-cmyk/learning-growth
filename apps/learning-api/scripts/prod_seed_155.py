"""FE-1441：Trial-155 正式入库（FE-1439 ⑤）。

前置（全绿后执行）：映射 APPROVED（#83）+ Gate 8 8/8 + M30 内容阻断清零（#85）。
- 题源=/tmp/final2_155（FE-1440a 六题整改后终态，Gate 1~3 权威全零）
- ability_id 一律以 docs/39 mapping_final.csv final_app_id 覆盖（5 条改判生效）
- Resource.status='published' + rv.review_status='published' + published_at=now
- transfer_distance：is_transfer=true → 1（与 V1 seed 语义一致，喂 #7 迁移证据链）
- 幂等：title=`[T155] <question_id>` 判重
- 退役：qa_staged（25 条=19 样本+6 整改题）review_status→'qa_retired'
  （pin 放行集合与 catalog 均不认=通道关闭；历史 task/evidence 保留不删，
   符合 QA_DATA_HYGIENE"污染只软删不 DELETE"）

用法：
  DATABASE_URL=... PYTHONPATH=apps/learning-api python scripts/prod_seed_155.py <final_155_dir>
"""
from __future__ import annotations

import asyncio, csv, json, os, sys, uuid
from datetime import datetime, timezone

sys.path.insert(0, "apps/learning-api")
sys.path.insert(0, "os.path.dirname(os.path.abspath(__file__))")

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import Resource, ResourceVersion
from qa_sample_ingest import to_rv_fields, load_samples, BATCHES, DIFF_MAP

DB_URL = os.environ["DATABASE_URL"]
MAPPING = "docs/frontend/39_M_mapping_approval/mapping_final.csv"


def final_map() -> dict[str, str]:
    rows = list(csv.DictReader(open(MAPPING, encoding="utf-8-sig")))
    assert all(r["verdict"] == "APPROVED" for r in rows) and len(rows) == 42
    return {r["source_skill_id"]: r["final_app_id"] for r in rows}


def load_all(root: str) -> list[dict]:
    qs = []
    for b in BATCHES:
        data = json.load(open(os.path.join(root, b, "questions.json"), encoding="utf-8"))
        for q in data["questions"]:
            q["_batch"] = b
            qs.append(q)
    return sorted(qs, key=lambda x: x["question_id"])


async def main(root: str) -> None:
    fmap = final_map()
    qs = load_all(root)
    assert len(qs) == 155, f"题数 {len(qs)} != 155"
    eng = create_async_engine(DB_URL)
    S = async_sessionmaker(eng, expire_on_commit=False)
    added = skipped = remapped = 0
    qid2rvid = {}
    async with S() as db:
        for q in qs:
            f = to_rv_fields(q)
            title = f"[T155] {q['question_id']}"
            ab = fmap[q["source_skill_id"]]
            if ab != f["ability_id"]:
                remapped += 1
            ex = (await db.execute(select(Resource).where(Resource.title == title))).scalar_one_or_none()
            if ex:
                skipped += 1
                rvx = (await db.execute(select(ResourceVersion).where(ResourceVersion.resource_id == ex.resource_id))).scalar_one_or_none()
                if rvx: qid2rvid[q["question_id"]] = str(rvx.resource_version_id)
                continue
            res = Resource(resource_id=uuid.uuid4(), ability_id=ab,
                           resource_type="word_problem", title=title,
                           status="published", created_by="FE-1441-Trial155")
            db.add(res)
            await db.flush()
            rv = ResourceVersion(
                resource_id=res.resource_id, version_no=1, difficulty=f["difficulty"],
                task_type="word_problem", content=f["content"], ui_schema=f["ui_schema"],
                error_models=f["error_models"], hint_policy=f["hint_policy"],
                mastery_rule=f["mastery_rule"],
                transfer_distance=1 if q.get("is_transfer") else None,
                review_status="published", published_at=datetime.now(timezone.utc))
            db.add(rv)
            await db.flush()
            qid2rvid[q["question_id"]] = str(rv.resource_version_id)
            added += 1
        # 退役 qa_staged
        rr = await db.execute(text("update resource_version set review_status='qa_retired' "
                                   "where review_status='qa_staged'"))
        retired = rr.rowcount
        await db.commit()
    await eng.dispose()
    json.dump(qid2rvid, open("/tmp/t155_rvids.json", "w"), indent=1)
    print(f"正式入库：新增 {added} / 幂等跳过 {skipped}（映射覆盖 {remapped} 条）；qa_staged 退役 {retired} 条")
    print("rvid 映射=/tmp/t155_rvids.json（喂 E2E 样本切换）")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/final2_155"))
