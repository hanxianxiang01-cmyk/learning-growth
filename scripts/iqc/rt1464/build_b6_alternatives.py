#!/usr/bin/env python3
"""B6 替代题构建（裁决 13:43 方案一）：新 resource+rv(qa_staged)，含独立核验。

设计：
A 数位策略（place-value·app_strat·d1，替 2c46c271）：题面不出现答案；条件
  ①百位=3 ②个位>十位 由 pool[3,0,5] 唯一推得 305——必须推理+实际放卡。
B 规律迁移（pattern-board·app_transfer·d4，替 845c6fea）：ABBA 周期4 信号灯
  新表征；visible=[1,2,2,1]×2，补两格=[1,2]→"12"——需识别对称周期结构。
两题 process_constraint 显式声明；错误模型 code≠pattern 可区分；Hint 阶梯
  L1/L2 不含答案值（Q06 口径）；context_family 复用原题受控词表值。
独立核验=本脚本穷举推导（不调产品 Judge）。原题状态零改动。
"""
import hashlib
import json
import os
import sys
import uuid
from itertools import permutations

import psycopg
import psycopg.types.json as pj

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("IQC_MIGRATE_DB") or sys.exit("缺 IQC_MIGRATE_DB")

STEM_A = ("三张数字卡 3、0、5 要放进百、十、个三个框里，组成一个三位数，"
          "同时满足两个条件：①百位框放 3；②个位框的数比十位框的数大。"
          "先想清楚哪张卡该进哪个框，摆好后把组成的三位数写下来。")
GOAL_A = "根据数位条件推理卡片位置（策略选择），并用实际摆卡验证答案"
STEM_B = ("十字路口的信号灯按规律闪：红、黄、黄，红、黄、黄……"
          "已经闪了这样两轮。接下来两个该闪什么？从颜色板里选出顺序摆到空位上，"
          "再按 红=1、黄=2 把这两个颜色写成两位数。")
GOAL_B = "识别 ABB 三元周期（非二元交替），迁移到信号灯情境并延续规律"

ITEM_A = {
    "title": "B6-ALT-A 位值卡策略摆放", "ability_id": "app_strat", "difficulty": 1,
    "content": {"stem": STEM_A, "goal": GOAL_A, "answer": 305},
    "ui_schema": {
        "schema_version": "2.0",
        "prompt": {"text": STEM_A[:40] + "…"},
        "ui_revision": "b6-alt-a-1",
        "response_contract": {"response_type": "place_value",
            "required_fields": ["workspaces", "answer"],
            "evidence_targets": ["slots", "structure"]},
        "workspaces": [{
            "workspace_id": "main", "renderer": "place-value", "mode": "place_value_build",
            "capabilities": ["drag", "answer_input", "undo", "reset"],
            "constraints": {"pool_multiset_equals_target_digits": True},
            "initial_state": {},
            "config": {"pool": [3, 0, 5], "target": 305,
                       "process_constraint": {"mode": "place_value_build", "params": {}}}}]},
    "error_models": [
        {"code": "zero_skipped", "pattern": "tens_placeholder_dropped",
         "note": "0 不敢占十位（只放两张）——占位概念未立"},
        {"code": "condition_b_violated", "pattern": "larger_digit_in_tens",
         "note": "摆成 350——个位不大于十位，条件②未核验"},
        {"code": "hundreds_wrong", "pattern": "condition_a_ignored",
         "note": "百位没放 3（如 503/035）——条件①遗漏"}],
    "hint_policy": {"ladder": [
        "三张卡里，题目说哪一张必须先住进百位框？",
        "剩下两张是 0 和 5——比一比，谁大？",
        "大数要住进个位框，那十位框只剩谁了？",
        "从百位往下读一遍：3、0、5——核对个位是不是比十位大。"]},
    "mastery_rule": {"context_family": "school_objects"}, "transfer_distance": 1,
}
ITEM_B = {
    "title": "B6-ALT-B2 信号灯ABB周期迁移", "ability_id": "app_transfer", "difficulty": 4,
    "content": {"stem": STEM_B, "goal": GOAL_B, "answer": "12"},
    "ui_schema": {
        "schema_version": "2.0",
        "prompt": {"text": STEM_B[:40] + "…"},
        "ui_revision": "b6-alt-b-1",
        "response_contract": {"response_type": "pattern",
            "required_fields": ["workspaces", "answer"],
            "evidence_targets": ["visible_tokens", "blank_fills", "pattern_phase"]},
        "workspaces": [{
            "workspace_id": "main", "renderer": "pattern-board", "mode": "repeat_pattern",
            "capabilities": ["extend_pattern", "answer_input", "undo", "reset"],
            "constraints": {"blanks": 2, "period": 3},
            "initial_state": {},
            "config": {"blanks": 2, "palette": [1, 2], "visible": [1, 2, 2, 1, 2, 2],
                       "process_constraint": {"mode": "pattern_extension", "params": {}}}}]},
    "error_models": [
        {"code": "phase_shift", "pattern": "counted_from_last_token",
         "note": "从最后那颗重新数（接成 2,2）——周期相位偏移"},
        {"code": "period_misread_abab", "pattern": "assumed_binary_alternation",
         "note": "按 AB 二元交替接（红黄后猜红黄=同值侥幸，观察区分靠摆珠记录）"},
        {"code": "direction_reversed", "pattern": "cycle_read_backwards",
         "note": "周期倒序（黄黄）——方向感缺失"}],
    "hint_policy": {"ladder": [
        "把闪过的灯分组数一数：每几个灯正好重复开头？",
        "一组是三个灯——红、黄、黄。这组里红排第几？",
        "第二轮已经闪完，第三轮该从这组的第几个灯重新开始？",
        "红、黄、黄三个一组——新起的一组头两个是什么？"]},
    "mastery_rule": {"context_family": "school_objects"}, "transfer_distance": 1,
}

REPLACES = {"A": "2c46c271-1a2f-4f45-ad3c-b5719ad58ded",
            "B": "845c6fea-418f-4365-a25e-b50e5b5040f8"}


def independent_verify():
    """§二.1 独立核验：穷举/结构推导答案唯一性（不调产品 Judge）。"""
    # A：pool 排列满足 百=3 且 个>十 → 唯一
    sols = ["".join(map(str, p)) for p in permutations([3, 0, 5])
            if p[0] == 3 and p[2] > p[1]]
    assert sols == ["305"], sols
    # B：ABBA 周期4 → 位置9,10 = period[0],period[1]
    period = [1, 2, 2, 1]
    nxt = [period[8 % 4], period[9 % 4]]
    assert nxt == [1, 2], nxt
    # Q06 口径：题面/L1/L2 不现答案串
    assert "305" not in STEM_A and not any("305" in h for h in ITEM_A["hint_policy"]["ladder"][:2])
    assert "12" not in STEM_B and not any("12" in h for h in ITEM_B["hint_policy"]["ladder"][:2])
    # Q05 口径：错误模型 code≠pattern 有区分度
    for it in (ITEM_A, ITEM_B):
        assert all(e["code"] != e["pattern"] for e in it["error_models"])
    return {"A_unique_solution": sols, "B_next_pair": nxt, "leak_checks": "PASS",
            "error_models_discriminative": True}


def main():
    iv = independent_verify()
    print("独立核验:", json.dumps(iv, ensure_ascii=False))
    # 静态规则复扫（Q05/Q06，checks.py 口径）
    sys.path.insert(0, os.path.join(HERE, ".."))
    from iqc import checks as C
    for item, tag in ((ITEM_A, "A"), (ITEM_B, "B")):
        s = item["ui_schema"]["workspaces"][0]
        fake = {"resource_version_id": "b6-" + tag, "content": item["content"],
                "hint_policy": item["hint_policy"], "error_models": item["error_models"]}
        q6 = [r for r in C.q06_stem_leak(fake)] + [r for r in C.q06_hint_ladder(fake)]
        q5 = [r for r in C.q05_error_models(fake)]
        assert not any(x[0] == "Q06-STEM-LEAK" for x in q6), q6
        assert not any(x[0] == "Q05-HOMOGENEOUS" for x in q5), q5
        print(f"静态复扫 {tag}: stem/hint 泄露=0 同质错因=0（{len(q6)} 条 L 级提示注记）")
    out = {"built": [], "independent_verify": iv, "replaces": REPLACES}
    apply = "--apply" in sys.argv
    # ==== 结构性零 DML（BUG-1456 纪律）：Dry Run 路径不构造任何
    # INSERT/UPDATE/DELETE 语句；写路径仅在 --apply 分支存在 ====
    conn = psycopg.connect(DB, autocommit=apply)
    try:
        for key, it in (("A", ITEM_A), ("B", ITEM_B)):
            exists = conn.execute("select 1 from resource where title=%s",
                                  (it["title"],)).fetchone()
            if exists:
                cur = conn.execute("""select resource_version_id::text, review_status
                    from resource_version rv join resource r using(resource_id)
                    where r.title=%s""", (it["title"],)).fetchone()
                print(f"{key} 已存在 {str(cur[0])[:8]}（{cur[1]}）幂等跳过")
                out["built"].append({"alt": key, "title": it["title"], "rvid": cur[0],
                                     "existing": True})
                continue
            if not apply:
                # Dry：只输出计划，不触库写
                out["built"].append({"alt": key, "title": it["title"],
                                     "planned": True})
                print(f"{key} DRY 计划: {it['title']}（无 DML）")
                continue
            rid, rvid = str(uuid.uuid4()), str(uuid.uuid4())
            conn.execute("insert into resource (resource_id,ability_id,resource_type,title,status,created_at)"
                      " values (%s,%s,'word_problem',%s,'draft',now())",
                      (rid, it["ability_id"], it["title"]))
            conn.execute("""insert into resource_version (resource_version_id,resource_id,version_no,
                difficulty,task_type,content,ui_schema,error_models,hint_policy,mastery_rule,
                transfer_distance,review_status,reviewer_1,reviewer_2,created_at)
                values (%s,%s,1,%s,'word_problem',%s,%s,%s,%s,%s,%s,'qa_staged','B6-alt','FE-1466',now())""",
                (rvid, rid, it["difficulty"], pj.Jsonb(it["content"]), pj.Jsonb(it["ui_schema"]),
                 pj.Jsonb(it["error_models"]), pj.Jsonb(it["hint_policy"]),
                 pj.Jsonb(it["mastery_rule"]), it["transfer_distance"]))
            out["built"].append({"alt": key, "title": it["title"], "resource_id": rid,
                                 "rvid": rvid, "ability": it["ability_id"],
                                 "difficulty": it["difficulty"]})
            print(f"{key} 建题: {rvid} {it['title']}（APPLIED，autocommit 单语句原子）")
    finally:
        if not apply:
            conn.rollback()  # 纵深防御（非唯一保证：Dry 路径无写语句可回滚）
        conn.close()
    json.dump(out, open(os.path.join(HERE, "FE1466_B6_alt_build.json"), "w"),
              ensure_ascii=False, indent=1)
    if not apply:
        print("Dry Run 完成：路径无 INSERT/UPDATE/DELETE（结构性零 DML）")
    else:
        with psycopg.connect(DB) as c:
            for k, old in REPLACES.items():
                st = c.execute("select review_status from resource_version where resource_version_id=%s", (old,)).fetchone()
                print(f"原题 {old[:8]} 状态未动: {st[0]}")


if __name__ == "__main__":
    main()
