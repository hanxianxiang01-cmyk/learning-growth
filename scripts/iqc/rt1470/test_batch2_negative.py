#!/usr/bin/env python3
"""FE-1470 负对照：分两类，效力边界不同，不能混着说。

用户 2026-10-21 复审 §三 明确划了线：
> 「故意改错存储答案，能够验证比较器发现不一致；**不能单靠它证明题干解析
>   本身正确**；题干数值/关系方向/必要条件变化时也应有对应预期变化或受控拒绝。」

所以本文件跑三组独立的对照，**分别出声、分别计数**：

A 组 `A_*`：改**存储答案** → 必须 MISMATCH。
   证明「比较器不是永真」。**不证明**题干读对了。附反向确认：
   换回原值必须 MATCH，否则 A 组是假检出（比如比较器恒返回不等）。

B 组 `B_*`：**模型函数**吃配置，改配置里的独立事实 → 输出必须按新事实变化。
   这一组是本文件真正有价值的部分。第一版我写成「比较两个常量表达式
   `6+4` 与 `5+4` 的结果是否不同」——那是同义反复，改不改代码都会通过。
   现在改成：为每类 renderer 写一个 `model(config) -> int`，
   然后 (a) 用**真实配置**跑，必须复现存储答案；(b) 改动配置里的数值，
   输出必须跟着变且等于手算的新值。这样测的才是「推导是否依赖题面数值」。

C 组 `C_*`：**必要条件不成立时必须受控拒绝**。
   尺子两端颠倒、单框容量放不下，都要抛错而不是返回一个看着合理的数。
   同样附反向确认：同一函数在合法输入下必须给出正确答案——
   否则「拒绝」可能只是个坏函数。

DB-free：只用 evaluate() / independent_eval() / model 层，不连库。
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO} 下没有 scripts/iqc"

fails: list[str] = []


def note(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def load():
    p = os.path.join(HERE, "q03_batch2.py")
    spec = importlib.util.spec_from_file_location("q03_b2", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def find(m, rvid_prefix: str) -> dict:
    for c in m.CHECKS:
        if c["rvid"].startswith(rvid_prefix):
            return c
    raise KeyError(rvid_prefix)


# ══ 模型层：从配置的独立事实出发求答案，和 CHECKS 里登记的 expr 互相印证 ══
# 写这一层不是为了取代 CHECKS，而是为了能"改配置看输出变不变"。
# CHECKS 是逐题手工推导（可读性优先），这里是按 renderer 的通用模型
# （可变形优先）。两者算出同一个数，才算推导不是碰巧。

def model_ten_frame(cfg: dict) -> int:
    """十格框：给定已有 initial_count，再放 add_count 个，求总数。"""
    total = cfg["initial_count"] + cfg["add_count"]
    capacity = 10 * cfg["max_frames"]
    if total > capacity:
        raise ValueError(
            f"{cfg['initial_count']}+{cfg['add_count']}={total} 超出 "
            f"{cfg['max_frames']} 框容量 {capacity}")
    return total


def model_object_counter(cfg: dict) -> int:
    """两组物体合并计数。"""
    return sum(g["count"] for g in cfg["groups"])


def model_column(cfg: dict) -> int:
    """竖式：按题面运算符把两个操作数算出来。"""
    a, b = cfg["operands"]
    op = cfg["operator"]
    if op == "+":
        return a + b
    if op == "-":
        if b > a:
            raise ValueError(f"退位到负数：{a}-{b}")
        return a - b
    raise ValueError(f"未知运算符 {op!r}")


def model_formula(cfg: dict) -> int:
    """解一元等式：按 tokens 还原成 a op x = c / x op b = c / a op b = c。"""
    toks = cfg["tokens"]
    nums, ops, slot_at = [], [], None
    for i, t in enumerate(toks):
        if t["t"] == "num":
            nums.append(t["v"])
        elif t["t"] == "op":
            ops.append(t["v"])
        elif t["t"] == "slot":
            slot_at = len(nums)          # 空格位于第 slot_at 个操作数位置
    assert slot_at is not None and len(ops) == 1, "本模型只处理单运算符单空格"
    a, c, op = nums[0], nums[1], ops[0]
    if slot_at == 1:                     # a op x = c
        return c - a if op == "+" else a - c
    return c - a if op == "+" else a - c  # x op b = c → 同为减法


def model_ruler(cfg: dict) -> int:
    """尺子量长度 = 右端 − 左端；两端颠倒视为线段不存在。"""
    left, right = cfg["object"]
    if right < left:
        raise ValueError(f"右端 {right} < 左端 {left}：线段不存在，拒绝求解")
    return right - left


# ══ A 组：改存储答案，必须检出 ═══════════════════════════════════════════════
A_CASES = [
    ("A1 ten-frame 答案改 10→9", "06546dfb", "9"),
    ("A2 ten-frame 跨框题答案改 13→10（受十格框暗示的错答）", "f9fae106", "10"),
    ("A3 object-counter 答案改 7→4（只数右侧）", "079d72bd", "4"),
    ("A4 column 退位题答案改 63→73（未退位）", "1b3c314e", "73"),
    ("A5 formula 加数题答案改 9→25（方向反）", "506538f4", "25"),
    ("A6 ruler 答案改 6→10（从零读）", "2c5f8ead", "10"),
    ("A7 ruler 答案改 8→10（采信题面断言）", "7abf0ae3", "10"),
]

# ══ B 组：模型吃真实配置必须复现存储答案，改配置必须跟着变 ═══════════════════
# (说明, rvid 前缀, 模型, 真实配置(取该题独立事实), 改动后配置, 改动后期望值)
B_CASES = [
    ("B1 ten-frame 06546dfb：initial 6→5 后总数应为 9",
     "06546dfb", model_ten_frame,
     {"initial_count": 6, "add_count": 4, "max_frames": 1},
     {"initial_count": 5, "add_count": 4, "max_frames": 1}, 9),
    ("B2 ten-frame cdcc6e30：initial 3→2 后总数应为 9",
     "cdcc6e30", model_ten_frame,
     {"initial_count": 3, "add_count": 7, "max_frames": 1},
     {"initial_count": 2, "add_count": 7, "max_frames": 1}, 9),
    ("B3 ten-frame f9fae106：跨框题 initial 8→7 后应为 12",
     "f9fae106", model_ten_frame,
     {"initial_count": 8, "add_count": 5, "max_frames": 2},
     {"initial_count": 7, "add_count": 5, "max_frames": 2}, 12),
    ("B4 object-counter b9a431f0：右组 3→5 后应为 10",
     "b9a431f0", model_object_counter,
     {"groups": [{"count": 5}, {"count": 3}]},
     {"groups": [{"count": 5}, {"count": 5}]}, 10),
    ("B5 column 183c028f：第二个操作数 28→29 后应为 76（进位仍发生但和变）",
     "183c028f", model_column,
     {"operands": [47, 28], "operator": "+"},
     {"operands": [47, 29], "operator": "+"}, 76),
    ("B6 column 1b3c314e：被减数 90→91 后应为 64",
     "1b3c314e", model_column,
     {"operands": [90, 27], "operator": "-"},
     {"operands": [91, 27], "operator": "-"}, 64),
    ("B7 formula 506538f4：等式右边 17→18 后空格应为 10",
     "506538f4", model_formula,
     {"tokens": [{"t": "slot"}, {"t": "op", "v": "+"}, {"t": "num", "v": 8},
                 {"t": "eq"}, {"t": "num", "v": 17}]},
     {"tokens": [{"t": "slot"}, {"t": "op", "v": "+"}, {"t": "num", "v": 8},
                 {"t": "eq"}, {"t": "num", "v": 18}]}, 10),
    ("B8 formula 8122c8c2：被减数 15→16 后空格应为 7（减数题跟着变）",
     "8122c8c2", model_formula,
     {"tokens": [{"t": "num", "v": 15}, {"t": "op", "v": "-"},
                 {"t": "slot"}, {"t": "eq"}, {"t": "num", "v": 9}]},
     {"tokens": [{"t": "num", "v": 16}, {"t": "op", "v": "-"},
                 {"t": "slot"}, {"t": "eq"}, {"t": "num", "v": 9}]}, 7),
    ("B9 ruler 2c5f8ead：右端 10→11 后长度应为 7（不是原来的 6）",
     "2c5f8ead", model_ruler,
     {"object": [4, 10]},
     {"object": [4, 11]}, 7),
    ("B10 ruler 7f76aa86：左端 2→1 后长度应为 6",
     "7f76aa86", model_ruler,
     {"object": [2, 7]},
     {"object": [1, 7]}, 6),
]


def main() -> int:
    m = load()

    print("── A 组：改存储答案 → 比较器必须检出（证明比较器非永真）──")
    for name, prefix, fake in A_CASES:
        c = find(m, prefix)
        r = m.evaluate(c, fake, [], {})
        note(name, r["verdict"] == "MISMATCH",
             f"computed={r['computed']} stated={fake} → {r['verdict']}")

    print("\n── A 组反向确认：换回原值必须 MATCH（否则 A 组是假检出）──")
    for name, prefix, _fake in A_CASES:
        c = find(m, prefix)
        real = m.independent_eval(c["expr"])
        r = m.evaluate(c, str(real), [], {})
        note(f"{prefix} 原值仍 MATCH", r["verdict"] == "MATCH",
             f"computed={r['computed']}")

    print("\n── B 组(a)：模型吃真实配置，必须复现该题存储答案与手推值 ──")
    for name, prefix, model, cfg_real, _cfg_new, _want in B_CASES:
        c = find(m, prefix)
        got = model(cfg_real)
        handmade = m.independent_eval(c["expr"])
        note(f"{prefix} 模型({got}) == 手推({handmade})",
             got == handmade, f"{got} vs {handmade}")

    print("\n── B 组(b)：改配置独立事实 → 输出必须按新事实变化 ──")
    for name, prefix, model, cfg_real, cfg_new, want in B_CASES:
        before, after = model(cfg_real), model(cfg_new)
        note(name, after == want and after != before,
             f"{before} → {after}（期望 {want}）")

    print("\n── C 组：必要条件不成立时必须受控拒绝，不许硬算 ──")
    rejected = 0
    for desc, fn, cfg in [
        ("C1 尺子两端颠倒（10 → 4）", model_ruler, {"object": [10, 4]}),
        ("C2 单框容量放不下 8+5=13", model_ten_frame,
         {"initial_count": 8, "add_count": 5, "max_frames": 1}),
        ("C3 竖式减出负数（27 − 90 类）", model_column,
         {"operands": [27, 90], "operator": "-"}),
    ]:
        try:
            v = fn(cfg)
            note(desc, False, f"未拒绝，反而返回 {v}")
        except (ValueError, AssertionError) as e:
            rejected += 1
            note(desc, True, str(e)[:70])

    print("\n── C 组反向确认：同一模型在合法输入下必须给出正确答案 ──")
    note("C1b 合法 4→10 仍返回 6", model_ruler({"object": [4, 10]}) == 6)
    note("C2b 两框容量下 8+5=13 合法（题库 f9fae106 正是 max_frames=2）",
         model_ten_frame({"initial_count": 8, "add_count": 5, "max_frames": 2}) == 13)
    note("C3b 合法 90−27 仍返回 63",
         model_column({"operands": [90, 27], "operator": "-"}) == 63)

    print()
    if fails:
        print(f"BATCH2-NEGATIVE-GATE: FAIL ({len(fails)}) → {fails}")
        return 1
    print(f"BATCH2-NEGATIVE-GATE: PASS "
          f"(A {len(A_CASES)} 检出 + {len(A_CASES)} 反向确认；"
          f"B {len(B_CASES)} 模型复现 + {len(B_CASES)} 预期变化；"
          f"C {rejected}/3 受控拒绝 + 3 反向确认)")
    return 0


if __name__ == "__main__":
    sys.exit(main())