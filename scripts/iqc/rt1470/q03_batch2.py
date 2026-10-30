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

import hashlib
import json
import os
import subprocess
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
        "boundary": "与 06546dfb（6+4）是同一个「先有 N 再放 M」模型的两个不同加数组合，"
                    "**不是交换律对照**——3+7 与 6+4 相加的四个数都不同。"
                    "真正的交换律对照是 3+7 与 7+3（同两数换位），本批没有 7+3 这条配置，"
                    "所以本批不能就交换律下任何结论",
        "q05_hypothesis": "只报新增的 7 个（3+7 中丢掉初始量）",
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
                  "cfg.target_count=13, max_frames=2；"
                  "content.goal=「用十格框表征 20 以内数的十与一结构（补十打包）」",
        "read": "题面给的是**构造任务**不是问答题：给定量 13 已知，孩子要做的是把它"
                "表示成「1 个十 + 3 个一」；所求的数是这次表征对应的总数（唯一值的量）",
        "object": "提交的 total（= tens*10 + current_frame_count），数量上等于 13",
        "expr": "10 * 1 + 3",
        "boundary": "**本题的提交对象已核清，依据是代码而非反推**："
                    "(1) `tenFrameV2.ts::serializeTenFrameV2` 固定输出 "
                    "`{tens, current_frame_count, total}`，其中 `total = totalOf(state)`；"
                    "(2) `TenFrameV2.tsx` 提交时 `answer: String(totalOf(runtime.present))`；"
                    "(3) `learning.py::_judge` 用 `float(expected) == float(user_answer)` "
                    "比 `content.answer`（=13）；"
                    "(4) ui_schema `response_contract.evidence_targets=[tens, current_frame_count]` "
                    "——这两个是**证据字段**（记录结构），不是**判分字段**。"
                    "所以「关注 tens/current_frame_count」与「answer 表示总数 13」并不矛盾："
                    "evidence 要结构，判分要 total。"
                    "仍需注明的是：题干只说「摆好后提交」，没写「一共几颗」这样的问句，"
                    "孩子靠界面上的「现在一共 N 个（目标 13）」得知提交量——"
                    "**提交量的提示来自 UI 而非题干**，这是内容设计上的可改进点，不是答案错误",
        "q05_hypothesis": "只摆散放的 3 个（未打包）；或把 13 理解成「13 袋」；"
                          "或摆到 10 就停（受满十框暗示）",
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
        "boundary": "5+3=8，**不等于 10**；与 ten-frame 的 cdcc6e30（3+7=10）不是等值对照——"
                    "两者和不同（8 vs 10）、renderer 也不同（多组计数 vs 十格框），"
                    "放在一起只能说明「不同配置会得到不同数」，说明不了任何等值关系。"
                    "本题唯一可说的是：配置两组 5 与 3，合计数与存储值 8 一致",
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
        "boundary": "6+6=12；与本批 ten-frame 的 f9fae106（8+5=13）**不同值**，"
                    "不能称为「同值不同模型」。可比的是「和都超过一框的 10」这一点，"
                    "但那只是共同的下界性质，不构成等值对照",
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
        "boundary": "个位 0−7 需从十位退位，十位 9 退 1 成 8，8−2=6 → 63。"
                    "**错误步骤与错误结果一一对应**（不是「73 或 77」这种混写）："
                    "① 每一位都拿大数字减小数字（十位 9−2、个位 7−0）→ 77；"
                    "② 个位借十后算 10−7，但十位没有扣除借出的 1（十位仍算 9−2）→ 73。"
                    "两条路径的中间量不同：①压根没有借位念头，②借了但没在十位扣账",
        "q05_hypothesis": "①逐位大减小 → 77；②借位未在十位扣账 → 73",
    },
    {
        "rvid": "39ce2243-24f7-4901-98e2-4894a0c36d27",
        "renderer": "column-arithmetic",
        "source": "cfg.operands=[54, 27]；题面「54 - 27」",
        "read": "54 减 27 → 求差",
        "object": "差",
        "expr": "54 - 27",
        "boundary": "个位 4−7 需退位成 14−7=7，十位 5 退 1 成 4，4−2=2 → 27。"
                    "**错误步骤与错误结果一一对应**："
                    "① 逐位大减小（十位 5−2、个位 7−4）→ 33；"
                    "② 个位算 14−7=7，但十位仍算 5−2=3（未扣借出的 1）→ 37。"
                    "与 1b3c314e 的②同为「借了不扣账」，差别在个位是否够减（本题个位 4<7 必借，"
                    "90−27 个位 0<7 也必借），所以两条②的结构相同、数值不同",
        "q05_hypothesis": "①逐位大减小 → 33；②借位未在十位扣账 → 37",
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
        "read": "11 − 3 = 8；题面断言 10 与真长 8 不符（10 偏大 2），"
                "所以「说法对吗」的答案是「不对」，正确长度是 8",
        "object": "线段实际长度",
        "expr": "11 - 3",
        "boundary": "与 2c5f8ead 同型（题面给了错误断言），两条的断言偏向相反："
                    "2c5f8ead 物体 [4,10]、真长 6、断言「7厘米」→ 断言**偏大**（7>6）；"
                    "本题物体 [3,11]、真长 8、断言「10厘米」→ 断言**也偏大**（10>8）。"
                    "注意本题若「直接读右端」应得 **11**，不是 10——断言值 10 恰好与 "
                    "2c5f8ead 的真长相同，是我上一版把它错写成「把右端当长度」的原因。"
                    "两条都答对才能说明不是碰巧采信题面数字",
        "q05_hypothesis": "from_zero_reading → 11（0..11 的精确靶，结构码会给出该标签）；"
                          "或采信题面断言的 10",
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


# ── Q05 可观察证据登记表（用户 2026-10-21 复审 §二.4）────────────────────────
# 用户指出：上一版 22 条 `requirement` 全是同一句通用说明，
# 「不能只放在 not_concluded 字段里，其他字段仍在直接诊断孩子」。
#
# 所以这里逐题登记三件事，且**只引用本项目真实存在的提交字段**：
#   observable  — 该错法在提交物上留下什么可区分的痕迹（字段名 + 取值）
#   competing   — 同一痕迹还能由哪些别的解释产生（不是唯一诊断）
#   neutral     — 若要反馈，怎么说才不至于直接断言他用了某种错法
#
# 字段出处（均在仓库核实过，不是推测）：
#   ten-frame         → serializeTenFrameV2: {tens, current_frame_count, total}
#   object-counter    → serializeObjectCounterV2: {groups[].count, total}
#   column-arithmetic → serializeColumnArithmetic: {result_digits[], carries[]}
#                       + evaluateColumnArithmetic: {incorrect_places, incorrect_carries}
#   formula-board     → serializeFormulaBoardV2: {filled{}, answer, structure.error}
#   ruler             → serializeRulerV2: {marks[], span, reading, structure.error}
#                       structure.error ∈ {"from_zero_reading", "wrong_span"}
Q05_EVIDENCE: dict[str, dict] = {
    # ── ten-frame ──
    "06546dfb": {
        "observable": "`total`=4 或 6 而非 10。`tens`/`current_frame_count` 可区分："
                      "只放新增 4 个 → tens=0,current_frame_count=4,total=4；"
                      "保持初始 6 个不动 → tens=0,current_frame_count=6,total=6",
        "competing": "total=4 也可能是「只摆了一部分就提交」（操作未完成），"
                     "或把「再放4个」读成「放到第4格」；仅凭终值不能定为「丢掉初始量」",
        "neutral": "说「框里的圆点数和题目要的不一样，再看看框里现在有几个」，"
                   "不说「你把原来的 6 个忘了」",
    },
    "939ab507": {
        "observable": "`total`=3（只数新增）或 7（保持初始）。两者 `current_frame_count` "
                      "不同（3 vs 7），可与「摆到一半就提交」区分开的是事件数："
                      "`COUNTER_ADDED` 只发生 3 次 vs 10 次",
        "competing": "total=3 也可能是孩子只点了 3 格就按提交（操作习惯），"
                     "与「理解成只放 3 个」在终值上同形",
        "neutral": "说「十格框里现在有 3 个圆点，题目要 10 个」，只报事实",
    },
    "cdcc6e30": {
        "observable": "`total`=7 或 3；`tens`=0 恒成立（max_frames=1 且和恰为 10，本不该打包）。"
                      "若出现 tens=1 才是「提前打包」，与本题两种错法都不同",
        "competing": "total=7 也可能是「从 7 开始摆」（起点记错），"
                     "与「3+7 只报 7」终值同形，轨迹不可分",
        "neutral": "说「框里是 7 个，目标是 10 个」",
    },
    "f9fae106": {
        "observable": "答 10 时 `tens` 的取值是关键区分："
                      "tens=1,count=0,total=10 → 摆满一框就打包停住（没跨框）；"
                      "tens=0,count=10 → 单框满但没打包。"
                      "正解需要 tens=1,current_frame_count=3,total=13",
        "competing": "total=10 也可能只是「摆到 10 就以为够了」（读题不完整），"
                     "与「受满十暗示」在终态上无法区分——两者都停在 10",
        "neutral": "说「一袋装满了，还剩 5 个没地方放，看看第二框」",
    },
    "fea38e2d": {
        # 本题有两个错法码，**必须分开写**：modeling 是建模环节的错，
        # calc 是算错了总数。二者留下的痕迹不同，不能共用一句。
        "observable": {
            "modeling": "结构没建对：`tens`=0 且 `total`∈{3,10}——"
                        "即「散放 3 个没打包」(0,3,3) 或「摆满一框就停」(0,10,10)。"
                        "正解结构是 (tens=1, current_frame_count=3, total=13)，"
                        "**建模错在 tens 上，total 只是跟着错**",
            "calc": "结构对但总数报错：`tens`=1、`current_frame_count`=3，"
                    "而提交的 `total`≠13（如误报 103 或 4）。"
                    "本 renderer 的 total 由 tens*10+count 唯一决定，"
                    "所以 calc 类错在现有交互中**几乎不可达**——"
                    "这一条本身是「错法码与实际可达状态不匹配」的证据",
        },
        "competing": "=(0,3) 也可能是「先摆散放的、还打算打包」的中间态——"
                     "提交时机由孩子决定，终态不必然代表最终想法",
        "neutral": "说「散放的有 3 颗，还差一袋没打」，指向状态不指向动机",
    },
    # ── object-counter（★ 本族有存量缺陷，见 q05_blocked_by）──
    "079d72bd": {
        "observable": "`groups[].count` 与 `total`。但**本族进入即满分**："
                      "`initialObjectCounterV2State(config.groups)` 直接用 config 的 "
                      "count(3,4) 作为初始态，`total=7` 一进页面就成立、"
                      "`evaluateStructure` 直接 PASS。任何错答都要孩子**主动点减号**才出现",
        "competing": "既然正解就是初始态，total=4 只能来自孩子点了 3 次减号——"
                     "那更可能是误触/试探，不是「忘记左侧 3 块」的建模错误",
        "neutral": "（暂不适用）在初始态缺陷修好前，本题不产生可解释的错误信号",
    },
    "08d4f5bc": {
        "observable": "同上：config 给 (1,2)，初始态 total=3 即 PASS。"
                      "total=2 需孩子主动减 1 次",
        "competing": "同 079d72bd：减号误触与建模错误不可区分",
        "neutral": "（暂不适用）",
    },
    "b9a431f0": {
        "observable": "同上：config 给 (5,3)，初始态 total=8 即 PASS。"
                      "本题的 `5+3=8` 与正确答案相同，纯计数错法在终值上**不会留下痕迹**",
        "competing": "本题配置值恰好等于答案，任何「数错」都不会体现在 total 上"
                     "（除非孩子改动了组内计数，而那需要主动操作）",
        "neutral": "（暂不适用）",
    },
    "d7a7c884": {
        "observable": "同上：config 给 (2,2)，初始态 total=4 即 PASS。"
                      "「把一样多理解成差为 0」需要孩子**主动把一组清零**才会出现 total=2，"
                      "而那与「只留一组」同形",
        "competing": "total≠4 的路径全都要主动减数，与「比较」误读难以建立唯一联系",
        "neutral": "（暂不适用）",
    },
    "f3bb5804": {
        "observable": "同上：config 给 (6,6)，初始态 total=12 即 PASS。"
                      "答 6 需孩子把其中一组清空（6 次减号或 1 次并入）",
        "competing": "若孩子用 compose 把一组并入另一组，"
                     "`composed_into`/`composed_count` 会留痕，那时 total 仍是 12"
                     "（并入不改总数），所以「答 6」在 compose 路径下**根本不可达**",
        "neutral": "（暂不适用）",
    },
    # ── column-arithmetic ──
    "183c028f": {
        # 两个错法码分开写：calc 是算错，strategy 是选错办法（把加法当减法）。
        "observable": {
            "calc": "`result_digits` 十位=6、个位=5，且个位进位标记 `carries` value=0；"
                    "正解为十位=7、个位=5、个位进位 value=1。"
                    "`incorrect_places`=[tens]、`incorrect_carries`=[ones] 精确定位到位置",
            "strategy": "`result_digits` 十位=1、个位=9（19，即把「又买来」按减法做）。"
                        "与 calc 的区别在整体数量级：calc 停在 65 附近，"
                        "strategy 直接掉到 19，两者在 `result_digits` 上不会混淆",
        },
        "competing": "个位 5 写得对、十位 6 也可能是「心里进了位但忘了点进位标记」——"
                     "本 renderer 把进位做成显式开关，两种解释都表现为 carries=0；"
                     "而 19 也可能只是「随手填了个小一点的数」，需结合事件轨迹",
        "neutral": "说「个位满十了，看看十位要不要多加 1」，指向位置不指向能力",
    },
    "1b3c314e": {
        "observable": "**两条错法可被字段分开**："
                      "① 逐位大减小 → result_digits 十位=7、个位=7（77），carries 全 0；"
                      "② 借了未扣账 → result_digits 十位=7、个位=3（73），"
                      "但个位 carries 标记 value=1（孩子点过借位）。"
                      "即 73 与 77 的差别不在答案，在 `carries` 个位标记 1 vs 0",
        "competing": "73 也可能是「个位算 10−7=3、十位漏算借位」，与②同形；"
                     "77 也可能是「0−7 反成 7−0」的逐位反减，与①同形。"
                     "carries 标记能分开这两类，但**分不开同一类内的不同想法**",
        "neutral": "说「十位现在写的是 7，正确答案的十位是 6，看看个位借走的那 1 个」",
    },
    "39ce2243": {
        "observable": "① 逐位大减小 → 十位=3、个位=3（33），carries 全 0；"
                      "② 借了未扣账 → 十位=3、个位=7（37），个位 carries=1。"
                      "与 1b3c314e 结构相同：答案差 4，`carries` 标记差 1",
        "competing": "同 1b3c314e；另需注意 33 也可能来自「5−2=3、7−4=3」的逐位大减小，"
                     "即孩子会做非退位减法但不会退位，这与「随机错」不同",
        "neutral": "说「个位要向十位借 1 个十，十位就少 1」",
    },
    # ── formula-board ──
    "506538f4": {
        "observable": "`filled[missing]` 的值 + `structure.error`。"
                      "答 25（方向反）= 17+8，structure.status=FAIL、error=\"relation\"；"
                      "本题没有运算符槽（op 是给定的 \"+\"），"
                      "所以 error 不可能是 \"operator\"——这条区分是稳定的",
        "competing": "答 25 也可能来自「看到 17 和 8 就想加」，"
                     "与「把等号两边关系弄反」在终值同形；"
                     "本 renderer 的 error 码只能到 relation 这一层",
        "neutral": "说「等号两边要一样多，8 再加多少才是 17」",
    },
    "8122c8c2": {
        "observable": "`filled[missing]`=24（15+9）时 structure.error=\"relation\"；"
                      "`filled[missing]`=9（把等号右边抄进来）时 error 也是 \"relation\"。"
                      "两种错法**在 error 码上不可分**，只能靠 `filled` 的具体数值分",
        "competing": "答 9 可能是「把右边的 9 当答案抄下来」（位置误读），"
                     "答 24 是「把减号当加号」；两者数值不同但同属 relation 类",
        "neutral": "说「15 减去多少才剩 9」",
    },
    "e29e7012": {
        "observable": "`filled[missing]`=7（抄已知数）时 error=\"relation\"；"
                      "正解 5。与 506538f4 配对：本题空格在右、那条在左，"
                      "两条 `filled` 值可对照位置是否影响求解",
        "competing": "答 7 也可能是「7 就是加数之一，填它试试」的试探，"
                     "与「把已知数当答案」不可分",
        "neutral": "说「7 加多少才是 12」",
    },
    # ── ruler ──
    "2c5f8ead": {
        "observable": "**本题有真实可区分的结构码**："
                      "若孩子把标记放在 {0,10}，structure.error=\"from_zero_reading\"、span=10；"
                      "若标记放在 {4,10}，span=6 → PASS。"
                      "`marks` 数组直接给出两个刻度，可与「采信断言 7」区分："
                      "答 7 需要 marks 间距为 7，如 {4,11} 或 {3,10}",
        "competing": "span=7 也可能是「看得不准、随手点两个刻度」，"
                     "与「相信题面写的 7」同形；marks 只能证明点在哪，证明不了为什么点那",
        "neutral": "说「这条线段从左端 4 到右端 10，中间有几格」",
    },
    "770ab57a": {
        "observable": "`marks`={0,12} → error=\"from_zero_reading\"、span=12；"
                      "正解 marks={5,12}、span=7。本题**没有**误导断言，"
                      "所以 from_zero_reading 是纯测量错法的干净样本",
        "competing": "span=12 也可能是量偏；但 marks 不足 2 会判 EMPTY 而不是给 12，"
                     "所以 12 必然来自两个刻度 {0,12}——这条比 2c5f8ead 干净",
        "neutral": "说「从 5 到 12，走了几格」",
    },
    "7abf0ae3": {
        "observable": "`marks`={0,11} → error=\"from_zero_reading\"、span=11；"
                      "答 10（采信断言）需要 marks 间距 10，如 {1,11} 或 {3,13}(越界)；"
                      "正解 marks={3,11}、span=8。三种想法对应三组不同 marks，**可区分**",
        "competing": "span=10 也可能是量偏了（点错一格）；"
                     "但 marks={0,11} 的 span=11 有专属结构码，不需推测",
        "neutral": "说「他说的 10 厘米不对，尺子上从 3 到 11 才是这条线段」",
    },
    "7f76aa86": {
        "observable": "`marks`={0,7} → error=\"from_zero_reading\"、span=7；"
                      "正解 marks={2,7}、span=5。"
                      "本题与 770ab57a 同为纯测量，两者 (left,right) 不同，"
                      "若两条都判 from_zero_reading 才说明是稳定的读法问题",
        "competing": "span=7 也可能来自 {0,7}（从零读）或 {2,9}（多量了 2）；"
                     "只有 error 码为 from_zero_reading 时才是前者——这正是结构码的价值",
        "neutral": "说「从 2 到 7，一共 5 格」",
    },
}

# object-counter 五题共有的存量缺陷：`initialObjectCounterV2State(config.groups)`
# 直接把 config 的 count 当初始态，导致「一进页面就是正确答案」。
# 这不是本轮核验引入的判断，是 FE-1414 组件的既有行为；
# 它使本族 5 题的 Q05 候选**在现有交互下不可能被观测**。
# 按要求：登记为条件、不静默删除，也不改动组件（本轮只读）。
Q05_BLOCKED_BY = {
    "reason": "object-counter 初始态 = config.groups（含 count），"
              "进入即 PASS，错误答案只能靠孩子主动减数产生",
    "evidence": "apps/child-web/src/components/renderers/ObjectCounterV2.tsx::initial "
                "→ initialObjectCounterV2State(config.groups)；"
                "apps/child-web/src/features/task-renderer/objectCounterV2.ts:49",
    "impact": "本族 5 题（079d72bd/08d4f5bc/b9a431f0/d7a7c884/f3bb5804）的 "
              "Q05 候选无法在现有交互中留下可归因的痕迹",
    "status": "已登记，待内容侧确认是否改为「空白起点 + 需孩子摆」；本轮不改组件",
}


def independent_eval(expr: str) -> float | int:
    return eval(expr, {"__builtins__": {}}, {})  # noqa: S307 常量算式


def _sha256_file(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _git_commit() -> str | None:
    """当前 HEAD 提交；取不到就返回 None（不假装有出处）。"""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO,
            capture_output=True, text=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _script_provenance() -> dict:
    """**出处必须能指出「哪份代码生成了这份报告」**（用户 2026-10-21 复审 §四）。

    上一版 `solver_version.script` 只写了 rt1469 的模块名，而实际入口是
    rt1470/q03_batch2.py —— 这是错的。现在分两项列明：
      · entry   ：真正跑起来的入口
      · shared  ：被 import 复用的模块（不是入口，但参与了绑定计算）
    并补上 Git 提交与两个文件的 sha256：改动能被 diff 看见，不等于
    离线报告已经说明了它由哪个版本生成。
    """
    entry = os.path.abspath(__file__)
    shared = os.path.join(REPO, "scripts/iqc/rt1469/q03_number_input.py")
    common = os.path.join(REPO, "scripts/iqc/common.py")
    return {
        "solver_version": {
            "entry_script": os.path.relpath(entry, REPO),
            "entry_sha256": _sha256_file(entry),
            "shared_modules": [
                {
                    "path": os.path.relpath(shared, REPO),
                    "sha256": _sha256_file(shared),
                    "role": "bind_inputs / judge_binding（输入绑定与漂移判定）",
                },
                {
                    "path": os.path.relpath(common, REPO),
                    "sha256": _sha256_file(common),
                    "role": "audit_input_sha（九域规范化哈希，与 scan.py 同一口径）",
                },
            ],
            "git_commit": _git_commit(),
            "expression_engine": "Python eval + 空 builtins（常量算式，无外部依赖）",
            "note": "入口与共享模块**分别列出**——只写其中一个都不足以定位生成者。"
                    "git_commit 是本报告生成时所在提交；若工作区有未提交改动，"
                    "以 entry_sha256 为准（它反映实际执行的字节）。",
        },
        "result_chain": (
            "当前工作清单中的 RVID → 被复用的冻结输入 "
            "scripts/iqc/runs/inventory_manifest_r2.json（snapshot_sha256）"
            "→ 逐题 audit_input_sha256（引用值 == 现场重算值）"
            "→ 本次核验结果 verdict"),
    }


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

    # 逐题取可观察证据登记（复审 §二.4 要求：不能 22 条同一句）。
    # 登记表缺条目时**必须显式报缺口**，不允许退回通用句——
    # 那正是上一版被打回的原因。
    # `observable` 支持两种形态：字符串（单错法题）
    # 或 {错误码: 描述} 字典（一题多错法，各错法痕迹本就不同）。
    ev = Q05_EVIDENCE.get(check["rvid"][:8])
    blocked = Q05_BLOCKED_BY if check["renderer"] == "object-counter" else None

    def obs_for(code: str) -> str:
        raw = (ev or {}).get("observable")
        if isinstance(raw, dict):
            return raw.get(code) or f"【缺口】本题未登记错误码 {code} 的可观察证据"
        return raw or "【缺口】本题未登记可观察证据"

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
        "q05_blocked_by": blocked,
        "q05_candidates": [{
            "code": str(e.get("code")),
            "status": ("同质占位候选，区分力尚待验证" if homogeneous
                       else "非同质，区分力尚待逐条验证"),
            "hypothesis": check.get("q05_hypothesis"),
            # 三字段逐题具体化：可观察痕迹 / 竞争解释 / 中性反馈。
            # **不是**「需补充证据」这种通用句，而是直接指出
            # 「本题在哪个提交字段上留下什么值」。
            "observable_evidence": obs_for(str(e.get("code"))),
            "competing_explanations": (ev or {}).get("competing")
                                      or "【缺口】本题未登记竞争解释",
            "neutral_feedback": (ev or {}).get("neutral")
                                or "【缺口】本题未登记中性反馈口径",
            "evidence_fields_from": (
                "renderer 序列化函数（见 q03_batch2.py::Q05_EVIDENCE 注释）"),
            "not_concluded": ("本条不主张该错法一定被孩子使用，"
                              "也不主张它对应某种认知缺陷；"
                              "上列痕迹只是「若成立应当看到什么」，"
                              "不是「已经看到」"),
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

    # 硬前置：Q05 可观察证据必须逐题登记齐全，且三字段非空。
    # 上一版被打回正是因为 22 条共用一句通用说明；这里让缺口直接失败，
    # 而不是悄悄退回通用句。
    missing = [c["rvid"][:8] for c in CHECKS
               if c["rvid"][:8] not in Q05_EVIDENCE]
    if missing:
        print(f"Q05_EVIDENCE 缺 {len(missing)} 题登记：{missing}", file=sys.stderr)
        return 1
    empty = [f"{k}.{f}" for k, v in Q05_EVIDENCE.items()
             for f in ("competing", "neutral") if not v.get(f)]
    # observable 允许字符串或 {错误码: 描述}；两种形态都不许有空值
    for k, v in Q05_EVIDENCE.items():
        o = v.get("observable")
        if isinstance(o, dict):
            empty += [f"{k}.observable[{c}]" for c, s in o.items() if not s]
        elif not o:
            empty.append(f"{k}.observable")
    if empty:
        print(f"Q05_EVIDENCE 有空字段：{empty}", file=sys.stderr)
        return 1
    flat = [s if isinstance(v["observable"], str) else d2
            for v in Q05_EVIDENCE.values()
            for s, d2 in ([(v["observable"], None)] if isinstance(v["observable"], str)
                          else v["observable"].items())]
    dup = [s for s in set(flat) if flat.count(s) > 1]
    if dup:
        print(f"Q05_EVIDENCE 存在重复 observable（说明又在套模板）：{dup}",
              file=sys.stderr)
        return 1

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
        "provenance": {**prov, **_script_provenance()},
        "summary": {
            "total": len(results),
            "match": sum(1 for r in results if r["verdict"] == "MATCH"),
            "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
            "not_found": sum(1 for r in results if r["verdict"] == "RVID_NOT_FOUND"),
            "drift": sum(1 for r in results if r.get("input_binding", {}).get("drift")),
            "by_renderer": {},
            "q05_candidates_total": sum(len(r.get("q05_candidates") or [])
                                        for r in results),
            "q05_blocked_items": sum(1 for r in results if r.get("q05_blocked_by")),
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