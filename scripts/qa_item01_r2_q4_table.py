#!/usr/bin/env python3
"""QA-ITEM-01 R2 Q4 教研签认表 v2（R2 裁决 §三）。

变化 vs 第一轮 item_quality_review.csv：
- 范围：抽样 29 → **全量 225 published 题**（app_check 15 / app_strat 30 /
  app_transfer 8 等"正常推荐未命中"能力必须有实际题样，不得从质量验收范围消失）；
- 固定六列任务契约：学习目标 / 合法操作与结果 / 典型错误 / 提示原则 /
  独立预期结果 / 验证依据（能从题面数据预填的预填，不能的标 NEEDS_TEACHING_SIGNOFF）；
- 签认字段：教研签认状态 / 评审人 / 日期 / 整改意见（留空待签）。

独立预期列=V2.1/Q5 同源 recompute 器（未经产品 Judge 自证）；
符号题（ITEM01-04）如实标 MISMATCH 疑点。只读 DB，零写入。
"""
import csv
import json
import os
import re
import subprocess
import sys

import psycopg

BASE = os.environ.get("R2_OUT", "output/qa_item01_r2")
URL = os.environ["DATABASE_URL"].replace("+psycopg", "")

# 复用第一轮独立重算器（分支内入仓件）
src = subprocess.run(
    ["git", "show", "chore/qa-growth-formal-v21b:scripts/qa_item01_recompute_lib.py"],
    capture_output=True, text=True).stdout
lib_path = os.path.join(BASE, "_recompute_lib.py")
os.makedirs(BASE, exist_ok=True)
with open(lib_path, "w") as f:
    f.write(src)
sys.path.insert(0, BASE)
from _recompute_lib import recompute  # noqa: E402

COLS = [
    "resource_version_id", "ability_id", "title", "difficulty", "task_type",
    "renderer", "transfer_distance", "question_id",
    # ---- 固定六列任务契约（R2 裁决 §三）----
    "学习目标", "合法操作与结果", "典型错误", "提示原则", "独立预期结果", "验证依据",
    # ---- 签认字段 ----
    "教研签认状态", "评审人", "日期", "整改意见",
]

with psycopg.connect(URL) as c:
    rows = c.execute("""
        select rv.resource_version_id, r.ability_id, r.title, rv.difficulty,
               rv.task_type, rv.ui_schema::text, rv.content::text,
               rv.error_models::text, rv.hint_policy::text, rv.transfer_distance
        from resource_version rv
        join resource r on r.resource_id = rv.resource_id
        where rv.review_status='published'
        order by r.ability_id, rv.difficulty, rv.created_at""").fetchall()

out = []
for rvid, aid, title, diff, ttype, ui_s, ct_s, em_s, hp_s, tdist in rows:
    ui = json.loads(ui_s)
    ct = json.loads(ct_s)
    em = json.loads(em_s) or []
    hp = json.loads(hp_s) or {}
    renderer = ((ui.get("workspaces") or [{}])[0] or {}).get("renderer") or "?"
    rc_method, rc_val = recompute(renderer, ct)
    if rc_method == "recompute":
        match = None
        ind = f"独立重算={rc_val!r}（与库答案比对：{'MATCH' if str(rc_val)==str(ct.get('answer')) or rc_val==ct.get('answer') else 'MISMATCH 疑点'}）"
        status = ("RECOMPUTED_MATCH" if ("MATCH 疑点" not in ind) else "MISMATCH_SIGNOFF")
    elif rc_method == "rule":
        ind = f"规则核对：{rc_val}"
        status = "RULE_CHECKED"
    else:
        ind = f"需人工独立预期（{rc_val}）"
        status = "NEEDS_TEACHING_SIGNOFF"
    goal = ct.get("goal") or "（题面无 goal，需教研补）"
    contract = ui.get("response_contract")
    legal = (f"contract={json.dumps(contract, ensure_ascii=False)[:120]}"
             if contract else "（response_contract 缺失，需教研补）")
    legal += f"；库答案={ct.get('answer')!r}"
    if em:
        codes = [e.get("code") for e in em if isinstance(e, dict)]
        errs = "、".join(str(x) for x in codes[:4])
        if all(e.get("code") == e.get("pattern") for e in em if isinstance(e, dict)):
            errs += "（ITEM01-05：code==pattern 同质，规则内容缺失待教研实化）"
    else:
        errs = "（无 error_models，需教研补典型错误）"
    ladder = hp.get("ladder") or []
    hintp = (f"{len(ladder)} 级阶梯；首级=「{str(ladder[0])[:40]}」"
             if ladder else "（无 hint 阶梯，需教研补提示原则）")
    basis = f"renderer={renderer}；task_type={ttype}；batch={ct.get('batch')}；q_id={ct.get('question_id')}"
    out.append([str(rvid), aid, title, diff, ttype, renderer, tdist,
                ct.get("question_id"), goal, legal, errs, hintp, ind, basis,
                status, "", "", ""])

path = os.path.join(BASE, "Q4_item_quality_review_v2.csv")
with open(path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLS)
    w.writerows(out)

import collections
st = collections.Counter(r[14] for r in out)
ab = collections.Counter(r[1] for r in out)
print("rows:", len(out), "->", path)
print("ability coverage:", dict(ab))
print("status:", dict(st))
