#!/usr/bin/env python3
"""FE-1460 确定性规则回归夹具（负例必须检出、正例不得误报——裁决 §四.2）。"""
import sys, os
import os as _os, sys as _sys
_p=_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _p not in _sys.path: _sys.path.insert(0,_p)
from iqc import checks as C

def item(**kw):
    base = {"resource_version_id": "r", "resource_id": "R", "version_no": 1,
            "review_status": "published", "difficulty": 2, "ability_id": "app_rd",
            "content": {"stem": "x", "answer": 1},
            "ui_schema": {"schema_version": "1.0", "kind": "number",
                          "response_schema": {"answer_type": "number"}},
            "error_models": [], "hint_policy": {"ladder": ["a", "b", "c", "d"]}}
    base.update(kw)
    return base

CASES = [
 # (名称, 规则调用, 期望码(None=空))
 ("Q01 dup 检出", C.q01_multi_published({"a": item(resource_id="X"),
   "b": item(resource_id="X", resource_version_id="b", review_status="published", version_no=2)}), "Q01-DUP-PUBLISHED"),
 ("Q01 无 dup 不误报", C.q01_multi_published({"a": item(resource_id="X"), "b": item(resource_id="Y", resource_version_id="b")}), None),
 ("Q01 链闭合正例", C.q01_version_chain(
   {"old": item(resource_version_id="old", review_status="superseded"),
    "new": item(resource_version_id="new", review_status="published", version_no=2)}, [("old", "new")]), None),
 ("Q01 跨资源 P0", C.q01_version_chain(
   {"old": item(resource_version_id="old", review_status="superseded"),
    "new2": item(resource_version_id="new2", resource_id="OTHER", version_no=2)}, [("old", "new2")]), "Q01-RESOURCE-MISMATCH"),
 ("Q02 未知 schema", C.q02_schema_contract(item(ui_schema={"schema_version": "9.9"})), "Q02-BLOCKED_SCHEMA"),
 ("Q02 V2 缺 renderer", C.q02_schema_contract(item(ui_schema={"schema_version": "2.0", "workspaces": [{}], "response_contract": {}})), "Q02-V2-INCOMPLETE"),
 ("Q02 V1 完整不误判", C.q02_schema_contract(item()), None),
 ("Q03 判断题式对", C.q03_arithmetic(item(content={"stem": "小华算\u201c8 - 3 = 5\u201d。请检查：正确填1，错误填0", "answer": 1})), "Q03-OK"),
 ("Q03 判断题期望错→填0对", C.q03_arithmetic(item(content={"stem": "小华算\u201c8 - 3 = 6\u201d。请检查：正确填1，错误填0", "answer": 0})), "Q03-OK"),
 ("Q03 开放链式对", C.q03_arithmetic(item(content={"stem": "9+9+9=", "answer": 27})), "Q03-OK"),
 ("Q03 判断型误配检出", C.q03_arithmetic(item(content={"stem": "小华算\u201c8 - 3 = 6\u201d。请检查：正确填1，错误填0", "answer": 1})), "Q03-ANSWER_MISMATCH"),
 ("Q03 完整等式不比对→UNVERIFIED", C.q03_arithmetic(item(content={"stem": "8 + 5 = 13", "answer": 14})), "Q03-UNVERIFIED"),
 ("Q03 组×数", C.q03_arithmetic(item(content={"stem": "有3个袋子，每袋里有7颗珠", "answer": 21})), "Q03-OK"),
 ("Q03 跳步", C.q03_arithmetic(item(content={"stem": "从20出发，每次向右跳5，跳3次", "answer": 35})), "Q03-OK"),
 ("Q03 不强转 UNVERIFIED", C.q03_arithmetic(item(content={"stem": "观察画布散点估一估", "answer": 30})), "Q03-UNVERIFIED"),
 ("Q05 全同质检出", C.q05_error_models(item(error_models=[{"code": "a", "pattern": "a"}, {"code": "b", "pattern": "b"}])), "Q05-HOMOGENEOUS"),
 ("Q05 差异化不误报", C.q05_error_models(item(error_models=[{"code": "a", "pattern": "desc"}])), None),
 ("Q06 L1 透答案", C.q06_hint_ladder(item(content={"stem": "x", "answer": 21}, hint_policy={"ladder": ["答案是21", "x", "y", "z"]})), "Q06-HINT-LEAK"),
 ("Q06 指定选项", C.q06_hint_ladder(item(content={"stem": "x", "answer": "-"}, hint_policy={"ladder": ["该点减号哦", "x", "y", "z"]})), "Q06-LEAK-PATTERN"),
 ("Q06 正常阶梯不误报", C.q06_hint_ladder(item(content={"stem": "x", "answer": 21}, hint_policy={"ladder": ["先想想有几个组", "每组几个？", "数一数三组合起来", "检查总数"]})), None),
 ("Q06 题面泄答案检出(组成)", C.q06_stem_leak(item(content={"stem": "把它们放回百、十、个的框里，组成 352。", "answer": 352})), "Q06-STEM-LEAK"),
 ("Q06 标价泄答案", C.q06_stem_leak(item(content={"stem": "一本练习本标价15角，凑出正好3元5角，答案用角表示", "answer": 15})), "Q06-STEM-LEAK"),
 ("Q06 普通输入数字不误报", C.q06_stem_leak(item(content={"stem": "小青有4支红笔和6支蓝笔，一共几支", "answer": 4})), None),
 ("Q06 题面含数不误报(判断题)", C.q06_stem_leak(item(content={"stem": "8 - 3 = 6。请检查：正确填1，错误填0", "answer": 0})), None),
 ("Q06 正常题面不误报", C.q06_stem_leak(item(content={"stem": "小红有8朵花，小蓝有5朵，多几朵", "answer": 3})), None),
]

def main():
    fails = []
    for name, got, want in CASES:
        codes = [g[0] for g in got]
        ok = (want in codes) if want else (len(got) == 0)
        if not ok: fails.append((name, codes))
        print(("✓" if ok else "✗"), name, "" if ok else f"→ {codes}")
    print(f"\n夹具 {len(CASES)-len(fails)}/{len(CASES)} PASS")
    return 1 if fails else 0

if __name__ == "__main__":
    sys.exit(main())
