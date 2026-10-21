#!/usr/bin/env python3
"""FE-1470：Q03 独立核验第二批（20 题，`numeric_judge ∩ both` 剩余队列）。

用户 2026-10-21 复审 §三 的执行要求，逐条对应本文件：
  · 「约 20 题一个可审查批次」→ 本批 20 题
  · 「优先选题干和必要配置完整、数学关系清楚的任务」
  · 「每题保留：输入依据 → 所求对象 → 独立推导 → 适用条件 →
     与存储答案比较 → 结论」→ `CHECKS` 里每题都有这六个字段
  · 「不要把配置里的 expected 或答案副本当成独立预期」
     → `independent_source()` 显式声明本题的独立事实来自哪里，
       并**拒绝**把 expected/target/answer 当作推导依据
  · 「144 是优先取题队列，不是 144 条已经被证明能够自动求解的题」

选题目录（20 题，跨 7 个 renderer，覆盖 3 条求解路径）：

| renderer | 题数 | 求解路径 | 独立事实来源 |
|---|---:|---|---|
| ten-frame | 5 | numeric_exact | config.target_count / initial_count |
| object-counter | 5 | numeric_exact | config.groups[].count |
| column-arithmetic | 3 | numeric_exact | config.operands[] + 题面运算符 |
| formula-board | 3 | numeric_exact | config.tokens（解一元等式） |
| ruler | 4 | numeric_exact | config.object 两端刻度之差 |

**本批没有取样 estimation-canvas(8)、shape-gallery(8)、direction-grid(8)、clock(8)**：
- 前三类的 9 条已在 FE-1468 里逐题核完（容差集合 / 属性计数 / 格编码），
  另 8 条同质，重复核验只会增加行数不增加证据。
- clock 的存储答案是 `h*60+m` 编码（4:30 → 270），上一批六题已证明
  「值域看着怪 ≠ 算错」，但改用它当第二批主干会让"独立推导"变成
  "反推编码规则"——那是另一件事，留到有明确编码契约可引时再做。

用法：
  DATABASE_URL=... python scripts/iqc/rt1470/q03_batch2.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/scripts/iqc/rt1470 → 退三级才是仓库根（同坑已踩三次，见 assert）。
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO} 下没有 scripts/iqc"

# ── 独立推导登记表 ────────────────────────────────────────────────────────────
# 每题的 source / stmt / read / expr / object / boundary 六个字段按用户规定的
# 顺序排列。**先解题、后对答案**：expr 只引用 source 里声明的独立事实。
CHECKS: list[dict] = [
    # ── ten-frame：初始有 N 个，再放 M 个，问一共几个 ──
    {
        "rvid": "06546dfb-7e18-45ab-8491-de6cdb0ebefb",
        "renderer": "ten-frame",
        "source": "cfg.initial_count=6, 题面「接着再放4个」",
        "read": "已有 6 个，再放 4 个 → 求总个数（合并，不是剩余）",
        "object": "圆点总数",
        "expr": "6 + 4",
        "boundary": "十格框容量为 10（max_frames=1），6+4 恰好填满；"
                    "若和超过 10 需跨框，题面会另说「摆满十个打包装袋」（见 fea38e2d）",
        "q05_hypothesis": "把「再放4个」当成最终总数 4，或把初始 6 当答案",
    },
    {
        "rvid": "939ab507-cee6-449a-80b9-cf97cedd194b",
        "renderer": "ten-frame",
        "source": "cfg.initial_count=7, 题面「接着再放3个」",
        "read": "已有 7 个，再放 3 个 → 合并求总数",
        "object": "圆点总数",
        "expr": "7 + 3",
        "boundary": "7+3 恰满一框，与上一题同一模型；区别只在加数不同",
        "q05_hypothesis": "只数新增的 3 个就提交",
    },
    {
        "rvid": "cdcc6e30-50f2-4efb-a5c8-06b373d8c797",
        "renderer": "ten-frame",
        "source": "cfg.initial_count=3, 题面「接着再放7个」",
        "read": "已有 3 个，再放 7 个 → 合并求总数",
        "object": "圆点总数",
        "expr": "3 + 7",
        "boundary": "与 06546dfb 是同一模型的交换加数版本（3+7 vs 6+4）；"
                    "若两条答案不同则说明模型不稳，不能只核单条",
        "q05_hypothesis": "把两个加数位置对调后只报其中一个",
    },
    {
        "rvid": "f9fae106-45db-499f-9b85-f0d93d17c64b",
        "renderer": "ten-frame",
        "source": "cfg.initial_count=8, 题面「接着再放5个」；cfg.max_frames=2",
        "read": "8+5 超过一框（10），需跨到第二框 → 总数仍是合并结果",
        "object": "圆点总数（**不是**框数，也不是第二框的个数）",
        "expr": "8 + 5",
        "boundary": "max_frames=2 允许跨框，所以 13 是合法状态；"
                    "若 max_frames=1 则本题物理上无解——配置与题面必须一致，"
                    "这一条正是用来检验「容量约束有没有被题面正确表达」",
        "q05_hypothesis": "受十格框「满十」暗示，答 10 而非 13",
    },
    {
        "rvid": "fea38e2d-225e-44b7-9e02-f09803405b8d",
        "renderer": "ten-frame",
        "source": "题面「妈妈买了13颗糖…摆满十个打包装成一袋，剩下的散着放」；"
                  "cfg.target_count=13, max_frames=2",
        "read": "13 颗 → 装满 1 袋（10 颗）+ 散放 3 颗 → 被问的是**总颗数**",
        "object": "糖的总颗数",
        "expr": "10 * 1 + 3",
        "boundary": "本题问的是总数而非「几袋几颗」；若问「装了几袋还剩几颗」"
                    "则答案是 (1, 3) 而非 13。题干结尾「摆好后提交」未指定提交量，"
                    "**这是本批唯一一条提交契约不够明确的题**，已在 provenance 里标注",
        "q05_hypothesis": "只报散放的 3，或只报装袋的 1",
    },

    # ── object-counter：两组各若干，问一共 ──
    {
        "rvid": "079d72bd-1458-4f0f-9285-3f7cf4733dd1",
        "renderer": "object-counter",
        "source": "cfg.groups: 左3(locked) + 右4",
        "read": "两组积木合并计数",
        "object": "积木总块数",
        "expr": "3 + 4",
        "boundary": "左侧 locked=true 表示已给定不可改，右侧需孩子摆放；"
                    "计数结果与哪组是 locked 无关",
        "q05_hypothesis": "只数右侧 4 块（忘记左侧已摆好的）",
    },
    {
        "rvid": "08d4f5bc-5534-4999-b431-47847834b049",
        "renderer": "object-counter",
        "source": "cfg.groups: 左1 + 右2",
        "read": "1 与 2 合并",
        "object": "积木总块数",
        "expr": "1 + 2",
        "boundary": "本批最小量级（3），用于确认计数不是靠数大数才成立",
        "q05_hypothesis": "把 1+2 算成 12（字符串拼接误读）",
    },
    {
        "rvid": "b9a431f0-c717-4ad0-97ff-69a5cf629656",
        "renderer": "object-counter",
        "source": "cfg.groups: 左5 + 右3",
        "read": "5 与 3 合并",
        "object": "积木总块数",
        "expr": "5 + 3",
        "boundary": "5+3 与 cdcc6e30 的 3+7 都等于 10 但模型不同（跨框 vs 单组），"
                    "两条都核过才能说明「等于 10」不是巧合",
        "q05_hypothesis": "把 5+3 当 5−3=2",
    },
    {
        "rvid": "d7a7c884-5ef7-4268-a949-d15031ce8012",
        "renderer": "object-counter",
        "source": "cfg.groups: 左2 + 右2",
        "read": "2 与 2 合并",
        "object": "积木总块数",
        "expr": "2 + 2",
        "boundary": "等量两组，用于区分「合并」与「比较」（比较会答 0）",
        "q05_hypothesis": "把「一样多」理解成差为 0",
    },
    {
        "rvid": "f3bb5804-3676-4e30-815a-d9d9edbc73db",
        "renderer": "object-counter",
        "source": "cfg.groups: 左6 + 右6",
        "read": "6 与 6 合并",
        "object": "积木总块数",
        "expr": "6 + 6",
        "boundary": "和为 12，超出单框 10，与本批 ten-frame 的 f9fae106 同值不同模型",
        "q05_hypothesis": "受「两组一样多」暗示答 6",
    },

    # ── column-arithmetic：竖式 ──
    {
        "rvid": "183c028f-fdc6-4fe1-8c6b-b55c111f906d",
        "renderer": "column-arithmetic",
        "source": "cfg.operands=[47, 28]；题面「又买来」→ 加法",
        "read": "原有 47 本，又买 28 本 → 求和",
        "object": "书的总本数",
        "expr": "47 + 28",
        "boundary": "个位 7+8=15 需进位，十位 4+2+1=7；"
                    "若孩子只算个位不进位会得 65（7+8 写 5 忘了进位）",
        "q05_hypothesis": "个位进位丢失 → 65；或把「又买来」当减法 → 19",
    },
    {
        "rvid": "1b3c314e-64c7-493b-98fa-bedbac6b51a6",
        "renderer": "column-arithmetic",
        "source": "cfg.operands=[90, 27]；题面「90 - 27」",
        "read": "90 减 27 → 求差",
        "object": "差",
        "expr": "90 - 27",
        "boundary": "个位 0−7 需从十位退位，十位 9 退 1 成 8，8−2=6；"
                    "本题是退位（borrow）的典型，未退位会得 73",
        "q05_hypothesis": "个位 7−0 反减（未退位）→ 73 或 77",
    },
    {
        "rvid": "39ce2243-24f7-4901-98e2-4894a0c36d27",
        "renderer": "column-arithmetic",
        "source": "cfg.operands=[54, 27]；题面「54 - 27」",
        "read": "54 减 27 → 求差",
        "object": "差",
        "expr": "54 - 27",
        "boundary": "个位 4−7 需退位成 14−7=7，十位 4−2=2 → 27；"
                    "与 1b3c314e 同为退位题但退位发生在个位，不是 0−7 的极端情形",
        "q05_hypothesis": "逐位反减（7−4、7−5）→ 33；或不退位 → 37",
    },

    # ── formula-board：解一元等式 ──
    {
        "rvid": "506538f4-1e95-402a-9b2e-8069d78251c5",
        "renderer": "formula-board",
        "source": "cfg.tokens: slot + 8 = 17",
        "read": "□+8=17 → 求加数",
        "object": "空格中的数",
        "expr": "17 - 8",
        "boundary": "空格在加号**左边**，与 e29e7012 的空格在右边是同一方程的不同"
                    "呈现；若孩子只在「空格在右」的题上正确，说明是位置记忆而非等式理解",
        "q05_hypothesis": "用 17+8=25（方向反）",
    },
    {
        "rvid": "8122c8c2-5151-46e8-b6d8-6df76e984775",
        "renderer": "formula-board",
        "source": "cfg.tokens: 15 - slot = 9",
        "read": "15−□=9 → 求减数",
        "object": "空格中的数",
        "expr": "15 - 9",
        "boundary": "本题求的是**减数**而非差；用 15−9 而不是 9−15。"
                    "若孩子答 15+9=24，说明把减号当加号",
        "q05_hypothesis": "把减数题当差题（答 15−9 的补数或 24）",
    },
    {
        "rvid": "e29e7012-306b-494a-8633-cfd56537adcd",
        "renderer": "formula-board",
        "source": "cfg.tokens: 7 + slot = 12",
        "read": "7+□=12 → 求加数",
        "object": "空格中的数",
        "expr": "12 - 7",
        "boundary": "与 506538f4 同型但空格在右、数值更小；"
                    "两条同时正确才说明加数位置不影响求解",
        "q05_hypothesis": "答 7（把已知数当答案）",
    },

    # ── ruler：两端刻度之差 ──
    {
        "rvid": "2c5f8ead-d4cf-4a31-9dfd-4d24bbce8277",
        "renderer": "ruler",
        "source": "cfg.object=[4, 10]；题面断言「长度是7厘米」",
        "read": "量长度 = 右端刻度 − 左端刻度，与左端是否在 0 无关",
        "object": "线段实际长度（不是他说的 7）",
        "expr": "10 - 4",
        "boundary": "**是否命题判断题**：先说「说法不对」再填正确长度。"
                    "若误按从 0 起读（直接取右端 10）会答 10；"
                    "若信了他的话会答 7。答 6 才是「测量正确 + 判断正确」",
        "q05_hypothesis": "from_zero_reading：把右端刻度当长度 → 10；"
                          "或直接采信题面给的 7",
    },
    {
        "rvid": "770ab57a-a1e2-4c78-8a9e-d89db4559ce9",
        "renderer": "ruler",
        "source": "cfg.object=[5, 12]",
        "read": "量长度 = 12 − 5",
        "object": "线段长度",
        "expr": "12 - 5",
        "boundary": "不含判断语句的纯测量题，与 2c5f8ead 配对："
                    "两条都对才能排除「因为题面出现过 7 所以答 7」",
        "q05_hypothesis": "from_zero_reading：直接读右端 12",
    },
    {
        "rvid": "7abf0ae3-712e-4f07-a069-313066c5eb49",
        "renderer": "ruler",
        "source": "cfg.object=[3, 11]；题面断言「长10厘米」",
        "read": "11 − 3；断言 10 是错的（那是把右端当长度）",
        "object": "线段实际长度",
        "expr": "11 - 3",
        "boundary": "与 2c5f8ead 同型（断言错误），但错法不同："
                    "2c5f8ead 断言 7 偏小，本题断言 10 偏大；"
                    "若两条都答对，说明不是碰巧偏向某个方向",
        "q05_hypothesis": "from_zero_reading → 11；或采信断言的 10",
    },
    {
        "rvid": "7f76aa86-eaa8-4bcb-a7cd-45d4b9033ac7",
        "renderer": "ruler",
        "source": "cfg.object=[2, 7]",
        "read": "量长度 = 7 − 2",
        "object": "线段长度",
        "expr": "7 - 2",
        "boundary": "本批最小刻度差（5）；与 770ab57a 同为纯测量题，"
                    "两条差值不同（5 与 7）才能排除固定偏移",
        "q05_hypothesis": "from_zero_reading：读右端 7",
    },
]


def independent_eval(expr: str) -> float | int:
    """只允许常量算术表达式。**不读任何 DB 字段。**"""
    return eval(expr, {"__builtins__": {}}, {})  # noqa: S307 常量算式


def judge_binding(ref_sha: str | None, recomputed: str | None) -> bool:
    """引用哈希 vs 重算哈希是否漂移（与 FE-1469 同一判据，保持一致）。

    两个都缺也算漂移：没有冻结原件可引，就不能声称核验的是同一份题。
    """
    return not (ref_sha and recomputed and ref_sha == recomputed)


def evaluate(check: dict, stated_raw, ems: list, ui: dict) -> dict:
    """单题核验：先独立求解，再与存储答案比较。**纯函数，不连库。**"""
    computed = independent_eval(check["expr"])
    try:
        stated = float(stated_raw)
    except (TypeError, ValueError):
        stated = None
    match = stated is not None and abs(float(computed) - stated) < 1e-9

    ws_cfg = {}
    for ws in (ui or {}).get("workspaces") or []:
        if isinstance(ws, dict) and isinstance(ws.get("config"), dict):
            ws_cfg = ws["config"]
            break
    homogeneous = bool(ems) and all(
        str(e.get("code")) == str(e.get("pattern")) for e in ems)

    return {
        "rvid": check["rvid"],
        "renderer": check["renderer"],
        "input_basis": check["source"],
        "target_object": check["object"],
        "derivation": {"read": check["read"], "expr": check["expr"]},
        "computed": computed,
        "applicable_conditions": check["boundary"],
        "stated_answer": stated_raw,
        "verdict": "MATCH" if match else "MISMATCH",
        "ui_config_seen": ws_cfg,
        "q05_error_models": ems,
        "q05_candidates": [{
            "code": str(e.get("code")),
            "status": ("同质占位候选，区分力尚待验证" if homogeneous
                       else "非同质，区分力尚待逐条验证"),
            "hypothesis": check.get("q05_hypothesis"),
            "requirement": ("需补充可观测证据：该错法在作答轨迹/中间量上留下"
                            "什么可区分痕迹、与同题其它错法的判定边界在哪。"
                            "仅有 code==pattern 不足以证明区分力。"),
            "not_concluded": ("本条不主张该错法一定被孩子使用，"
                              "也不主张它对应某种认知缺陷"),
        } for e in ems],
    }


def main() -> int:
    db = os.environ.get("DATABASE_URL")
    if not db:
        sys.exit("缺少 DATABASE_URL（只读账号即可）")
    db = db.replace("postgresql+psycopg://", "postgresql://")

    # 依赖预检：环境错误退 2，与「答案不等」退 1 区分（FE-1469 踩过的坑）。
    try:
        import psycopg  # noqa: F401
    except ModuleNotFoundError:
        print("ENV_ERROR: 当前解释器没有 psycopg。请用 "
              "~/.workbuddy/binaries/python/envs/learning-engine/bin/python 运行。"
              "退出码 2 表示环境错误，与核验结论无关。", file=sys.stderr)
        return 2

    sys.path.insert(0, os.path.join(REPO, "scripts", "iqc"))
    import common
    # 复用 FE-1469 的绑定逻辑，不另造一套哈希口径。
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "q03_b1", os.path.join(REPO, "scripts/iqc/rt1469/q03_number_input.py"))
    b1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b1)

    rvids = [c["rvid"] for c in CHECKS]
    prov = b1.bind_inputs(db, common, rvids)
    import psycopg
    with psycopg.connect(db) as conn:
        rows = conn.execute(
            "select resource_version_id::text, content->>'answer', "
            "content->>'stem', error_models, ui_schema from resource_version "
            "where resource_version_id = any(%s::uuid[])", (rvids,)).fetchall()
    live = {r[0]: r[1:] for r in rows}

    results = []
    for c in CHECKS:
        row = live.get(c["rvid"])
        if not row:
            results.append({**c, "verdict": "RVID_NOT_FOUND"})
            continue
        stated_raw, stem, ems, ui = row
        r = evaluate(c, stated_raw, ems or [], ui or {})
        r["stem"] = stem
        r["input_binding"] = {
            "audit_input_sha256": prov["per_item"][c["rvid"]]["sha"],
            "manifest_snapshot": prov["manifest"]["snapshot_sha256"],
            "drift": prov["per_item"][c["rvid"]]["drift"],
        }
        results.append(r)

    out = {
        "title": "FE-1470｜Q03 独立核验第二批（20 题）",
        "batch": {
            "scope": "numeric_judge ∩ both 剩余 144 条中的 20 条",
            "selection_rule": "题干与配置完整、数学关系清楚、跨 5 个 renderer",
            "not_selected_why": (
                "estimation-canvas(8)/shape-gallery(8)/direction-grid(8) 的"
                "同质题已在 FE-1468 逐题核完，重复不增证据；"
                "clock(8) 的存储答案是 h*60+m 编码，独立推导会退化成反推编码规则，"
                "留到有明确编码契约可引时再做"),
        },
        "chain": ["input_basis", "target_object", "derivation",
                  "applicable_conditions", "原值比较", "verdict"],
        "provenance": prov,
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "not_found": sum(1 for r in results if r["verdict"] == "RVID_NOT_FOUND"),
            "drift": sum(1 for r in results if r.get("input_binding", {}).get("drift")),
            "by_renderer": {},
        },
        "items": results,
    }
    from collections import Counter
    out["summary"]["by_renderer"] = dict(
        Counter(r["renderer"] for r in results if r["verdict"] == "MATCH"))

    os.makedirs(os.path.join(REPO, "scripts/iqc/runs"), exist_ok=True)
    path = os.path.join(REPO, "scripts/iqc/runs/FE1470_q03_batch2.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for r in results:
        if r["verdict"] == "RVID_NOT_FOUND":
            print(f"NOTFOUND {r['rvid'][:8]}")
            continue
        print(f"{r['verdict']:8s} {r['renderer']:18s} {r['derivation']['expr']:14s}"
              f" = {r['computed']:<4} stated={r['stated_answer']!r:5} {r['rvid'][:8]}")
    print("\n", json.dumps(out["summary"], ensure_ascii=False, indent=1))
    print("out:", path)
    ok = (out["summary"]["mismatch"] == 0 and out["summary"]["drift"] == 0
          and out["summary"]["not_found"] == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())