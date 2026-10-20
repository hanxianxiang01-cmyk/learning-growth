#!/usr/bin/env python3
"""FE-1466 B 批次迁移发布器（产品裁决 13:26 §二：B1 首发、逐批推进）。

沿用现有发布通道（apply_content_fixes 口径）：新版→published、旧版→superseded
（保留行=历史 task/evidence 关联不失效）。安全纪律（BUG-1456 事务根治版）：
- 默认 Dry Run：判定阶段全只读 SELECT，写语句只在 --apply 分支执行（连"执行后
  rollback"都不发生）；
- --apply：单事务切换，任一门禁/异常整体 rollback，无部分更新；
- manifest 防覆盖：正式成功后落一次；重跑幂等空操作不覆写；
- 凭据 IQC_MIGRATE_DB 显式注入（R2 合规）。

每批切换前硬门禁（§二.1，任一不满足=整批拒绝，暂停后续）：
G1 状态前提：旧=published、新=qa_staged、同 resource
G2 映射核验：新行 ui 剥离 process_constraint==旧行 ui，content/hint/err 全等
  （B4 花边 088d0469 例外=content 继承内容修复版，lineage proof 文件必须在案）
G4 约束：新行 pc.mode 与 renderer 匹配、除 pc 外零差异（防夹带）
G3 唯一性：切换后该 resource 仅 1 个 published（事务内查）
切换后（§二.3/4）：只读回验 v2-catalog（含新版/不含旧版）+ 定向冒烟三态。
"""
import argparse
import copy
import hashlib
import json
import os
import sys
import uuid

import psycopg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from migrate_batch import attempt, gen_data, post  # noqa: E402

MODE = {"money-board": "payment_change", "pattern-board": "pattern_extension",
        "shape-canvas": "shape_drawing", "place-value": "place_value_build"}
LINEAGE_PREFIX = "088d0469"


def canon(o):
    return hashlib.sha256(json.dumps(o, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def load_batch(n):
    rep = json.load(open(f"{HERE}/FE1466_B{n}_migration_report.json"))
    assert rep.get("all_pass"), f"B{n} 报告非全过，拒绝发布"
    return rep["results"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True, type=int)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--db", default=os.environ.get("IQC_MIGRATE_DB", ""))
    args = ap.parse_args()
    if not args.db:
        sys.exit("缺 IQC_MIGRATE_DB（迁移发布需写账号显式注入）")
    dry = not args.apply
    results = load_batch(args.batch)
    print(f"B{args.batch}: {len(results)} 对，dry={dry}")

    conn = psycopg.connect(args.db)
    items, gates = [], []
    try:
        for x in results:
            src, new = x["src"], x["new"]
            o = conn.execute("""select resource_id,version_no,review_status,content::text,
                ui_schema::text,hint_policy::text,error_models::text from resource_version
                where resource_version_id=%s""", (src,)).fetchone()
            n = conn.execute("""select resource_id,version_no,review_status,content::text,
                ui_schema::text,hint_policy::text,error_models::text from resource_version
                where resource_version_id=%s""", (new,)).fetchone()
            if o is None or n is None:
                gates.append(f"行缺失 {src[:8]}/{new[:8]}"); continue
            if n[2] == "published" and o[2] == "superseded":
                continue  # 幂等：已切换
            if o[2] != "published" or n[2] != "qa_staged" or o[0] != n[0]:
                gates.append(f"G1 状态/归属破坏 {src[:8]}={o[2]} {new[:8]}={n[2]}"); continue
            oc, oui = json.loads(o[3]), json.loads(o[4])
            nc, nui = json.loads(n[3]), json.loads(n[4])
            stripped = copy.deepcopy(nui)
            pc = (stripped["workspaces"][0]["config"] or {}).pop("process_constraint", None)
            renderer = nui["workspaces"][0].get("renderer")
            if new[:8] == LINEAGE_PREFIX:
                if not os.path.exists(f"{HERE}/FE1466_lineage_proof_b4.json"):
                    gates.append("G2b 花边血缘证明文件缺失"); continue
                if stripped != oui:
                    gates.append(f"G2b 花边 ui 非约束唯一差异 {new[:8]}"); continue
            else:
                if stripped != oui or nc != oc:
                    gates.append(f"G2 映射核验失败 {new[:8]}"); continue
            if pc is None or pc.get("mode") != MODE.get(renderer):
                gates.append(f"G4 约束缺失/模式不符 {new[:8]}"); continue
            if json.loads(n[5]) != json.loads(o[5]) or json.loads(n[6]) != json.loads(o[6]):
                gates.append(f"G4c hint/err 漂移 {new[:8]}"); continue
            items.append({"old_rvid": str(src), "new_rvid": str(new), "resource_id": str(o[0]),
                          "old_version": o[1], "new_version": n[1], "renderer": renderer,
                          "content_sha_old": canon(oc), "content_sha_new": canon(nc),
                          "ui_sha_old": canon(oui), "ui_sha_new_minus_pc": canon(stripped)})
        if gates:
            print("门禁未过（整批拒绝，零写入）：", *gates, sep="\n  ")
            return 2
        if dry:
            for it in items[:3]:
                print("DRY:", it["old_rvid"][:8], "->", it["new_rvid"][:8],
                      "| content等=", it["content_sha_old"] == it["content_sha_new"] or it["new_rvid"][:8] == LINEAGE_PREFIX,
                      "| ui(-pc)等=", it["ui_sha_old"] == it["ui_sha_new_minus_pc"])
            print(f"Dry run 完成：{len(items)} 对通过门禁，无 DML")
            return 0
        # ==== --apply：单事务切换 ====
        for it in items:
            conn.execute("update resource_version set review_status='published' where resource_version_id=%s and review_status='qa_staged'", (uuid.UUID(it["new_rvid"]),))
            conn.execute("update resource_version set review_status='superseded' where resource_version_id=%s and review_status='published'", (uuid.UUID(it["old_rvid"]),))
        for it in items:
            dup = conn.execute("select count(*) from resource_version where resource_id=%s and review_status='published'", (uuid.UUID(it["resource_id"]),)).fetchone()[0]
            if dup != 1:
                raise RuntimeError(f"G3 唯一性破 {it['resource_id'][:8]} published={dup}")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("发布中止（整体 rollback，无部分切换）：", e)
        return 1
    finally:
        conn.close()

    mp = f"{HERE}/FE1466_publish_manifest_B{args.batch}.json"
    if not os.path.exists(mp):
        json.dump({"batch": f"B{args.batch}", "applied": True, "items": items,
                   "note": "new→published old→superseded 单事务；反向 update 即回滚"},
                  open(mp, "w"), ensure_ascii=False, indent=1)
    else:
        print("manifest 已存在，防覆盖")

    # §二.3/4：只读回验 + 冒烟
    with psycopg.connect(args.db) as c:
        for it in items:
            dup = c.execute("select count(*) from resource_version where resource_id=%s and review_status='published'", (uuid.UUID(it["resource_id"]),)).fetchone()[0]
            st = c.execute("select review_status from resource_version where resource_version_id=%s", (uuid.UUID(it["new_rvid"]),)).fetchone()[0]
            assert dup == 1 and st == "published", (it["new_rvid"][:8], dup, st)
    cat = json.loads(urllib_request(f"{_api()}/v1/content/v2-catalog"))
    cids = {str(i["resource_version_id"]) for i in cat.get("items", [])}
    miss = [it["new_rvid"][:8] for it in items if it["new_rvid"] not in cids]
    ghost = [it["old_rvid"][:8] for it in items if it["old_rvid"] in cids]
    rep = json.load(open(f"{HERE}/FE1466_B{args.batch}_migration_report.json"))
    bynew = {r["new"]: r for r in rep["results"]}
    smoke = []
    for it in items:
        r = bynew[it["new_rvid"]]
        with psycopg.connect(args.db) as c:
            ui = json.loads(c.execute("select ui_schema::text from resource_version where resource_version_id=%s", (it["new_rvid"],)).fetchone()[0])
            ct = json.loads(c.execute("select content::text from resource_version where resource_version_id=%s", (it["new_rvid"],)).fetchone()[0])
        cfg = ui["workspaces"][0]["config"]; cons = ui["workspaces"][0].get("constraints") or {}
        legal, contra, empty = gen_data(r["renderer"], cfg, cons)
        ans = ct.get("answer")
        _, o1, _ = attempt(it["new_rvid"], empty, ans)
        _, o3, _ = attempt(it["new_rvid"], legal, ans)
        ok = (o1.get("correct") is None and o1.get("process_status") == "missing"
              and o3.get("correct") is True and o3.get("process_status") == "valid")
        smoke.append({"new": it["new_rvid"][:8], "smoke_pass": ok})
        if not ok:
            print("冒烟失败——暂停后续批次：", it["new_rvid"][:8])
            return 3
    print(f"B{args.batch} 发布完成：{len(items)} 对，唯一性/目录(缺={miss or '无'} 残={ghost or '无'})/冒烟全过")
    json.dump({"batch": f"B{args.batch}", "post": {"catalog_missing": miss, "catalog_ghost": ghost, "smoke": smoke}},
              open(f"{HERE}/FE1466_postpublish_B{args.batch}.json", "w"), ensure_ascii=False, indent=1)
    return 0


def urllib_request(url):
    import urllib.request
    return urllib.request.urlopen(url).read()


def _api():
    return os.environ.get("IQC_API_BASE", "http://127.0.0.1:8000")


if __name__ == "__main__":
    sys.exit(main())
