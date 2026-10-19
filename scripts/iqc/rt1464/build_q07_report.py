#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""账1 结果落盘（实测数据来自 q07 三态提交流程 stdout，2026-10-19）。"""
import json

obs = [
    ("货币35 空过程", "2ff4a288", "empty", True, "attempt_standard", 1.0, 1.0, True, "ffc0b738", [2,191], [2,191]),
    ("货币35 矛盾过程(选50)", "2ff4a288", "contradiction", True, "attempt_standard", 1.0, 1.0, True, "b3ecfd3c", [2,192], [2,192]),
    ("货币35 合法过程", "2ff4a288", "valid_op", True, "attempt_standard", 1.0, 1.0, True, "09d02cbb", [2,193], [2,193]),
    ("花边12 空过程", "1723d78a", "empty", True, "attempt_standard", 1.0, 1.0, True, "a426489f", [4,908], [4,908]),
    ("花边12 合法过程", "1723d78a", "valid_op", True, "attempt_standard", 1.0, 1.0, True, "ea2113df", [4,909], [4,909]),
    ("钉子板6 空过程", "971b1f5e", "empty", True, "attempt_standard", 1.0, 1.0, True, "e527f35a", [2,569], [2,569]),
    ("数字卡352 空过程", "9d0d3a7e", "empty", True, "attempt_standard", 1.0, 1.0, True, "61f35a60", [2,213], [2,213]),
]
rows = [{"case": c, "rvid": v, "process": p, "judge_correct": jc, "evidence_type": et,
         "correctness": co, "independence": ind, "valid": val, "attempt8": a,
         "mastery_before": lb, "mastery_after": la}
        for c, v, p, jc, et, co, ind, val, a, lb, la in obs]

report = {
    "verdict": "CONFIRMED——空/矛盾过程+正确终值一律产出有效正向 Mastery Evidence"
               "（correctness=1.0，valid=true，type=attempt_standard）；"
               "evidence_count 逐条递增（191→192→193 / 908→909 / 569 / 213）＝确被能力账本消费",
    "level_unchanged_note": "本轮 level 未跳变（QA 历史证据基数大，L2/L4 稳态）——"
                            "裁决要求'即使等级不变也核对有无新增正向证据'＝有新增，实锤",
    "session_settlement": "每题均调用 GET /sessions/{sid}/result 执行结算读取，settled=true",
    "rows": rows,
    "root": "turn_service.record_attempt：correct is not None 即写 MasteryEvidence"
            "（correctness=1/0）——不查 V2 response.workspaces 过程数据；"
            "jump_constraint 仅数轴题判分前翻转 correct，翻转后 correct=False→写 0.0 负证据"
            "（FE-1455 全链正确），其余四类 renderer 无此门槛",
    "principle_alignment": "对照裁决§二四格语义表：现行系统'终值对+过程缺失'＝产正向掌握证据"
                           "（应＝不产＋提示完成）；'终值对+过程明确错'＝产正向（应＝过程反馈，"
                           "负向与否由冻结契约定）——四格仅'终值对+过程对''终值错'两格现行语义正确",
    "impact_scope": "非仅 7 题——凡 V2 提交且 renderer 无过程校验的题型均可能；7 题为 QA 代表样本",
    "isolation": "全部 QA child …0099；题库资源零修改；Judge 零修改（裁决=暂不改）"
}
json.dump(report, open("q07_evidence_chain_results.json", "w"), ensure_ascii=False, indent=1)
print("账1 落盘 ok |", report["verdict"][:60])
