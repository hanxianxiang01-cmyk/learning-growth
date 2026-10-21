#!/usr/bin/env python3
"""FE-1471：Q03 独立核验第三批（额定 20 题，实核 29 题；`legacy:*` + `bar-model`）。

**账要分开记，但不许把「记录缺失」记成「题的身份不明」：**

| 项 | 数 | 依据 |
|---|---|---|
| 计划 | 约 20 | 复审第七项原文是「**约**20 题」，不是「只能 20 题」 |
| 实核 | 29 | 本文件 `CHECKS` 条数，也是工件 `summary.total` |
| 后补入 | 7 | DEF-D1 补 4（`8b121389`/`c88410f2`/`e5c13ef5`/`04f97cb8`）<br>+ DEF-D2 补 3（`421ede36`/`6e5395f0`/`8981fbcc`），有分组注释与补入理由 |
| 身份完整性 | 29/29 | 每条都有完整 UUID、题干、独立推导、存储答案比对 |

**这个 29/29 与「原定 20」的关系（2026-10-21 复审裁决）：**

29 条 RVID 的身份**全部明确**，不存在「结果集里有两条身份不明的记录」。
缺的是**最初选样过程的记录**：那 20 题的冻结名单没有落盘，所以无法反查
「最初那批是哪 20 个 RVID」。因此：

- **不追造历史**：不反推原来 20 个 RVID，不把「29 − 7 − 20 = 2」讲成两条
  来路不明的题；
- **不删题凑 20**：29 条都已实核，删掉反而丢证据；
- **留改进项**：下次开批时先把选题集合写进工件（`quota_list`），扩样时追加
  新增 RVID 及原因，使差额可从工件反查而不靠记忆；
- **门禁不再强制「差额必须未解释」这个固定状态**——那会把一次性的过程瑕疵
  固化成永久门禁条件，逼着后来的人维护一个不再有意义的字段。

补入 7 条的理由是硬的：`KNOWN_DEFECTS[x].affected` 若引用批外 RVID，等于
「缺陷已登记，但登记时没核对过现场」。不过定理式的解法不是「必须扩批」，
而是**缺陷调查可以引用批外题目，只要独立保留其身份、输入和核查证据**。
本批选择扩批，是因为这 7 条确实需要现场核对；「批外发现」与「本批完成数量」
本可以分账，见 `batch.out_of_batch_refs`。

用户 2026-10-21 复审《FE-1470 复审结论与 FE-1471 执行裁决》第七项，逐条对应：

  · 「从 `legacy:*` + `bar-model` 取 20 题」→ 本批**全部**来自这两类（见 `by_renderer`）
  · 「覆盖五类关系：整体与部分、比较差、较大/较小量、连续变化、条件筛选」
  · 「逐题注明 `known` 的角色（已知部分 / 已知整体 / 差量 / **答案副本**）」
     → `known_role` 是**必填第七字段**，且答案副本**不可作为独立推导依据**
  · 「保留手工推导的真实性质，配置模型变异测试**不自动证明题干已被正确解析**」
     → `read` 字段是人读题干后的判定，`expr` 只引用题面出现的数；
       `config_role` 说明配置在本题里扮演什么角色（**不是**推导依据）
  · 「Q05 与 Q03 共同理解题目、分别验收」→ 每题同时给 Q03 推导与 Q05 三字段
  · 「下一次交付的重点应是更多可复算的题意模型，以及少而明确的例外」
     → 例外（EXCEPTION）单列成表，不混进 MATCH

**本批与上一批（batch2）的结构性差别——不写清楚就会重犯上一版的错：**

上一批 20 题全部是 V2 renderer（`ui_schema.workspaces[]` 带 `config`），
配置里的数就是"题面已知量"。本批 29 题里有 **27 题**是 V1 `legacy:*`
（只有 2 题 bar-model 是 V2，见工件 `summary.by_renderer`）：
它们的 `ui_schema.visual` 是**演示参数**（滑杆上限、数轴刻度范围），
**不是**题面的已知量来源。若把 `visual` 里的数当推导依据，等于
「用界面参数反推数学关系」——那正是复审要挡的那类做法。

按 `source_kind` 记（这是本题「独立事实从哪来」的唯一开关）：
`stem_only` 5 / `stem_plus_visual` 22 / `stem_plus_v2config` 2，合计 29。
按 `known_role` 记：已知部分 8 / 已知整体 16 / 差量 0 / 答案副本 5。
**差量为 0 不是漏检**——本批没有被问「差本身」又恰好只给了差量的题；
答案副本 5 条全部落在 DEF-D1。

**关于 `MATCH` 的效力边界（必须在每次汇报里重复）：**

`MATCH` 只表示「按题面独立推导的结果与存储答案相等」。它**不**表示该题的
交互/配置无问题。本批的 `visual_leak` / `unreachable_signal` /
`known_defects` 是**与 MATCH 独立**的另一笔账，必须分开读。

**关于风险条目的证据分层（2026-10-21 复审要求）：**

`KNOWN_DEFECTS` 里的条目在报告中被称作「已登记的交互／配置风险条目」，
不再统称为「已确证缺陷」。每条必须标出 `evidence_tier`：

| tier | 含义 | 允许写成 |
|---|---|---|
| `static_fact` | 只读仓库/配置即可确认的数值或字段事实 | 「配置里 A 等于 B」「字段 X 不存在」 |
| `inference` | 由静态事实推出、但需要额外前提的风险 | 「若前提 P 成立，则存在风险 R」 |
| `needs_runtime` | 必须真实操作/提交才能判定 | 「未经运行验证，不作定论」 |

**不许**把 `static_fact` 直接叙述成「评分已经出错」。例如滑杆上限等于答案
是一个可确认的配置事实，但「孩子只要拖到底就能满分」还需要核对提交契约和
判分路径；「答案数值超过某个上限」也只是线索，不等于任务不可完成。

因此本批每题都显式声明 `source_kind`：

| source_kind | 含义 | 独立事实从哪来 |
|---|---|---|
| `stem_only` | 题面就是全部已知（`legacy:direct`，纯数字输入框） | 题面文字 |
| `stem_plus_visual` | 题面给数，`visual` 只是摆设参数 | 题面文字（visual 不参与推导） |
| `stem_plus_v2config` | V2 `workspaces[0].config` 与题面一致，config 可**交叉复核**题面 | 题面文字，config 作旁证 |

用法：
  DATABASE_URL=... python scripts/iqc/rt1471/q03_batch3.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = <repo>/scripts/iqc/rt1471 → 退三级才是仓库根（同坑已踩四次，见 assert）。
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
assert os.path.isdir(os.path.join(REPO, "scripts", "iqc")), \
    f"REPO 层级算错：{REPO} 下没有 scripts/iqc"

# ── 账目（单一出处）────────────────────────────────────────────────────────
# 「计划多少」与「实际核了多少」是两笔账，必须分开记。本批实情是：
# 计划约 20 题（复审原文「约20题」，不是「只能20题」）→ 实核 29 题，
# 其中 7 条有可追溯的补入依据（缺陷登记需要核对现场）。
#
# 关键口径（2026-10-21 复审裁决）：
#   29 条 RVID 的**身份全部明确**，不存在「结果集里有两条身份不明的记录」。
#   缺的是「最初选样过程的记录」——那 20 题的冻结名单没有落盘，所以无法
#   反查「最初那批是哪 20 个 RVID」。
#   因此本账不设 `gap` / `gap_explained` 这类「差额必须未解释」的固定状态，
#   改为 `selection_record` 明确记录「记录缺失」这件事本身。
LEDGER: dict = {
    "quota": 20,
    "quota_wording": "约 20（复审原文「约20题」）",
    "verified": 29,                      # 必须 == len(CHECKS)
    "traced_extra": 7,
    "traced_extra_breakdown": {
        "DEF-D1": ["8b121389", "c88410f2", "e5c13ef5", "04f97cb8"],
        "DEF-D2": ["421ede36", "6e5395f0", "8981fbcc"],
    },
    "traced_extra_reason": (
        "KNOWN_DEFECTS.affected 若引用批外 RVID，等于「缺陷已登记但登记时"
        "没核对过现场」。本批选择扩批以完成现场核对；但这条不是唯一解法——"
        "缺陷调查也可以引用批外题目，只要独立保留身份、输入与核查证据。"),
    "identity_complete": True,
    "identity_basis": (
        "29/29 有完整 RVID、题干、独立推导与存储答案比对；"
        "与前两批重叠 0；全部位于 numeric_judge ∩ both 队列内。"),
    "selection_record": {
        "frozen_initial_list": None,
        "missing_reason": (
            "最初的选样集合没有在开批时写入工件，事后无法从仓库反查"
            "「计划的那约 20 题具体是哪 20 个 RVID」。"),
        "what_this_is_not": (
            "**不是**「结果集里有 2 条身份不明的记录」，"
            "也**不是**「29 − 7 − 20 = 2 那两条来路不明」。"),
        "remedy": ("下次开批先把选题集合写入工件 quota_list 字段，扩样时追加"
                   "新增 RVID 及原因，使计划与实际可从工件对账；"
                   "不追溯补造本批的历史名单。"),
    },
}

# ── 五类关系的口径（题面层判据，不是 renderer 层判据）────────────────────────
# 复审要求「覆盖五类关系」。这里把每类的**判定依据**写死，避免事后按结果
# 给题贴标签（那是循环论证）。
RELATION_RULES: dict[str, str] = {
    "part_whole": "题面出现「一共有 / 一共多少 / 其余是 / 还剩」等部分—整体措辞，"
                  "且所问量由两个（或多个）部分合成或从整体中分出",
    "difference": "题面出现「比…多 / 比…少 / 相差 / 多几」且**所问就是差量本身**",
    "larger_smaller": "题面出现「比…多 / 比…少」但**所问是较大或较小的那一方**"
                      "（不是差量）",
    "continuous": "同一对象经历**两次以上先后变化**（又来/又走、上来/下去、"
                  "放进/吃掉），所求是变化后的状态",
    "conditional": "题面给了**用不上的信息**（别的物品、别的数量、别的类别），"
                   "或要求**从多个条件里选**出与问题相关的那几个",
}

# ── 独立推导登记表 ──────────────────────────────────────────────────────────
# 字段顺序固定，与复审规定的「输入依据 → 所求对象 → 独立推导 → 适用条件 →
# 与原值比较 → 结论」一一对应；另加 known_role / source_kind / config_role。
CHECKS: list[dict] = [
    # ══ 整体与部分（part_whole）════════════════════════════════════════════
    {
        "rvid": "73dd367b-3883-4621-bdef-3951aee84881",
        "renderer": "bar-model",
        "relation": "part_whole",
        "source_kind": "stem_plus_v2config",
        "known_role": "已知部分",
        "source": "题面「两层书架分别放着5本和7本书」→ 两个已知部分；"
                  "所求「书架上一共有多少本」= 两部分合成",
        "read": "5 本与 7 本是**同一整体的两个部分**（两层书架 = 一个书架），"
                "不是两组独立物品；所求是整体",
        "object": "整体条（answer_bar=c）的长度，= 5 + 7",
        "expr": "5 + 7",
        "config_role": "`workspaces[0].config.known={a:5,b:7}`、`answer_bar=c`、"
                       "`mode=part_whole`。config 与题面**逐值一致**，"
                       "所以这里 config 可以当**旁证**——但它仍然不是推导依据："
                       "推导用的是题面里的 5 和 7",
        "boundary": "**初始态已实测核对**：DB 里 `workspaces[0].initial_state = {}`"
                    "（空对象，不是 `bars:{a:0,b:0,c:0}`），"
                    "而组件侧 `BarModelV2.tsx` 用 `initialBarModelV2State()` "
                    "→ `{bars:{a:0,b:0,c:0}, answerTouched:false}`，"
                    "即**组件不读 initial_state，自己给空态**。"
                    "两条路殊途同归：孩子进页面时三根条都是 0，"
                    "必须自己把 a、b 摆到 5 和 7。这与上一批 object-counter "
                    "「进入即 PASS」的缺陷**恰相反**：bar-model 不会白送分。"
                    "另一处：`max_blocks=14` ≥ 12+1，通过 `parseBarModelConfig` 的"
                    "`maxBlocks >= solved + 1` 守卫，不构成答案副本",
        "q05_hypothesis": "**错误码有优先级，必须先说清顺序**（`evaluateBarModel` "
                          "的执行顺序决定错法归类）："
                          "① 已知条摆错（a≠5 或 b≠7）→ 立即 `modeling`，"
                          "**不管 c 对不对**；"
                          "② 已知条对了但 c ≤ a 或 c ≤ b → `relation`；"
                          "③ 已知条对、结构成立、c≠12 → `calc`。"
                          "所以「只摆 c=12、a 与 b 留 0」实际落到 **modeling**"
                          "（因为 a=0≠5），**不是 calc**——"
                          "要拿到 calc，必须先把 a、b 精确摆对",
    },
    {
        "rvid": "a76ac388-4c00-4888-82f1-6d49e852dfbc",
        "renderer": "bar-model",
        "relation": "part_whole",
        "source_kind": "stem_plus_v2config",
        "known_role": "已知部分",
        "source": "题面「先拿来3张彩纸，又拿来4张彩纸」→ 两次拿来的量都是已知部分",
        "read": "两次「拿来」是**同一堆纸的两个部分**（最后合成一堆），"
                "所求是总数；不是「原来有几张、现在有几张」的状态变化",
        "object": "整体条 c = 3 + 4",
        "expr": "3 + 4",
        "config_role": "`workspaces[0].config.known={a:3,b:4}`、`answer_bar=c`、"
                       "`mode=part_whole`、`max_blocks=12`；与题面一致，可作旁证不作依据",
        "boundary": "与 39b09e38（9+4）、e1e2c896（6+1）、d7fbd744（11+3）"
                    "**同一模板不同加数**。四条放在一起只能说明「模板换数不出错」，"
                    "**说明不了**孩子理解了「又是一次拿来」——后者要 Q05 侧的证据。"
                    "`max_blocks=12` ≥ 8，不泄露答案",
        "q05_hypothesis": "**已按 `evaluateBarModel` 的执行顺序重算，上一版写错了**："
                          "若把「又拿来4张」当最终总数，孩子会把 c 摆成 4、"
                          "而 a、b 仍按题面摆 3 与 4 → 已知条摆对、"
                          "结构判定 `c > a && c > b` 即 4>3 且 4>4 → "
                          "4>4 为假 → **`relation`**（不是 modeling，"
                          "因为 a=3、b=4 都对）。"
                          "另一路径：a 或 b 也摆错 → 先命中 `modeling`，"
                          "**modeling 优先于 relation**",
    },
    {
        "rvid": "5bceb172-2b67-4421-99b2-175ec05b94e9",
        "renderer": "legacy:number-line",
        "relation": "part_whole",
        "source_kind": "stem_plus_visual",
        "known_role": "已知部分",
        "source": "题面「3个相同的小袋子，每个袋子里有7颗玻璃珠」→ 三个相等部分",
        "read": "3 与 7 是「份数」与「每份量」，所求是总量；"
                "这是**等量组的合并**（乘法结构），不是两个不同部分的合并",
        "object": "玻璃珠总数 = 3 × 7",
        "expr": "3 * 7",
        "config_role": "`visual={type:number-line, min:0, max:23, start:0, step:1}`。"
                       "**数轴只是摆设**：本题是「3 个袋子」的乘法，"
                       "一条数轴表达不了「3 份各 7」。"
                       "`max=23` 与答案 21 差 2，**不等于答案**，不构成答案副本；"
                       "但 `23 = 21 + 2` 这个关系也说明它不承载题意——"
                       "23 既不是题面里的数，也不是任何中间量",
        "boundary": "**这是本批一个明确的例外**：题面是乘法的等量组，"
                    "而 renderer 是单条数轴。孩子可以用数轴连跳 3 次 7 格"
                    "（0→7→14→21）表达，但**数轴不记录「3 个袋子」这个结构**，"
                    "所以即便答案对，也无法从 representation 判断"
                    "「孩子是按 3 份 7 个做的，还是直接跳到 21」的。"
                    "题面数学关系本身清楚（3×7=21），判为 MATCH；"
                    "但 renderer 与题意的匹配度不足，记为例外 EX-R1",
        "q05_hypothesis": "把 3 和 7 相加得 10（份数当量），或只跳到 7（单袋量）",
    },
    {
        "rvid": "240ff07b-3f7d-4420-97d3-e6ab89fd24dd",
        "renderer": "legacy:bar-model",
        "relation": "part_whole",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「一盒彩纸有13张，其中红色5张，其余是黄色」→ "
                  "13 是整体，5 是已知部分",
        "read": "「其余是黄色」把整体切成两块：已知 5、未知「其余」；"
                "所求是**未知部分**（不是整体）",
        "object": "黄色部分 = 整体 − 已知部分 = 13 − 5",
        "expr": "13 - 5",
        "config_role": "`visual.bars=[total(max=13,value=13), known(max=13,value=5), "
                       "unknown(max=13,unknown=true)]`、`max_value=15`。"
                       "**两根已知条的 `value` 与题面一致**（13 与 5），"
                       "`max=13` 是滑杆上限不等于答案 8，不构成答案副本",
        "boundary": "本题 `known_role` 是**已知整体**（13），与上一批 ten-frame "
                    "「已知部分」不同——整体与部分的角色不能混用。"
                    "注意 `total.max=13` 恰好等于整体 13：这在本题是**正确的**"
                    "（整体就是 13，滑杆要能摆到 13），不构成问题；"
                    "但如果某题把 `unknown.max` 设成答案，就是滑杆泄露——"
                    "本批已单独检出 5 条此类缺陷（见 KNOWN_DEFECTS.DEF-D1）。"
                    "**V1 legacy 的判分口径必须写明**：`legacy:bar-model` 走 "
                    "`ManipulativeRenderer` → `AnswerComposer`，"
                    "提交的是 `TaskResponse.answer`（数字框）**加上** "
                    "`representation`；但后端 `_judge` 只比 `content.answer`，"
                    "**不核 representation 结构**。"
                    "所以本题的真错法与假错法不能靠 structure 字段区分——"
                    "只能靠 `bars[].value` 这个表征快照，而它又不参与判分",
        "q05_hypothesis": "**按 V1 legacy 的实际判分口径重算**：V1 判分只比 "
                          "`TaskResponse.answer`（数字框），**不比 bars 结构**，"
                          "所以「13+5=18」不会被界面挡住（18 只是摆不上条，"
                          "但答案框可以填 18），会以 `MISMATCH` 呈现为错答。"
                          "真正的可观察痕迹只有 `bars[].value`（表征）"
                          "与 `answer`（判分）两处，**两者不联动**——"
                          "这是 V1 legacy 与 V2 的关键差别："
                          "V2 的 `evaluateBarModel` 会把结构错分到 "
                          "modeling/relation/calc，V1 **没有结构判分**",
    },
    {
        "rvid": "f5fb6594-862e-4dfe-9f19-723b1eed7ea6",
        "renderer": "legacy:bar-model",
        "relation": "part_whole",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「共有15本书，其中6本是故事书，其余是科普书」",
        "read": "与 240ff07b 同构（整体已知、求另一部分），只是场景与数值不同；"
                "所求是**科普书**这一部分",
        "object": "科普书 = 15 − 6",
        "expr": "15 - 6",
        "config_role": "`visual.bars=[total(value=15), known(value=6), unknown]、"
                       "visual.max_value=17`；`unknown.max=15` ≠ 答案 9，"
                       "**上限不构成泄露**；但 `bars` 只有三格（整体/已知/未知），"
                       "**无法承载「其余」这个措辞的语义**——"
                       "题意靠题面文字，不靠 visual",
        "boundary": "与 240ff07b、b1a30690、e6f17364 同模板（整体−部分）。"
                    "四条的差别只在数值与场景名词，**结构完全一样**——"
                    "所以这四条不能互相充当「换情境仍能做对」的证据，"
                    "那是 transfer 能力的问题，得由 app_transfer 的题来验。"
                    "本条 `ability_id=app_strat`，目标是「知道整体求另一部分」的策略选择",
        "q05_hypothesis": "把 15+6=21 当答案（方向反了）；或直接抄 6",
    },
    # ══ 比较差（difference）════════════════════════════════════════════════
    {
        "rvid": "eaa828b3-a633-4ab6-9cf5-8025a3687899",
        "renderer": "legacy:objects",
        "relation": "difference",
        "source_kind": "stem_plus_visual",
        "known_role": "已知部分",   # 两组的量都已知，差是导出的
        "source": "题面「小东有8支彩笔，小西有5支彩笔」→ 两个量都已知",
        "read": "所求是「多几支」= **差量本身**，不是任一方；"
                "8 与 5 都在题面里，差要自己算",
        "object": "两组之差 = 8 − 5",
        "expr": "8 - 5",
        "config_role": "`visual={type:objects, groups:[{count:8},{count:5}]}`。"
                       "**两组的 count 与题面完全一致**，是「题面已知量」的"
                       "忠实镜像——这恰好是上一批 object-counter 缺陷的反面："
                       "这里是 V1 legacy，物件**直接就摆好了**，"
                       "孩子只能拖对齐、不能减数，所以不存在「进入即满分」——"
                       "但这带来另一个限制，见 boundary",
        "boundary": "**这是本批第二个明确例外（EX-R2）**："
                    "`legacy:objects` 的两组 count 由 config 写死（8 和 5），"
                    "`tools=[drag,align,count,undo,reset]` **没有 add/remove**，"
                    "孩子只能「拖动/一一对齐」，**无法增减**，"
                    "所以 `ObjectCounterRepresentation.groups[].count` "
                    "永远是 8 与 5，唯一会变的是 `items[].x` 与 `aligned`。"
                    "「多出来的是哪 3 个」这个关键动作**没有留下痕迹**。"
                    "答案仍可从题面独立算出（8−5=3），题面数学清楚，判 MATCH；"
                    "但 Q05 侧「孩子是否用一一对应求差」不可观测，"
                    "已登记为 DEF-D3",
        "q05_hypothesis": "8+5=13（误把「多几」当「一共」）；或答 8（只报较大数）",
    },
    {
        "rvid": "7acb4a38-e51a-4c48-aa0b-4d0bce402f2e",
        "renderer": "legacy:objects",
        "relation": "difference",
        "source_kind": "stem_plus_visual",
        "known_role": "已知部分",
        "source": "题面「左边有6块积木，右边有4块积木」",
        "read": "布局提示了「左/右」两列，所求是「多几块」= 差量",
        "object": "两列之差 = 6 − 4",
        "expr": "6 - 4",
        "config_role": "`groups:[{count:6},{count:4}]` 与题面一致；同 eaa828b3 的"
                       "「只能对齐不能增减」限制",
        "boundary": "与 eaa828b3 同构（两组已知求差），数值不同、"
                    "`ability_id` 不同（本条 app_model，上条 app_rel）——"
                    "**能力标签不同不等于题意不同**，两条的数学结构一样。"
                    "这一点必须写明：同一批里 `ability_id` 分布不能反过来"
                    "当作「覆盖了不同能力」的证据。"
                    "与上一批 7acb4a38 无重号（上一批同号条目为 ruler/column 族，"
                    "本批按 RVID 全量比对已确认无交集，见 main() 的 overlap 检查）",
        "q05_hypothesis": "6+4=10（当合并）；或答 6",
    },
    {
        "rvid": "cfc971b4-002f-42c3-8b00-993784a4f9ff",
        "renderer": "legacy:objects",
        "relation": "difference",
        "source_kind": "stem_plus_visual",
        "known_role": "已知部分",
        "source": "题面「小红有8朵花，小蓝有5朵花」",
        "read": "两人各自的量已知，所求「多几朵」= 差量；"
                "本条 `ability_id=app_strat`，考点是**方法选择**（该用减法）",
        "object": "差 = 8 − 5",
        "expr": "8 - 5",
        "config_role": "`groups:[{count:8},{count:5}]`；只能对齐不可增减",
        "boundary": "**与 eaa828b3 的数值完全相同（8 与 5），只换了人和物品**。"
                    "这不是「换情境迁移」的合格证据——迁移要求结构与情境同时变，"
                    "这里结构没变。两条都做对只说明「8−5 会算」，"
                    "**不说明**孩子把「多几朵」和「多几支笔」识别为同一关系。"
                    "本条与 eaa828b3 的 `ability_id` 也不同（app_strat vs app_rel），"
                    "进一步说明能力标签不能替代题意判定",
        "q05_hypothesis": "8+5=13；或答 5（报较小数，把「多」读成「是」）",
    },
    {
        "rvid": "8f603745-fc26-4402-9cd2-0fc20cfd401a",
        "renderer": "legacy:objects",
        "relation": "difference",
        "source_kind": "stem_plus_visual",
        "known_role": "已知部分",
        "source": "题面「小海跑了9圈，小森跑了6圈」",
        "read": "两人圈数已知，所求「多跑几圈」= 差量；"
                "本条 `ability_id=app_transfer`，声称考「换到跑步情境仍能比较」",
        "object": "差 = 9 − 6",
        "expr": "9 - 6",
        "config_role": "`groups:[{count:9},{count:6}]`；只能对齐不可增减",
        "boundary": "**这是一条必须先说明的限制**：本条自称 transfer（迁移），"
                    "但它是 batch 内**第一次**出现「9 与 6 求差」的数值组合，"
                    "与 eaa828b3（8−5）、cfc971b4（8−5 同值不同人）、"
                    "7acb4a38（6−4）之间**没有同值配对**。"
                    "所以「换情境后仍能做对」这个迁移结论，"
                    "本批**给不出对照**——要证实迁移，必须找到"
                    "「同一数值结构、不同情境」的一对，本批凑不出来。"
                    "登记为：transfer 标签未获本批证据支持，不作否认也不作确认",
        "q05_hypothesis": "9+6=15；或答 9（只报较大数）",
    },
    # ── DEF-D2 三条（答案在界面上物理摆不出）——**必须进本批**，
    #    否则缺陷登记表引用批外 RVID，「已登记」就没有核对过现场 ──
    {
        "rvid": "421ede36-8f1b-4b10-9433-e92f039231bd",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「小青有11张贴纸，小雨比小青少4张。两个人一共有多少张贴纸」"
                  "→ 两步：先求小雨 = 11 − 4，再求两人合计",
        "read": "**两步题**：第一步求较小方（11−4=7），"
                "第二步把两人合起来（11+7=18）。"
                "所求是第二步的量，不是第一步的 7",
        "object": "两人合计 = 11 + (11 − 4) = 18",
        "expr": "11 + (11 - 4)",
        "config_role": "`bars=[base(max=15,value=11), unknown(max=15,unknown)]`、"
                       "`max_value=17`、`relationship=compare`。"
                       "⚠ **三处上限全都小于答案 18**（bars.max=15、max_value=17），"
                       "所以答案条**物理上摆不到 18**",
        "boundary": "⚠ **本题命中 DEF-D2（比 DEF-D1 更严重）**："
                    "题面是两个数量求差、再求总量，"
                    "但 `visual` 是按单条比较配置的（两根条：已知 + 未知），"
                    "**只有两根条的位置，没有第三根「合计」条**。"
                    "于是：① 该摆的 18 摆不出（max 15）；"
                    "② 即便能摆，两根条也表达不了「两人合计」。"
                    "这是**配置与题意结构性不匹配**，不是数值笔误。"
                    "数学结论成立（18），判 MATCH；"
                    "但本题的 representation 侧**必然全错**，"
                    "错误证据被污染（分不清「不会」与「摆不出」）",
        "q05_hypothesis": "答 7（只做完第一步）；或答 15（11+4，方向反）",
    },
    {
        "rvid": "6e5395f0-def7-4060-a501-044d8e9a3764",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「小明有9本故事书，小红比小明多3本。两个人一共有多少本」",
        "read": "两步：先求较大方（9+3=12），再求合计（9+12=21）",
        "object": "两人合计 = 9 + (9 + 3) = 21",
        "expr": "9 + (9 + 3)",
        "config_role": "`bars=[base(max=12,value=9), unknown(max=12,unknown)]`、"
                       "`max_value=14`。⚠ **上限 12 与 14 都远小于 21**"
                       "（12 恰好等于第一步的 12，14 = 12+2）",
        "boundary": "⚠ **命中 DEF-D2，且比 421ede36 更能说明问题**："
                    "`bars.max=12` 正好等于**中间结果**（小红 12 本）。"
                    "所以如果孩子只做第一步、把 12 当作最终答案，"
                    "滑杆**恰好能摆到**；而正确答案 21 摆不到。"
                    "**界面在奖励做一半**——这比单纯摆不出更糟。"
                    "题面数学清楚（21），判 MATCH；配置层判 NOT_READY",
        "q05_hypothesis": "答 12（只做第一步，且界面滑杆上限也是 12，会被强化）；"
                          "或答 6（9−3，方向反）",
    },
    {
        "rvid": "8981fbcc-5b92-44b6-ab89-6b8ef0e715fd",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「小兰有8颗糖，小杰比小兰多3颗。两个人一共有多少颗糖」",
        "read": "与 6e5395f0 同构（已知较小方 + 差，求合计），"
                "第一步 8+3=11、第二步 8+11=19",
        "object": "两人合计 = 8 + (8 + 3) = 19",
        "expr": "8 + (8 + 3)",
        "config_role": "`bars=[base(max=11,value=8), unknown(max=11,unknown)]`、"
                       "`max_value=13`。⚠ `bars.max=11` **恰好等于中间结果**"
                       "（小杰 11 颗），与 6e5395f0 是同一个毛病。"
                       "**`visual` 只留两格（已知/未知），没有「合计」格**——"
                       "题意要三根条，visual 只给两根，"
                       "所以它不是「已知量来源」，而是**容量不足的表征容器**",
        "boundary": "⚠ **命中 DEF-D2，且与 6e5395f0 同型**：`bars.max` 等于第一步结果，"
                    "答案 19 摆不出。三条 DEF-D2 的共同根因是"
                    "**`visual` 按「单条比较」配置，而题面是「两步求合计」**——"
                    "这两类题共用同一个 renderer 配置模板，"
                    "模板里的 `bars` 只留了「已知 / 未知」两格，"
                    "没有为「合计」留第三格。"
                    "所以不是三条各自配错了数，是**模板用错了题**",
        "q05_hypothesis": "答 11（只做第一步）；或答 5（8−3，方向反）",
    },
    {
        "rvid": "2dd5be20-77ea-400c-aa68-4702ecae705b",
        "renderer": "legacy:direct",
        "relation": "difference",
        "source_kind": "stem_only",
        "known_role": "已知整体",   # 13 = 整体（姐姐的量），差量 5 也已知
        "source": "题面「姐姐有13颗珠子，比弟弟多5颗。小明说『弟弟有18颗珠子』」"
                  "→ 13 是较大方、5 是差量、18 是被检验的断言",
        "read": "这是**判断题**：断言「弟弟有18颗」对不对。"
                "弟弟 = 13 − 5 = 8（较小方，已知较大方与差）≠ 18 → 断言错 → 答 0",
        "object": "判断值：1=断言正确，0=断言错误。本题应为 **0**",
        # 断言内容是「弟弟有 18 颗」，所以判 1 当且仅当 (13-5)==18；
        # 13-5=8 ≠ 18 → 0。上一版写成 `int((13-5) != 18)` 得 1，
        # 是把「不相等」直接当成了「断言正确」——方向正好相反，
        # 由本脚本首轮实跑 MISMATCH 检出（stated='0'），已改正。
        "expr": "int((13 - 5) == 18)",
        "config_role": "`kind=number`，`visual` 不存在（纯数字输入框）；"
                       "**没有任何配置参与**，题面是唯一信息源",
        "boundary": "**这是本批第三个必须写明的例外（EX-R3）**："
                    "答案 0 在「正确填1、错误填0」的约定下表示「断言错误」。"
                    "但 0 也可以被读成「弟弟有 0 颗」「数量是 0」，"
                    "**单看提交值分不开这两种读法**。"
                    "上一批 fea38e2d 的教训就是「值域看着怪 ≠ 算错」，这里同理，"
                    "只是方向相反：**值对 ≠ 理解对**。"
                    "判 MATCH 只表示「按题面的 1/0 约定算对了」，"
                    "不表示孩子把 0 当成了「错误」这个语义。"
                    "另：本题与 3ea61fc9（姐姐13、比弟弟多5、问弟弟几颗）"
                    "是**同一题面的两种问法**——一个问数、一个问对错。"
                    "这种配对是本批唯一可用于「同一关系不同表征」的对照",
        "q05_hypothesis": "答 1（直接采信断言 18，不去验算）；"
                          "或算出 18（把「比弟弟多5」做成 13+5）后再判 1",
    },
    # ══ 较大/较小量（larger_smaller）══════════════════════════════════════
    {
        "rvid": "3ea61fc9-850f-4b59-987d-1a58fe00087f",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",   # 13 是较大方（整条）
        "source": "题面「姐姐有13颗珠子，比弟弟多5颗」→ 已知**较大方**13、"
                  "差量 5；所求是**较小方**",
        "read": "「比弟弟多5」说的是姐姐相对弟弟的关系。已知较大求较小 → 减。"
                "这是本题的关键：语言里「多」出现，但运算要减",
        "object": "弟弟的量（较小方）= 13 − 5",
        "expr": "13 - 5",
        "config_role": "`bars=[base(max=18,value=13), unknown(max=18,unknown)]`、"
                       "`max_value=20`。`base.value=13` 与题面一致；"
                       "`unknown.max=18` ≠ 答案 8，**不泄露**",
        "boundary": "**与 2dd5be20 构成对照对**：同一题面（姐姐13、多5），"
                    "一个求数值（8）、一个求断言对错（0）。"
                    "这是本批唯一「同关系不同表征」的合格对照——"
                    "两条都做对，才能说孩子既会算 8、又知道 18 是错的。"
                    "只做对一条时，不能推出另一条也会。"
                    "注意 `bars` 里**没有第三根「差条」**：本题的 understood 结构是"
                    "「大条−小条=差」，但 UI 只给两根条（已知+未知），"
                    "差 5 只在题面里、不在条上——孩子要自己在脑中补第三根条。"
                    "这是 renderer 表达力不足，不是题错",
        "q05_hypothesis": "13+5=18（「多」直接做加法）；或答 5（把差量当答案）",
    },
    {
        "rvid": "7f22076d-e47d-46e4-a822-0528a90a451a",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「小安的棋子比小林少6颗。小林有14颗棋子」→ 已知较大方 14、"
                  "差量 6；所求是较小方",
        "read": "**语言顺序与角色相反**：「比…少」的主语（小安）是较小的那一方，"
                "但句子把主语放前面、把已知的较大方放后面。"
                "孩子要先分清「谁比谁少」，再选减法",
        "object": "小安的量（较小方）= 14 − 6",
        "expr": "14 - 6",
        "config_role": "`bars=[base(max=20,value=14), unknown(max=20,unknown)]`、"
                       "`max_value=22`；`unknown.max=20` ≠ 8，不泄露",
        "boundary": "与 3ea61fc9 的**关键差别是语序**：3ea61fc9 是"
                    "「[已知者]比[未知者]多」（已知者在前）；"
                    "本条是「[未知者]比[已知者]少」（未知者在前）。"
                    "**这是本批唯一一对「同运算、不同语序」的题**，"
                    "也是最有价值的对照：孩子若只会一种语序，"
                    "两条会出现一错一对的分离。"
                    "但注意——配对的是「语序」，不是「数值」，"
                    "所以它检验的是语言解析，不是计算",
        "q05_hypothesis": "14+6=20（把「少」读成「多」）；或答 14（忽略差量）",
    },
    {
        "rvid": "8612589b-80dd-4ac7-8658-c241b8d45153",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「哥哥有12个贝壳，比妹妹多5个」",
        "read": "与 3ea61fc9 **同语序同结构**（已知者在前、比未知者多），"
                "数值不同（12/5 vs 13/5）",
        "object": "妹妹的量 = 12 − 5",
        "expr": "12 - 5",
        "config_role": "`bars=[base(max=17,value=12), unknown(max=17,unknown)]`、"
                       "`max_value=19`；`unknown.max=17` ≠ 7，不泄露。"
                       "**`bars` 只有两格（已知/未知），差量 5 不在条上**——"
                       "「比…多5」这个关系没有被 visual 承载，"
                       "孩子要自己在脑中补第三根条",
        "boundary": "本条 `ability_id=app_strat`（策略选择），3ea61fc9 是 app_rel"
                    "（关系理解）——**标签不同但题目结构完全相同**。"
                    "两条一起做对只说明「12−5 与 13−5 都会算」，"
                    "不能说「既掌握了关系又掌握了策略」："
                    "那是把同一份能力证据记了两遍。"
                    "本批明确声明：**能力标签的差异不在本批证据范围内**",
        "q05_hypothesis": "12+5=17（方向反）；或答 12",
    },
    {
        "rvid": "ed97b114-6599-4cd3-ad0e-ca1c3509ed57",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「小芸比小康少5颗星星。小康有14颗星星」",
        "read": "与 7f22076d **同语序**（未知者在前、比已知者少），"
                "差量同为 5、已知量同为 14 → 数值也相同",
        "object": "小芸的量 = 14 − 5",
        "expr": "14 - 5",
        "config_role": "`bars=[base(max=19,value=14), unknown(max=19,unknown)]`、"
                       "`max_value=21`；`unknown.max=19` ≠ 9，不泄露",
        "boundary": "**与 7f22076d 完全同值同语序（14−6 vs 14−5 差一个数）**——"
                    "两条是「差量 6」与「差量 5」的最小对。"
                    "严格说这不是重复题（差量不同），但也**不是有意义的对照**："
                    "差值差 1 不能区分「会算」与「理解」。"
                    "本条真正可说的是：与 7f22076d 一起，"
                    "两条都做对至少排除了「14−6 恰好蒙对」这一种偶然",
        "q05_hypothesis": "14+5=19（方向反）；或答 5",
    },
    {
        "rvid": "c07482bb-8a60-4b18-b3c1-25532a77a339",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "答案副本",   # ← 关键：bars[].max == answer
        "source": "题面「小杰有7张卡片，小宁比小杰多4张」→ 已知较小方 7、差量 4；"
                  "所求是较大方",
        "read": "已知较小方与差量求较大方 → 加。"
                "**注意「多」在这里要加**，与 3ea61fc9 的「多要减」相反——"
                "差别在于「谁是已知方」：已知较小方时「多」是加到未知方上",
        "object": "小宁的量（较大方）= 7 + 4",
        "expr": "7 + 4",
        "config_role": "⚠ **`bars=[base(max=11,value=7), unknown(max=11,unknown)]`——"
                       "两根条的滑杆上限 11 **恰好等于答案 11**。"
                       "这不是旁证，是**答案副本**：孩子把未知条拖到最右端就得到正确答案，"
                       "不需要知道 7+4。",
        "boundary": "⚠ **本题按题意推导 MATCH，但配置层有缺陷（DEF-D1）**："
                    "`unknown.max`（以及 `base.max`）== 答案 11。"
                    "滑杆的上限由 config 给定、在界面上**可见**（拖到底是 11），"
                    "所以「把条拖满」这个动作等价于「拿到答案」。"
                    "对比 V2 bar-model：`parseBarModelConfig` 有"
                    "「`maxBlocks >= solved + 1`」守卫，V1 legacy **没有这层守卫**。"
                    "结论：**数学结论成立，UI 泄露答案**。"
                    "`known_role` 标为「答案副本」正是为此——"
                    "本题的配置**不能**作为任何独立依据，"
                    "甚至要把它当作一个不利证据",
        "q05_hypothesis": "拖到最右得 11（正确但无推导过程，不可观测）；"
                          "或 7−4=3（方向反）",
    },
    # ── DEF-D1 其余四条（同族：已知较小方 + 差，求较大方；bars.max == 答案）──
    # 门禁 T5 检出这四条曾在 affected 里却不在批内，已补入。
    {
        "rvid": "8b121389-2d87-4ea2-aef1-0a626e5464de",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "答案副本",
        "source": "题面「小雨有6本书，小安比小雨多4本」→ 已知较小方 6、差量 4；"
                  "所求是较大方",
        "read": "已知较小方与差量求较大方 → 加（6+4）。"
                "与 c07482bb 同结构，数值不同",
        "object": "小安的书数（较大方）= 6 + 4",
        "expr": "6 + 4",
        "config_role": "⚠ `visual.bars=[base(max=10,value=6), unknown(max=10,unknown)]`、"
                       "`max_value=12`。**bars.max=10 恰好等于答案 10**，"
                       "max_value=12 = 10+2 —— 两条上限都不构成「留出正确余量」",
        "boundary": "⚠ **命中 DEF-D1（滑杆上限 == 答案）**：把未知条拖到最右端"
                    "就得到 10，与算出 6+4 在表征上不可区分。"
                    "与 c07482bb、c88410f2、e5c13ef5、04f97cb8 同属一族"
                    "（已知较小方+差求较大方）。"
                    "**本族 5 条的 `bars.max` 全部等于答案，不是偶发配错**——"
                    "这是该模板的默认行为：上限按「答案 + 0」而非「答案 + 余量」生成。"
                    "数学结论成立（10），判 MATCH",
        "q05_hypothesis": "拖到底得 10（正确但无过程）；或 6−4=2（方向反）",
    },
    {
        "rvid": "c88410f2-f810-47b4-8ae4-cc218b140a88",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "答案副本",
        "source": "题面「小雨今天走了9千步，小安比小雨多走4千步」→ "
                  "已知较小方 9、差量 4；所求是较大方",
        "read": "同 8b121389 结构（已知较小方+差求较大方），"
                "本条唯一不同是**单位是「千步」**——"
                "数字 9 与 4 的语义是「9 千步」「4 千步」，"
                "不是 9 与 4 个步。所求 13 的单位也应是千步",
        "object": "小安的步数（较大方，单位千步）= 9 + 4",
        "expr": "9 + 4",
        "config_role": "⚠ `bars=[base(max=13,value=9), unknown(max=13,unknown)]`、"
                       "`max_value=15`。**bars.max=13 == 答案 13**（DEF-D1）",
        "boundary": "⚠ **命中 DEF-D1（滑杆上限 == 答案）**，与同族五条一致。"
                    "本条额外值得记的是**单位问题**：`visual` 里没有任何字段"
                    "表达「千步」这个单位，滑杆只标 0..13，"
                    "所以孩子在界面上看到的 13 与题面的「13 千步」"
                    "在表征层没有连接。这不是错误（答案数值对），"
                    "但属于**单位语义在 renderer 层丢失**，"
                    "登记为观察项，不计入缺陷（因为没有可对照的正确做法）",
        "q05_hypothesis": "拖到底得 13；或 9−4=5（方向反）",
    },
    {
        "rvid": "e5c13ef5-daa1-46c4-a545-a40f38ba1e79",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "答案副本",
        "source": "题面「小李有7本故事书，小美比小李多4本」→ 已知较小方 7、差量 4",
        "read": "同族结构（已知较小方+差求较大方）→ 7+4",
        "object": "小美的书数 = 7 + 4",
        "expr": "7 + 4",
        "config_role": "⚠ `bars=[base(max=11,value=7), unknown(max=11,unknown)]`、"
                       "`max_value=13`。**bars.max=11 == 答案 11**（DEF-D1）。"
                       "`visual` 只有两根条（已知 7 / 未知），"
                       "**不记录「比…多 4」这个差量关系**——"
                       "差 4 只在题面里，条上无处表达，"
                       "所以 visual 的角色是「两个数的容器」，"
                       "**不是「关系模型」**",
        "boundary": "⚠ **命中 DEF-D1：bars.max = 11 = 答案**，拖到底即满分。"
                    "另：**与 c07482bb 的数值完全相同（7 与 4）、答案也相同（11）**，"
                    "只换了人和物品名。两条的 `visual` 逐字段一致。"
                    "这意味着：**两条的 Q05 证据不可区分**，"
                    "不能当成两份独立证据；且两条都受 DEF-D1 影响，"
                    "「拖到底」在两条上都会得到满分。"
                    "这是本批第二次出现「同值同结构只换名词」的重复对"
                    "（第一次是 eaa828b3/cfc971b4）",
        "q05_hypothesis": "拖到底得 11；或 7−4=3（方向反）",
    },
    {
        "rvid": "04f97cb8-b918-4836-bf06-c39d8613fe0e",
        "renderer": "legacy:bar-model",
        "relation": "larger_smaller",
        "source_kind": "stem_plus_visual",
        "known_role": "答案副本",
        "source": "题面「小冬有7张卡片，小冬比小夏少4张」→ 已知较小方 7、差量 4；"
                  "所求是较大方（小夏）",
        "read": "**语序与 c07482bb 相反**：c07482bb 是「甲比乙多」，"
                "本条是「甲比乙少」。但**所求都在同一侧**——"
                "c07482bb 求「比小杰多」的偏大者，本条求「小冬比之少」的偏大者。"
                "所以两条虽然措辞相反，**运算与角色相同**（都是 7+4=11），"
                "这是本批一对**「措辞相反但语义同侧」**的对照",
        "object": "小夏的卡片数（较大方）= 7 + 4",
        "expr": "7 + 4",
        "config_role": "⚠ `bars=[base(max=11,value=7), unknown(max=11,unknown)]`、"
                       "`max_value=13`。**bars.max=11 == 答案 11**（DEF-D1）。"
                       "**本题的 visual 与 c07482bb 逐字段相同**——"
                       "两条的「比…少 / 比…多」全靠题面文字区分，"
                       "visual 里没有任何字段表达关系方向，"
                       "所以它无法承载语序对照，只能承载两个数",
        "boundary": "⚠ **命中 DEF-D1（bars.max = 11 = 答案，拖到底即满分）**；"
                    "本条的价值在语序对照："
                    "与 c07482bb（7+4，措辞「比…多」）相比，"
                    "本条（7+4，措辞「比…少」）**数值与答案完全相同**，"
                    "但孩子需要理解「小冬比小夏少」意味着「小夏更多」。"
                    "两条都做对，才说明「多/少」的**指向**被理解，"
                    "而不只是「看到多就加」。"
                    "**但两条都受 DEF-D1 影响**——拖到底都得 11，"
                    "所以这个对照**在现有 UI 下失效**：即使孩子不理解语序，"
                    "拖到底也能两条全对。这是 DEF-D1 对教学诊断的实质损害",
        "q05_hypothesis": "拖到底得 11；或 7−4=3（把「少」直接做减法）",
    },
    # ══ 连续变化（continuous）══════════════════════════════════════════════
    {
        "rvid": "76d49907-c092-4822-b0ea-344850970da0",
        "renderer": "legacy:number-line",
        "relation": "continuous",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",   # 起点量
        "source": "题面「原来有8辆车，又开来5辆，后来开走4辆」→ 起点 8，"
                  "两次变化 +5、−4",
        "read": "**同一对象的两次先后变化**，所求是变化后的状态。"
                "顺序要紧：先 +5 再 −4，不能合并成 −4 再 +5 吗？"
                "数值上可交换（8+5−4 = 8−4+5），"
                "但题面语义顺序是「先来后走」，中间状态 13 有实际意义",
        "object": "最终车辆数 = 8 + 5 − 4",
        "expr": "8 + 5 - 4",
        "config_role": "`visual={type:number-line, min:0, max:14, start:8, step:1}`。"
                       "**`start=8` 与题面起点一致**，这是数轴唯一承载的题意；"
                       "`max=14` ≥ 中间态 13，允许跳到 13 再退回 9，"
                       "**不构成答案副本**（9 ≠ 14）",
        "boundary": "数轴能表达两次跳步（+5、−4），**这是本批 renderer 与题意"
                    "匹配得最好的一条**。但要注意：`visual` 里**没有记录**"
                    "「跳了几次、每次几格」的期望值，"
                    "所以 representation 只能证明「跳到了 9」，"
                    "不能证明「跳了 +5 再 −4」——"
                    "跳到 9 也可能是一次 +1（从 8 到 9）。"
                    "这一点使 Q05 侧仍不可观测，见 KNOWN_DEFECTS",
        "q05_hypothesis": "8+5=13 忘记减 4；或 8+5+4=17（把「开走」当加）",
    },
    {
        "rvid": "bb376fbd-06c8-4604-91c9-4cc195567a49",
        "renderer": "legacy:number-line",
        "relation": "continuous",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「原来有9个人，第一站上来6人，第二站下去4人」",
        "read": "两次变化（+6、−4），所求是变化后的状态；"
                "**两站在题面里是有序的**，中间态 15 可被孩子先算出来",
        "object": "最终人数 = 9 + 6 − 4",
        "expr": "9 + 6 - 4",
        "config_role": "`visual={min:0, max:16, start:9}`、`ui_revision=v1.1`。"
                       "`start=9` 与题面一致；`max=16` ≥ 中间态 15、"
                       "且 ≠ 答案 11，**不泄露**",
        "boundary": "与 76d49907、552b39e3 同一结构（起点 + 两次变化）。"
                    "三条的差别是数值与场景，**结构不变**。"
                    "三条一起做对，能说明「这套两次变化的算法稳定」，"
                    "但**不能**说明「换了场景仍能识别出这是两次变化」——"
                    "后者的前提是场景变了而题面措辞也变了，"
                    "本批三条的措辞几乎一样（都是「原来有…，又…，后来…」），"
                    "连措辞都没换。这是本批一个诚实的限制",
        "q05_hypothesis": "9+6+4=19（「下去」当加）；或 9+6=15（漏第二步）",
    },
    {
        "rvid": "552b39e3-7127-4c2d-a506-628259bb08c7",
        "renderer": "legacy:number-line",
        "relation": "continuous",
        "source_kind": "stem_plus_visual",
        "known_role": "已知整体",
        "source": "题面「原来有8本新书，老师又放上5本，后来同学借走4本」",
        "read": "与 76d49907 **数值完全相同**（8、+5、−4），只换了场景名词"
                "（车辆→书）与措辞（开来/开走 → 放上/借走）",
        "object": "最终本数 = 8 + 5 − 4",
        "expr": "8 + 5 - 4",
        "config_role": "`visual={min:0, max:14, start:8}`——**与 76d49907 的 "
                       "visual 逐字段相同**（本批唯一一对完全同配置的题）。"
                       "`start=8` 与题面起点一致；`max=14` 允许先跳到中间态 13 "
                       "再退回 9。**`visual` 不记录跳步序列**，"
                       "只给起点与量程——跳了几次、每次几格，"
                       "由 `NumberLineRepresentation.jumps` 在运行时记录，"
                       "但**判分不看 jumps**",
        "boundary": "**本条 `ability_id=app_transfer`，而且它是本批唯一"
                    "「同值同结构、只换场景」的配对**（配 76d49907）。"
                    "这一点比 8f603745 强：8f603745 找不到配对，"
                    "而本条与 76d49907 构成合格的「换情境」对照。"
                    "但**仍不足**以证明迁移：两条的措辞结构相同"
                    "（都是「原来…，又…，后来…」），只是名词换了。"
                    "真正的迁移要措辞也变（例如「先放入5本，后取出4本，"
                    "原来书架另有8本」），本批没有这样的题。"
                    "登记为：transfer 有**弱对照**，不能升级为「迁移已验证」",
        "q05_hypothesis": "8+5=13；或 8+5+4=17",
    },
    # ══ 条件筛选（conditional）════════════════════════════════════════════
    {
        "rvid": "3706473c-8f57-45a5-b01a-d6470d826321",
        "renderer": "legacy:direct",
        "relation": "conditional",
        "source_kind": "stem_only",
        "known_role": "已知部分",
        "source": "题面「6个苹果、2个梨，还有4支铅笔。苹果和梨一共有多少个」",
        "read": "**三个量、两类物品**。「铅笔」与问题无关，必须排除。"
                "所求只在苹果与梨之间合并",
        "object": "苹果 + 梨 = 6 + 2（**不含 4**）",
        "expr": "6 + 2",
        "config_role": "`kind=number`，纯数字输入框，`visual` 不存在；"
                       "题面是唯一信息源",
        "boundary": "**本批最干净的条件筛选题**：无关项是一个**不同类别的物品**"
                    "（铅笔不属于水果），类别边界清楚。"
                    "对比 6857ba8d（橘子/苹果）与 623b7f19（贴纸/练习册），"
                    "三条的无关项都是「不同类别」，"
                    "**没有一条是「同类别但用不上」**（例如「3 个红苹果、"
                    "2 个绿苹果，问红苹果和梨一共几个」这种）。"
                    "那才是更难的条件筛选。登记为覆盖不足，扩样时补",
        "q05_hypothesis": "6+2+4=12（把铅笔也算上，未做条件筛选）",
    },
    {
        "rvid": "6857ba8d-9130-4da3-97ad-267e06e87e97",
        "renderer": "legacy:direct",
        "relation": "conditional",
        "source_kind": "stem_only",
        "known_role": "已知整体",
        "source": "题面「篮子里原来有12个橘子，吃掉4个，又放进3个苹果。"
                  "还剩多少个橘子」",
        "read": "**两个陷阱叠在一起**：①「又放进3个」是**苹果**不是橘子，不计入；"
                "②所问限定为「橘子」。所以只做 12−4",
        "object": "橘子剩余 = 12 − 4（**不含 +3**）",
        "expr": "12 - 4",
        "config_role": "`kind=number`，无 visual；题面唯一信息源",
        "boundary": "**本条的条件筛选比 3706473c 难一层**：3706473c 的无关项"
                    "在问题之外（问水果、铅笔在旁边），"
                    "本条的无关项**混在操作序列里**（「又放进3个苹果」是夹在"
                    "「吃掉4个」和「还剩」之间的一次动作）。"
                    "孩子要同时做两件事：识别「放进的不是橘子」、"
                    "识别「所问是橘子」。这两件事在题面里**没有分开写**。"
                    "这是本批条件筛选类里**唯一带动作干扰**的题，"
                    "价值高于 3706473c / 623b7f19 / af2cb0d1",
        "q05_hypothesis": "12−4+3=11（把苹果算进橘子）；或 12+3−4 但答橘子（同值巧合，"
                          "需注意 11 也可能来自这个错序——两种错法同值，不可分）",
    },
    {
        "rvid": "76ce803c-cdf8-46c1-85f7-d5207bdca060",
        "renderer": "legacy:direct",
        "relation": "conditional",
        "source_kind": "stem_only",
        "known_role": "已知整体",
        "source": "题面「盒子里有10颗糖，又放进5颗，后来吃掉3颗。"
                  "旁边还有4块饼干。现在盒子里有多少颗糖」",
        "read": "**连续变化 + 条件筛选叠加**：两次变化（+5、−3）都是糖，"
                "「4块饼干」是无关项。所求是变化后的糖数",
        "object": "糖数 = 10 + 5 − 3（**不含 4**）",
        "expr": "10 + 5 - 3",
        "config_role": "`kind=number`，无 visual",
        "boundary": "**本条同时属于「连续变化」与「条件筛选」两类**。"
                    "本批按 `relation` 单一归类为 conditional，"
                    "因为它的难点在排除饼干（4 与答案 12 差得远，"
                    "排除后 10+5−3=12；若不排除则会算成 16 或 12+4）。"
                    "**必须注明这种单选归类是简化**："
                    "把复合题塞进单一类别，会低估它的难度。"
                    "五类关系的题数分布因此不能当成「难度分布」看",
        "q05_hypothesis": "10+5−3+4=16（把饼干算进糖）；或 10+5=15（漏掉吃掉）",
    },
    {
        "rvid": "623b7f19-47ba-467f-bad7-2b87bc4a5401",
        "renderer": "legacy:direct",
        "relation": "conditional",
        "source_kind": "stem_only",
        "known_role": "已知整体",
        "source": "题面「小芳有9张贴纸，送给小美3张。她的书包里还有2本练习册。"
                  "小芳还剩几张贴纸」",
        "read": "无关项「2本练习册」出现在**动作句之后**，且与贴纸无关；"
                "所求是送完后的贴纸数",
        "object": "剩余贴纸 = 9 − 3",
        "expr": "9 - 3",
        "config_role": "`kind=number`，无 visual",
        "boundary": "与 3706473c **同构**（无关项是另一个类别的物品、"
                    "紧跟在相关句后面）。两条的差别只在位置："
                    "3706473c 的无关项在问句前、本题在动作句后。"
                    "这个差别**太细**，不足以构成独立的难度层。"
                    "诚实地说：本批 conditional 类 4 条里，"
                    "3706473c 与 623b7f19 实质是同一难度；"
                    "6857ba8d（动作干扰）与 76ce803c（复合）才是真正的增量",
        "q05_hypothesis": "9−3+2=8（把练习册当贴纸）；或 9−3−2=4",
    },
]

# ── KNOWN_DEFECTS：本批核验中登记的「交互／配置风险条目」（**不改组件，只登记**）──
# 2026-10-21 复审要求：15 条先称为「已登记的交互／配置风险条目」，分别标出
# 静态事实、推断、待运行验证，**不直接作为 15 条已确认产品故障**。
# 因此每条都带 `evidence_tier`：
#   static_fact  → 只读仓库/配置即可确认的数值或字段事实
#   inference    → 由静态事实推出、但需要额外前提的风险
#   needs_runtime→ 必须真实操作/提交才能判定
# 以及 `confirmed`（本批是否已确证为产品故障）与 `not_claimed`（明确不主张什么）。
KNOWN_DEFECTS: dict[str, dict] = {
    "DEF-D1": {
        "title": "legacy:bar-model 滑杆上限等于答案（配置事实）",
        "kind": "ui_answer_leak",
        "evidence_tier": "static_fact → inference",
        "confirmed": False,
        "evidence": "`ui_schema.visual.bars[].max` == `content.answer`（5 题逐一核对）；"
                    "V1 legacy 渲染路径无 `maxBlocks >= solved+1` 守卫"
                    "（对比 `barModelV2.ts::parseBarModelConfig` 有该守卫）",
        "static_fact": ("5 题的 `bars[].max` 与 `content.answer` 数值相等；"
                        "`BarModel.tsx` 滑杆 `max={Math.max(min + 1, barMax)}`，"
                        "所以最右端恰好是答案值。"),
        "inference": ("未知条拖到最右端时，表征里的 `unknown.value` 等于答案。"
                      "**但这是否构成「直接得分」，取决于提交与判分契约**，"
                      "不是静态配置能单独决定的。"),
        "not_claimed": ("**不主张「只拖到底即满分」**。V1 仍有独立的数字答案输入框"
                        "（`TaskRenderer.tsx::ManipulativeRenderer` 同时渲染 "
                        "`AnswerComposer`），判分读的是 `response.answer`"
                        "（`learning.py` 中 `content.answer` 与 `response.answer` 比较），"
                        "`representation` 不参与判分。因此更准确的说法是："
                        "**表征层的答案泄露风险**，而不是「分数白送」。"),
        "impact": ("存在**目标值提示风险**：滑杆最右端即答案，孩子可以不推理就把"
                   "未知条摆到正确长度；因此 `representation` 作为「是否理解比较关系」"
                   "的证据时区分力弱。**这不等于判分必然出错**，"
                   "但确实使过程证据的可信度下降。"),
        "needs_runtime": ("真实提交一次「未知条拖到底 + 数字答案填错」的组合，"
                          "观察判分是否仍为 `correct=false`；"
                          "本批**未做**该实验，故 `confirmed=false`。"),
        "affected": ["c07482bb", "8b121389", "c88410f2", "e5c13ef5", "04f97cb8"],
        # 差额可追溯性：这 4 条是门禁 T5 检出「affected 引用批外 RVID」后补入的，
        # 源码里留有对应分组注释（见 CHECKS 内 "DEF-D1 其余四条"）。
        "added_after_gate": ["8b121389", "c88410f2", "e5c13ef5", "04f97cb8"],
        "status": "已登记风险；本轮不改组件（只读范围），待内容侧评估 max 与提示设计",
    },
    "DEF-D2": {
        "title": "legacy:bar-model 最终合计大于单条上限（线索，非可完成性判定）",
        "kind": "unreachable_signal",
        "evidence_tier": "needs_runtime",
        "confirmed": False,
        # ★★ 本条目是 2026-10-21 复审撤回重写的地方，改动原因写在此处备查：
        #    上一版把它定性为「答案在界面上无法摆出」「界面在系统性奖励半成品」，
        #    前提是「未知条必须表示最终合计」。该前提**未经核验**：
        #    三题都是「先求另一个人的数量、再求两人合计」的两步题，
        #    未知条完全可以表示**另一个人的数量**，而不是最后的合计。
        "evidence": "`content.answer` > 所有 `bars[].max`（3 题逐一核对）",
        "static_fact": ("三题的最终合计（18 / 21 / 19）都大于任一单条上限；"
                        "三题的**个人数量**却都在范围内（见下表）。"),
        "inference": ("**没有**。当前检测器 `detect_unreachable()` 只比较"
                      "「最终答案 > 所有上限」，它不读「哪根条代表哪个量」，"
                      "也不知道题目是否要求单独展示合计。"
                      "所以它给出的是线索，不是可完成性结论。"),
        "detector_limits": (
            "`detect_unreachable()` 是**线索检测器**，不是任务可完成性判定器。"
            "两个具体缺陷：① 不读条的角色语义，无法区分「未知条 = 合计」"
            "与「未知条 = 另一个人的数量」；② 取 `max(所有上限)` 而非"
            "「答案条的上限」，因此会漏报——"
            "反例：答案条上限 5、另一无关条上限 100、答案 10，"
            "该函数取最大值 100 后判定「可达」，实际答案条摆不出 10。"),
        "not_claimed": ("**不主张「永远拿不到分」**，也**不主张「界面在系统性奖励"
                        "半成品」**。上一版这两句与同一份报告里「只能靠数字输入框"
                        "答对」互相矛盾——两者不能作为同一已证结论并存。"
                        "而且判分读 `response.answer`，与滑杆能否摆出无关。"),
        "role_hypothesis": [
            {"rvid": "421ede36", "person_a": 11, "person_b": 7,
             "answer": 18, "bar_caps": [15, 15], "max_value": 17,
             "bars_can_show": "11 与 7（两人各自的数量）",
             "both_within_range": True},
            {"rvid": "6e5395f0", "person_a": 9, "person_b": 12,
             "answer": 21, "bar_caps": [12, 12], "max_value": 14,
             "bars_can_show": "9 与 12（两人各自的数量）",
             "both_within_range": True},
            {"rvid": "8981fbcc", "person_a": 8, "person_b": 11,
             "answer": 19, "bar_caps": [11, 11], "max_value": 13,
             "bars_can_show": "8 与 11（两人各自的数量）",
             "both_within_range": True},
        ],
        "verification_plan": [
            "① 表征对象：确认未知条在本题型里被要求表示「另一个人的数量」"
            "还是「两人合计」——查内容侧任务契约与 `relationship` 语义",
            "② 正确候选：分别用 11/7、9/12、8/11 摆条并提交，应判对（若契约要求"
            "表征提交的是两人各自数量）；随后在数字框提交 18/21/19",
            "③ 半成品负例：分别用 7/12/11 提交，应判错——否则才是「奖励半成品」",
            "④ 提交关联：确认 `representation` 与 `response.answer` 在判分里"
            "各承担什么，是否要求一致",
        ],
        "impact": ("在①②未完成前，**只能说「单条上限不足以表示最终合计」这一"
                   "静态事实**。若核验证明未知条只需表示个人数量，则本条目应降级为"
                   "「条形角色标签不清楚」的可用性问题，而不是可达性缺陷。"),
        "if_confirmed": ("若契约确实要求未知条为合计、或提交被真实阻断，"
                         "再走内容侧新版本整改；且**不能只把 `max` 改成比答案大"
                         "就算修好**——那会同时制造新的答案泄露。"),
        "math_answers_unaffected": "18 / 21 / 19 三个数学答案本身无需修改。",
        "affected": ["421ede36", "6e5395f0", "8981fbcc"],
        "added_after_gate": ["421ede36", "6e5395f0", "8981fbcc"],
        "status": "**已登记线索，待定向核验**；不按当前检测器结论改 Published 配置",
    },
    "DEF-D3": {
        "title": "legacy:objects 未提供增减操作（静态事实）",
        "kind": "interaction_gap",
        "evidence_tier": "static_fact → inference",
        "confirmed": False,
        "evidence": "`visual.groups[].count` 由 config 写死；"
                    "`tools` 无 `remove_object`/`add_object`",
        "static_fact": ("4 题的 `groups[].count` 来自配置，界面上没有增删物件的"
                        "工具项。"),
        "inference": ("「先摆到一样多、再看多出几个」这个动作**不能通过增删完成**。"),
        "not_claimed": ("**不主张「求差动作完全不可观测」**，也**不主张「不能一一对应」**。"
                        "仍需查三件事：① 物件位置是否记录（`items[].x/y`）；"
                        "② 对齐动作是否记录（`aligned` 字段）；"
                        "③ 序列化是否保留了两组的相对排布。"
                        "「没有增删」只否掉了其中一条路径，不等于否掉全部过程信息。"),
        "impact": ("一一对应与「多出几个」的过程证据，**不能来自物件数量的变化**；"
                   "是否可从对齐/位置/其它工具动作中读出，本批**未逐项核验**。"),
        "needs_runtime": ("以 `[对齐]` 操作驱动一次真实提交，检查序列化里"
                          "`aligned` 与 `items[].x` 是否变化；本批**未做**。"),
        "affected": ["eaa828b3", "7acb4a38", "cfc971b4", "8f603745"],
        "status": "已登记风险；与上一批 object-counter「进入即 PASS」不是同类问题，"
                  "不宜并列成「两个相反的缺陷」",
    },
    "DEF-D4": {
        "title": "legacy:number-line 未声明期望跳步序列（有字段、无口径）",
        "kind": "interaction_gap",
        "evidence_tier": "static_fact",
        "confirmed": False,
        "evidence": "`NumberLineRepresentation` **有** `jumps: number[]` 字段；"
                    "`visual` 侧只给 `min/max/start`，**没有期望跳步序列**",
        "static_fact": ("`jumps` 字段真实存在且会被序列化；"
                        "`visual` 里没有「期望怎么跳」的声明。"),
        "not_claimed": ("**不主张「不记录跳步」**——上一版这个标题是错的，"
                        "因为 `jumps` 字段明确存在。准确的表述是"
                        "「**没有声明期望跳步序列**」，属于「有字段无口径」。"),
        "four_things_separated": {
            "能否操作": "可以（数轴上可连续跳步）",
            "有没有记录": "**有**（`jumps` 数组；`[7,7,7]` 与 `[21]` 是不同的记录）",
            "有没有校验": "**没有**（判分只比 `answer`，不比 `jumps`）",
            "有没有进入能力证据": "**没有**（`jumps` 不参与判分与能力证据）",
        },
        "inference": ("因为「没有校验」，所以「跳到 9」可来自不同跳法而判分相同；"
                      "但这**不等于**过程信息不存在——它存在但未被使用。"),
        "impact": ("连续变化类的**过程证据未被判分使用**；"
                   "若要让跳步进入能力证据，需要先补「期望跳步序列」的口径，"
                   "而不是改记录结构。"),
        "affected": ["76d49907", "bb376fbd", "552b39e3"],
        "status": "已登记风险；`jumps` 字段存在但未被判分使用，"
                  "与上一批 ruler 的 `structure.error`（有精确靶）不同",
    },
}

# ── Q05 逐题可观察证据（三字段，按 renderer 真实序列化字段写）──────────────
# 字段出处（均在仓库核实过）：
#   bar-model(V2)     → serializeBarModelV2: {bars, answer_bar, answer, structure{status,error,relation}}
#   legacy bar-model  → WorkspaceRepresentation(BarModelRepresentation):
#                       {type, relationship, bars[{id,label,value,unknown}]}
#   legacy object-counter → ObjectCounterRepresentation:
#                       {type, groups[{id,label,count,items[]}], aligned}
#   legacy number-line    → NumberLineRepresentation:
#                       {type, min, max, step, start, current, jumps[]}
#   legacy direct(number) → TaskResponse.answer（纯字符串），无 representation
Q05_EVIDENCE: dict[str, dict] = {
    # ── bar-model V2（有 structure.error 三分类，证据最细）──
    "73dd367b": {
        "observable": {
            "modeling": "`bars.a` 或 `bars.b` ≠ config.known 的 5/7，"
                        "且 `answerTouched=true`。`structure={status:FAIL, "
                        "error:'modeling', relation:'part_whole'}`。"
                        "**痕迹在 a/b 两根已知条上**，不在答案条",
            "calc": "`bars.a=5`、`bars.b=7`（已知条摆对），"
                    "但 `bars.c` ≠ 12。`structure.error='calc'`。"
                    "**结构对、结果错**",
            "relation": "`bars.c` ≤ `bars.a` 或 ≤ `bars.b`（整体条不比部分条长）→ "
                        "`structure.error='relation'`。摆出了数学上不存在的模型",
        },
        # ★ 内部矛盾修正（2026-10-21 复审）：上一版这里写「`calc` 也可能来自
        #   『摆对了 12 但中途移动过已知条又移回』」，同时又承认「序列化只存终态」。
        #   二者不能并存：既然不记录中途动作，就不能拿一个未记录的中间动作
        #   去解释一个终态错误码。正确的写法是**明确说出不能区分什么**。
        "competing": (
            "`calc` 只说明**终态**里 `bars.c ≠ 12` 且已知条摆对。它与下列解释"
            "**全都相容**，而现有字段**不能区分**它们："
            "①把 5+7 算成别的数；②算对了但拖动时停在别处；"
            "③先摆了别的值再改到 12 的一半。"
            "序列化只保留终态、不保留轨迹，所以本题的错误码只能定位到"
            "「结构对、结果错」，**不能定位到具体算法错在哪里**。"
            "上一版用「中途移动过又移回」解释 `calc` 是越权的——那个动作没有记录。"),
        "cannot_distinguish": (
            "终态同值时，以下解释均相容且不可分：算错 / 停错位置 / 改过又改回。"),
        "neutral": "说「整体条要盖住两根部分条，看看现在盖住了吗」",
    },
    "a76ac388": {
        "observable": {
            "modeling": "`bars.a`≠3 或 `bars.b`≠4，`answerTouched=true` → "
                        "`structure.error='modeling'`",
            "calc": "a=3、b=4 对，`bars.c`≠7 → `structure.error='calc'`",
            "relation": "`bars.c`≤3 或 ≤4 → `structure.error='relation'`",
        },
        "competing": "`calc` 也可能是「把 c 摆成 4（只记第二次拿来的量）」——"
                     "这与「算错」在终态上同值，需结合 c 的具体值区分："
                     "c=4 更可能是漏了第一次，c=别的数更像误算",
        "neutral": "说「两次拿来的纸都倒进同一个筐，筐里现在有几张」",
    },
    # ── legacy:number-line（只有终点，无结构码）──
    "5bceb172": {
        "observable": "`NumberLineRepresentation.jumps` 记录跳步数组，"
                      "`current` 记录终点。**只有 `current=21` 能对上答案**；"
                      "`jumps` 若为 `[7,7,7]` 则说明是连跳三次（正确过程），"
                      "若为 `[21]` 则是一次跳到（结果对、过程不可判定）",
        "competing": "`jumps=[21]` 也可能是孩子心算 3×7 后一次跳到位——"
                     "这在数学上是**正确**的，与「乱跳蒙对」不可分。"
                     "所以 `jumps` 长度本身不能当过程质量的证据",
        "neutral": "说「每个袋子 7 颗，三个袋子一起数，你打算怎么跳」",
    },
    # ── legacy:bar-model DEF-D1 其余四条（滑杆上限==答案）──
    "8b121389": {
        "observable": "`bars=[{id:base,value:6},{id:unknown,value:?}]`；"
                      "正解 `unknown.value=10`。"
                      "**`unknown.max=10`** —— 构造上的答案上界，"
                      "所以 `unknown.value=10` 天然可达且是最右端",
        "competing": "⚠ `unknown.value=10` 有两种来源，且**在表征上完全同形**："
                     "①算 6+4 后摆到 10；②直接把条拖到最右端。"
                     "由于 max 恰为 10，「拖到底」与「摆对」是**同一个状态**。"
                     "这不是区分力弱，是**两种来源在状态空间上重合**",
        "neutral": "说「小安的书比小雨多 4 本，未知条要比已知条长出 4 格」",
    },
    "c88410f2": {
        "observable": "`bars=[{id:base,value:9},{id:unknown,value:?}]`；"
                      "正解 13，`unknown.max=13` —— 同 DEF-D1 形态",
        "competing": "⚠ 同 8b121389：max==答案 → 拖到底即满分，无法归因。"
                     "另注：`visual` 无单位字段，"
                     "所以 `unknown.value=13` 与题面「13 千步」在表征层无连接，"
                     "**单位语义丢失**（登记为观察项）",
        "neutral": "说「小安比小雨多走 4 千步，未知条要多出 4 格」",
    },
    "e5c13ef5": {
        "observable": "`bars=[{id:base,value:7},{id:unknown,value:?}]`；"
                      "正解 11，`unknown.max=11`。"
                      "**与 c07482bb 的 visual 逐字段相同**（除无 ui_revision）",
        "competing": "⚠ 同族。**本条与 c07482bb 的状态空间完全相同**（7→11、max=11），"
                     "所以两条的 representation 在任何一次作答中都同形——"
                     "既不能互相区分，也不能互相补证。"
                     "若把它们当成两份证据，等于把同一份证据数了两次",
        "neutral": "说「小美的书比小李多 4 本，未知条要多 4 格」",
    },
    "04f97cb8": {
        "observable": "`bars=[{id:base,value:7},{id:unknown,value:?}]`；"
                      "正解 11，`unknown.max=11` —— 同 DEF-D1 形态",
        "competing": "⚠ 同族缺陷。**本条与 c07482bb 的语序相反但数值全同**"
                     "（本条「小冬比小夏少」，c07482bb「小宁比小杰多」），"
                     "本来是一对很好的语序对照，"
                     "但两条都拖到底得 11 → **对照被 DEF-D1 破坏**。"
                     "这是本批最能说明「配置缺陷会毁掉教学设计」的实例："
                     "题目本身设计得当，UI 让它失效",
        "neutral": "说「小冬比小夏少 4 张，那谁更多？多的那条要多 4 格」",
    },
    "76d49907": {
        "observable": "`current=8+5-4=9`；`jumps` 应为 `[5,-4]` 或 `[-4,5]`。"
                      "**`current=9` 是唯一判分依据**，`jumps` 不参与判分",
        "competing": "`current=9` 也可能来自 `jumps=[1]`（从 8 跳 1 格）——"
                     "结果对、过程完全错。**这是 DEF-D4 的直接后果**："
                     "终点相同则过程不可分",
        "neutral": "说「先开来了几辆，后来开走了几辆，数轴上走过哪两段」",
    },
    "bb376fbd": {
        "observable": "`current=9+6-4=11`；`jumps` 应为 `[6,-4]`。"
                      "中间态 15 在 max=16 内可达，"
                      "所以 `jumps=[6,-4]` 与 `[11]` 都停在 11",
        "competing": "同上——`[11]` 一次跳到与 `[6,-4]` 两步在终态上无差。"
                     "另：`[6,4]`（把「下去」当加）会停在 19，"
                     "超出 max=16 → 物理上跳不到，孩子会被迫回头，"
                     "**这个约束反而帮了忙**：19 不可达意味着错误路径会被界面挡住",
        "neutral": "说「车上先上来 6 个人，再下去 4 个人，人数怎么变」",
    },
    "552b39e3": {
        "observable": "`current=8+5-4=9`；`jumps` 应为 `[5,-4]`。"
                      "**与 76d49907 的 visual 逐字段相同**，"
                      "所以两条的 representation 形态完全一致，"
                      "只有题面文字不同",
        "competing": "**这一条的竞争解释与前一条同形**，"
                     "而这恰是「换情境」对照的价值："
                     "若孩子在 76d49907 上 `jumps=[5,-4]`、"
                     "在本条上 `jumps=[9]`，则说明场景换了过程就丢了——"
                     "这是可观测的迁移失败信号。"
                     "**但只有两条都留下 jumps 才可判，而判分不看 jumps**",
        "neutral": "说「书架上的书先放上后借走，数轴上走过哪两段」",
    },
    # ── legacy:bar-model（有 bars[].value，可看摆位）──
    "c07482bb": {
        "observable": "`bars=[{id:base,value:?},{id:unknown,value:?}]`。"
                      "期望是 `base.value=7`、`unknown.value=11`。"
                      "**但 `unknown.max=11`**，所以 `value=11` 有两种来源："
                      "算出 7+4，或把滑杆拖到底（DEF-D1）",
        "competing": "⚠ **本题的 `competing` 不是「别的想法」，而是硬件级歧义**："
                     "`unknown.value=11` 完全无法区分「算对了」与「拖到底了」。"
                     "这是本批唯一一处**证据本身失效**的情形，"
                     "不是「区分力待验证」，是**不可验证**",
        "neutral": "说「小宁比小杰多 4 张，未知条该比已知条长多少」",
    },
    "3ea61fc9": {
        "observable": "`bars=[{id:base,value:13},{id:unknown,value:8}]` 为正解形态。"
                      "`unknown.max=18`，**拖到底得 18 ≠ 8**，"
                      "所以本题的滑杆不泄露答案",
        "competing": "`unknown.value=18` 与「做了 13+5（方向反）」**相容**。"
                     "比 c07482bb 可用之处在于：本题拖到底得到的是 18（错值），"
                     "所以「拖到底」与「方向反」在这一题上**指向同一个值**，"
                     "仍不能区分；但它至少**排除了「拖到底就蒙对」**这一条。"
                     "**注意：这不构成对孩子的归因**，只缩小了相容假设的范围",
        "neutral": "说「姐姐比弟弟多 5 颗，弟弟的条该比姐姐的条短还是长」",
    },
    "7f22076d": {
        "observable": "`bars=[{id:base,value:14},{id:unknown,value:8}]` 为正解。"
                      "`unknown.max=20`，拖到底得 20 ≠ 8",
        "competing": "`unknown.value=20` → 做了 14+6（方向反）；"
                     "`unknown.value=14` → 直接抄已知量。"
                     "两种错法**值不同**，可分开",
        "neutral": "说「小安比小林少 6 颗，小安那条比 14 长还是短」",
    },
    "8612589b": {
        "observable": "`bars=[{id:base,value:12},{id:unknown,value:7}]` 为正解。"
                      "`unknown.max=17`，拖到底得 17 ≠ 7",
        "competing": "`unknown.value=17` → 12+5（方向反）；"
                     "`unknown.value=5` → 把差量当答案。"
                     "两种错法值不同，可分开这两个假设"
                     "（**可分开假设 ≠ 可归因**：仍只说明与该假设相容）",
        "neutral": "说「妹妹比哥哥少 5 个，妹妹那条该短 5 格」",
    },
    "ed97b114": {
        "observable": "`bars=[{id:base,value:14},{id:unknown,value:9}]` 为正解。"
                      "`unknown.max=19`，拖到底得 19 ≠ 9",
        "competing": "`unknown.value=19` → 14+5（方向反）。"
                     "**注意与 7f22076d 的错法同形**（都是 `base+差量`），"
                     "两条的错法值分别是 19 与 20——"
                     "这是「同一错法不同数值」的对照，"
                     "可用于确认方向错是稳定模式而非偶发",
        "neutral": "说「小芸比小康少 5 颗，从小康那条往回收 5 格」",
    },
    "240ff07b": {
        "observable": "`bars=[{id:total,value:13},{id:known,value:5},"
                      "{id:unknown,value:8}]` 为正解。"
                      "`unknown.max=13`，拖到底得 13 ≠ 8",
        "competing": "`unknown.value=13` → 抄整体（把未知部分当整体）；"
                     "`unknown.value=5` → 抄已知部分（把两块当一样大）。"
                     "两种错法值不同，可分开——"
                     "**本题的 bars 结构（三根条：整体/已知部分/未知部分）"
                     "比 compare 族的两根条更能暴露「整体与部分混淆」**",
        "neutral": "说「整条是 13，红的占了 5 格，剩下那截是黄的」",
    },
    "f5fb6594": {
        "observable": "`bars=[{id:total,value:15},{id:known,value:6},"
                      "{id:unknown,value:9}]` 为正解。`unknown.max=15`，不泄露",
        "competing": "`unknown.value=15` → 抄整体；`unknown.value=6` → 抄已知部分；"
                     "`unknown.value=21` 物理不可达（max=15）——"
                     "**「15+6 方向反」这条错法在本题被上限挡住了**，"
                     "所以本题看不到方向错的证据。"
                     "这是与 240ff07b（unknown.max=13=整体，21 也不可达）"
                     "相同的限制，须与「孩子不会犯方向错」区分开",
        "neutral": "说「书架共 15 本，故事书占 6 本，剩下的是科普书」",
    },
    # ── legacy:objects（groups[].count 固定，只有对齐痕迹）──
    "eaa828b3": {
        "observable": "`groups=[{id:g1,count:8,items[…]},{id:g2,count:5,items[…]}]`、"
                      "`aligned:boolean`。**`count` 永远是 8 和 5**"
                      "（config 写死、界面无增减能力），"
                      "所以 representation 里唯一会变的只有 `items[].x` 与 `aligned`",
        "competing": "`aligned=true` 只说明点过「一一对齐」按钮，"
                     "**不说明孩子看懂了多出 3 个**——"
                     "对齐是单键操作，一键完成，无过程可分。"
                     "`aligned=false` 也不能推出「没理解」（可能孩子不用对齐也能算）",
        "neutral": "说「把两支队伍一排一排对齐，看哪一列多出来了」",
    },
    "7acb4a38": {
        "observable": "`groups=[{count:6},{count:4}]`、`aligned`；"
                      "同 eaa828b3，`count` 固定，只有 `items[].x`/`aligned` 可变",
        "competing": "同 eaa828b3；另注意本题 `ability_id=app_model`"
                     "（建模）而 eaa828b3 是 app_rel（关系），"
                     "但 representation 形态**完全相同**，"
                     "所以「建模能力」在本题没有独立的可观察证据——"
                     "这是标签与证据不匹配",
        "neutral": "说「左边的积木比右边多，多出来的那几块在哪」",
    },
    "cfc971b4": {
        "observable": "`groups=[{count:8},{count:5}]`、`aligned`；"
                      "同族限制：`count` 固定",
        "competing": "**与 eaa828b3 的 groups 逐字段相同（8 和 5）**，"
                     "所以两条的 representation **必然一致**——"
                     "若孩子都用对齐，两条的痕迹一模一样。"
                     "这意味着：本题的 Q05 证据与 eaa828b3 的不可区分，"
                     "不能当成两份独立证据",
        "neutral": "说「两行花排齐后，多出来的那一行有几朵」",
    },
    # ── legacy:bar-model DEF-D2 三条（答案摆不出，证据被结构性污染）──
    "421ede36": {
        "observable": "`bars=[{id:base,value:11},{id:unknown,value:?}]`、"
                      "`max_value=17`。**正解需要 unknown.value=18，"
                      "但 bars.max=15 与 max_value=17 都小于 18**，"
                      "所以 `unknown.value` 永远到不了 18——"
                      "本题的 representation 侧**不存在正确终态**",
        "competing": "⚠ 本题的 `competing` 无意义：**没有正确表征可供对照**。"
                     "`unknown.value=15`（拖到底）既不等于答案也不等于任何"
                     "合理的错误答案（15=11+4，恰好是方向反的结果，"
                     "但这是巧合，因为 15 同时是上限）。"
                     "上限与某个错法值撞车，使「拖到底」这个动作"
                     "在证据上被误标成「方向反」——"
                     "这是**缺陷污染错误归因**的实例",
        "neutral": "说「小青 11 张，小雨比小青少 4 张，两个人数一数一共几张」",
    },
    "6e5395f0": {
        "observable": "`bars=[{id:base,value:9},{id:unknown,value:?}]`、"
                      "`max_value=14`。正解 unknown=21，**摆不出**；"
                      "而 `bars.max=12` **恰好等于第一步结果 12**，"
                      "所以「只做第一步」的表征**恰恰可以摆出来**",
        "competing": "⚠ 最严重的一条：界面**能摆出错误答案 12、摆不出正确答案 21**。"
                     "若孩子只做第一步并把 12 作为答案提交，"
                     "其 `unknown.value=12` 与「算对了两步」在表征上无法区分——"
                     "因为后者根本摆不出来。"
                     "**这不是区分力不足，是界面在系统性地奖励半成品**",
        "neutral": "说「先算小红有几本，再把两个人的加在一起」",
    },
    "8981fbcc": {
        "observable": "`bars=[{id:base,value:8},{id:unknown,value:?}]`、"
                      "`max_value=13`。正解 unknown=19 摆不出；"
                      "`bars.max=11` 等于第一步结果（小杰 11 颗）",
        "competing": "⚠ 与 6e5395f0 同型：能摆出 11（第一步）、摆不出 19（正解）。"
                     "三条 DEF-D2 的 `competing` 都指向同一个结构性事实——"
                     "**渲染模板只留两根条，而题意需要三根（较小方 / 较大方 / 合计）**，"
                     "所以这类题的 representation 侧证据整体不可用",
        "neutral": "说「先算小杰有几颗，再算两人合起来」",
    },
    "8f603745": {
        "observable": "`groups=[{count:9},{count:6}]`、`aligned`；同族限制",
        "competing": "`count` 固定 → 同 eaa828b3。"
                     "另：本条标 app_transfer（迁移），但**本批找不到同值的"
                     "非迁移配对**（9−6 只出现这一次），"
                     "所以迁移结论没有对照，`competing` 里也没有可比的错法模式",
        "neutral": "说「两个人跑的圈数排成两行，哪一行长出来了」",
    },
    # ── legacy:direct（kind=number，走 NumberRenderer 的 AnswerComposer）──
    # 已核实：`TaskRenderer.tsx::isTaskResponseReady` 对 schema_version=="1.0"
    # 且 `response_schema.representation_required==false` 时**只要求 answer 非空**，
    # 所以这四条的可提交字段确实只有 answer；`interaction_events` 里理论上
    # 会有一条 `answer_changed`（`NumberRenderer` 里构造的），但**不带值**
    # （event 只有 event_id/event_type/occurred_at/task_instance_id/renderer_id/
    # capability_id），因此不能用来还原「输入过什么又改了什么」。
    "2dd5be20": {
        "observable": "**判分字段只有 `TaskResponse.answer`（字符串）**；"
                      "`representation` 在这个 schema 下不参与提交门禁。"
                      "`answer='0'` 为正解（断言错误）。"
                      "`interaction_events` 里只有 `answer_changed` 事件，"
                      "**不带输入值**，所以无法还原输入历史。"
                      "本题的 0 与「数量为 0」在提交值上同形",
        "competing": "⚠ `answer='0'` 的两种可能：①算出弟弟=8、判断言 18 错、填 0；"
                     "②误以为「弟弟有 0 颗」、填 0。"
                     "**提交值完全相同，交互事件里也没有可用于区分的字段**。"
                     "这是本批第二个「证据本身失效」的情形（第一个是 c07482bb 的"
                     "滑杆）。区别在于：c07482bb 是配置泄露，"
                     "本条是**题型设计缺少区分字段**",
        "neutral": "说「先算算弟弟到底几颗，再和小明说的 18 比一比」",
    },
    "3706473c": {
        "observable": "只有 `answer`。正解 `'8'`。"
                      "**注意 8 也可能来自 6+2 或别的组合**——"
                      "本题的 8 不可分解来源",
        "competing": "`answer='8'` 是正解，但 8 这个值本身**没有唯一分解**："
                     "6+2=8、8−0=8、（若把梨当 2、铅笔当 0）也是 8。"
                     "所以「答对 8」不能证明做了正确的条件筛选——"
                     "只能证明没把 4 算进去。"
                     "这是本题作为条件筛选题的**根本弱点**："
                     "干扰项 4 加进去是 12，减出去是 8，"
                     "但答 8 也可能是「只加了苹果」（漏了梨）",
        "neutral": "说「题目问的是水果，桌子上的铅笔要不要算」",
    },
    "6857ba8d": {
        "observable": "只有 `answer`。正解 `'8'`（12−4）。"
                      "**11 = 12−4+3 是主要错法**，但 11 也可能来自 12+3−4 "
                      "（同值不同序）",
        "competing": "`answer='11'` 有两种错法同值：①把苹果算进橘子（12−4+3）；"
                     "②先加后减但答橘子（12+3−4，数值巧合相同）。"
                     "**两种错法的数学含义完全不同**（①是条件筛选失败、"
                     "②是只要有「放进来」就加），但提交值都是 11。"
                     "这是本批唯一「两种错法同值」的题——"
                     "如果要分开，需要额外要求写过程，当前题型做不到",
        "neutral": "说「放进来的是苹果，篮子里问的是橘子，苹果算不算橘子的数」",
    },
    "76ce803c": {
        "observable": "只有 `answer`（本题**没有** `representation`，"
                      "也没有除终值外的过程字段）。正解 `'12'`（10+5−3）。"
                      "`10+5−3+4=16` 与 `10+5=15` 都是不同值，"
                      "所以**若**孩子提交这些值，它们与特定假设相容",
        # ★ 越权归因修正（2026-10-21 复审）：上一版把「答 16」直接写成
        #   「把饼干算进糖，可归因」。本题只有 answer 一个字段，
        #   终值 16 只能说明**与**「把饼干算进去了」这个假设**相容**，
        #   不能证明孩子实际用了该算法——同一个 16 也可能来自别处。
        "competing": (
            "`answer='16'` 与「把 4 块饼干也算进糖」**相容**；"
            "`answer='15'` 与「漏掉『吃掉 3 颗』这一步」**相容**；"
            "`answer='8'` 与「把加法做成减法」相容。"
            "**以上都只是相容，不是归因**：本题只存终值，"
            "同一个终值可以来自不同算法，现有字段无法判定孩子用了哪一种。"),
        "cannot_distinguish": (
            "只有终值时，任何「他一定是这样算的」都不成立；"
            "可说的是「这个值与假设 H 相容」，不可说的是「他用了 H」。"),
        "neutral": "说「饼干也在旁边，但问的是糖，饼干要不要数」",
    },
    "623b7f19": {
        "observable": "只有 `answer`（无过程字段）。正解 `'6'`（9−3）。"
                      "`8 = 9−3+2`、`4 = 9−3−2` 都是不同值",
        "competing": (
            "`answer='8'` 与「把 2 本练习册也当成贴纸（加进去了）」相容；"
            "`answer='4'` 与「把练习册当成贴纸且方向反了（减两次）」相容。"
            "两者终值不同，**故可区分这两个假设**；但都不能从终值推出"
            "「孩子实际这样想」——只能说明与该假设相容。"),
        "cannot_distinguish": (
            "终值不同 → 可区分「相容的假设集合」；"
            "终值相同 → 不可区分具体算法。二者不要混说。"),
        "neutral": "说「书包里那 2 本练习册，和贴纸是不是一回事」",
    },
}

# ── 覆盖度自检要用的对照声明 ───────────────────────────────────────────────
# 复审要求「覆盖五类关系」。这里登记**本批真实凑出的对照对**与**凑不出的**，
# 不靠事后贴标签。
CONTRAST_PAIRS: list[dict] = [
    {
        "kind": "same_stem_two_representations",
        "a": "3ea61fc9", "b": "2dd5be20",
        "why": "同一题面（姐姐13、比弟弟多5），一个求数值（8）、一个求断言对错（0）。"
               "**本批唯一合格的「同关系不同表征」对照**",
    },
    {
        "kind": "same_operation_different_word_order",
        "a": "3ea61fc9", "b": "7f22076d",
        "why": "3ea61fc9「[已知者]比[未知者]多」、7f22076d「[未知者]比[已知者]少」。"
               "同运算（减法）、不同语序。**检验语言解析而非计算**",
    },
    {
        "kind": "same_value_different_context",
        "a": "76d49907", "b": "552b39e3",
        "why": "数值与 visual 逐字段相同（8、+5、−4），只换场景名词。"
               "**本批唯一合格的「换情境」弱对照**；措辞未变，"
               "故只能算弱证据",
    },
    {
        "kind": "same_error_different_value",
        "a": "8612589b", "b": "ed97b114",
        "why": "两者主要错法都是「base+差量」（17 与 19），"
               "用于确认方向错是稳定模式；两条错法值不同",
    },
    {
        "kind": "MISSING",
        "a": "8f603745", "b": None,
        "why": "标 app_transfer 但**找不到同值的非迁移配对**（9−6 只出现一次），"
               "迁移结论无对照，本批不作确认也不作否认",
    },
    {
        "kind": "MISSING",
        "a": None, "b": None,
        "why": "**本批没有任何一题是「同类别但用不上」的条件筛选**"
               "（4 条 conditional 的干扰项都是不同类别的物品）。"
               "扩样时必须补这一类",
    },
    {
        "kind": "MISSING",
        "a": None, "b": None,
        "why": "**本批连续变化 3 题的措辞结构完全相同**"
               "（都是「原来有…，又…，后来…」），"
               "所以「换措辞后仍能识别出两次变化」未获检验",
    },
]


def independent_eval(expr: str):
    """常量算式求值。空 builtins，只允许算术与 int()。"""
    return eval(expr, {"__builtins__": {"int": int}}, {})  # noqa: S307


def _sha256_file(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def _git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO,
            capture_output=True, text=True, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _script_provenance() -> dict:
    """出处四件套：入口 / 入口哈希 / 共享模块 / Git 提交（同 FE-1470 口径）。"""
    entry = os.path.abspath(__file__)
    shared = os.path.join(REPO, "scripts/iqc/rt1469/q03_number_input.py")
    common = os.path.join(REPO, "scripts/iqc/common.py")
    return {
        "solver_version": {
            "entry_script": os.path.relpath(entry, REPO),
            "entry_sha256": _sha256_file(entry),
            "shared_modules": [
                {"path": os.path.relpath(shared, REPO),
                 "sha256": _sha256_file(shared),
                 "role": "bind_inputs / judge_binding（输入绑定与漂移判定）"},
                {"path": os.path.relpath(common, REPO),
                 "sha256": _sha256_file(common),
                 "role": "audit_input_sha（九域规范化哈希，与 scan.py 同一口径）"},
            ],
            "git_commit": _git_commit(),
            "expression_engine": "Python eval + 空 builtins（仅算术与 int()）",
            "note": "入口与共享模块分别列出；git_commit 是本次生成时所在提交，"
                    "工作区有未提交改动时以 entry_sha256 为准。",
        },
        "result_chain": (
            "当前工作清单中的 RVID → 冻结输入 "
            "scripts/iqc/runs/inventory_manifest_r2.json（snapshot_sha256）"
            "→ 逐题 audit_input_sha256（引用值 == 现场重算值）→ verdict"),
    }


def judge_binding(ref_sha: str | None, recomputed: str | None) -> bool:
    return not (ref_sha and recomputed and ref_sha == recomputed)


def detect_visual_leak(vis: dict | None, answer: float) -> list[str]:
    """检出 V1 legacy `visual` 里「单字段恰好等于答案」的泄露点。

    这是本批新增的自检——上一批全是 V2 config，没这个机会踩坑。
    """
    if not isinstance(vis, dict):
        return []
    hits: list[str] = []
    t = vis.get("type")
    if t == "bar-model":
        for b in vis.get("bars") or []:
            if isinstance(b, dict) and b.get("max") == answer:
                hits.append(f"bars[{b.get('id')}].max")
    if vis.get("max") == answer:
        hits.append("max")
    if vis.get("max_value") == answer:
        hits.append("max_value")
    if t == "objects":
        groups = vis.get("groups") or []
        for g in groups:
            if isinstance(g, dict) and g.get("count") == answer:
                hits.append(f"groups[{g.get('id')}].count")
    return hits


def detect_unreachable(vis: dict | None, answer: float) -> str | None:
    """**线索检测器，不是可完成性判定器。**

    只回答一个问题：「最终答案的数值是否大于界面能显示的最大值」。

    ## 它不能回答什么（2026-10-21 复审指出的两处局限）

    1. **不读条的角色语义。** 它不知道哪根条代表哪个量，也不知道题目是否
       要求「未知条 = 最终合计」。对「先求另一个人的数量、再求两人合计」的
       两步题，未知条完全可以表示另一个人的数量，此时最终合计大于单条上限
       是**正常设计**，不是缺陷。
    2. **取 `max(所有上限)` 导致漏报。** 反例：答案条上限 5、另一无关条上限
       100、答案 10 —— 本函数取最大值 100 后判定「可达」，但答案条其实摆不出
       10。正确做法是读「答案条」的上限，而「哪根是答案条」需要角色语义。

    因此返回值只是**线索**，出现在报告里时必须与
    `KNOWN_DEFECTS[x].verification_plan` 一起读，不得直接写成「答案不可达」。
    """
    if not isinstance(vis, dict):
        return None
    t = vis.get("type")
    if t == "bar-model":
        caps = [b.get("max") for b in (vis.get("bars") or [])
                if isinstance(b, dict) and isinstance(b.get("max"), (int, float))]
        mv = vis.get("max_value")
        if isinstance(mv, (int, float)):
            caps.append(mv)
        if not caps:
            return None
        return (f"线索：最终答案 {answer:.0f} > 单条可摆放上限 {max(caps):.0f}"
                f"（不代表任务不可完成，需核验未知条应表示哪个量）"
                if answer > max(caps) else None)
    if t == "number-line":
        mx = vis.get("max")
        return (f"线索：最终答案 {answer:.0f} > number-line max {mx}"
                if isinstance(mx, (int, float)) and answer > mx else None)
    return None


def evaluate(check: dict, stated_raw, ems: list, ui: dict) -> dict:
    """单题核验：先独立求解，再与存储答案比较。纯函数，不连库。"""
    computed = independent_eval(check["expr"])
    try:
        stated = float(stated_raw)
    except (TypeError, ValueError):
        stated = None
    match = stated is not None and abs(float(computed) - stated) < 1e-9

    vis = (ui or {}).get("visual")
    leak = detect_visual_leak(vis, float(stated)) if stated is not None else []
    signal = detect_unreachable(vis, float(stated)) if stated is not None else None

    ev = Q05_EVIDENCE.get(check["rvid"][:8])
    # 风险挂载：按 affected 列表反查（同一风险可挂多题）
    defects = [{"id": k, **{kk: vv for kk, vv in v.items() if kk != "affected"}}
               for k, v in KNOWN_DEFECTS.items()
               if check["rvid"][:8] in v["affected"]]

    def obs_for(code: str) -> str:
        raw = (ev or {}).get("observable")
        if isinstance(raw, dict):
            return raw.get(code) or f"【缺口】本题未登记错误码 {code} 的可观察证据"
        return raw or "【缺口】本题未登记可观察证据"

    homogeneous = bool(ems) and all(
        str(e.get("code")) == str(e.get("pattern")) for e in ems)

    return {
        "rvid": check["rvid"],
        "renderer": check["renderer"],
        "relation": check["relation"],
        "relation_rule": RELATION_RULES[check["relation"]],
        "source_kind": check["source_kind"],
        "known_role": check["known_role"],
        "known_role_note": {
            "已知部分": "题面给出的是整体的一个组成部分，所求是整体或另一部分",
            "已知整体": "题面给出的是整体量（或较大/起点量），所求是从中分出/变化后的量",
            "差量": "题面给出的就是差本身，所求不是差",
            "答案副本": "配置/上限里出现的数与答案相等——**不可作为独立推导依据**，"
                        "按复审要求单独标出",
        }[check["known_role"]],
        "input_basis": check["source"],
        "target_object": check["object"],
        "derivation": {"read": check["read"], "expr": check["expr"]},
        "config_role": check["config_role"],
        "computed": computed,
        "applicable_conditions": check["boundary"],
        "stated_answer": stated_raw,
        "verdict": "MATCH" if match else "MISMATCH",
        # 单列的例外/风险线索，不混进 MATCH 统计
        "visual_leak": leak,
        # 字段名从 unreachable 改为 unreachable_signal：这是线索，不是结论
        "unreachable_signal": signal,
        "known_defects": defects,
        "ui_visual_seen": vis,
        "q05_error_models": ems,
        "q05_candidates": [{
            "code": str(e.get("code")),
            "status": ("同质占位候选，区分力尚待验证" if homogeneous
                       else "非同质，区分力尚待逐条验证"),
            "hypothesis": check.get("q05_hypothesis"),
            "observable_evidence": obs_for(str(e.get("code"))),
            "competing_explanations": (ev or {}).get("competing")
                                      or "【缺口】本题未登记竞争解释",
            "cannot_distinguish": (ev or {}).get("cannot_distinguish")
                                  or "【未登记】本题未显式声明现有字段不能区分什么",
            "neutral_feedback": (ev or {}).get("neutral")
                                or "【缺口】本题未登记中性反馈口径",
            "evidence_fields_from": "见 q03_batch3.py::Q05_EVIDENCE 头部注释",
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

    try:
        import psycopg  # noqa: F401
    except ModuleNotFoundError:
        print("ENV_ERROR: 当前解释器没有 psycopg。请用 "
              "~/.workbuddy/binaries/python/envs/learning-engine/bin/python 运行。"
              "退出码 2 表示环境错误，与核验结论无关。", file=sys.stderr)
        return 2

    sys.path.insert(0, os.path.join(REPO, "scripts", "iqc"))
    import common
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "q03_b1", os.path.join(REPO, "scripts/iqc/rt1469/q03_number_input.py"))
    b1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b1)

    # ── 硬前置 1：Q05 证据逐题登记齐全且三字段非空 ──
    missing = [c["rvid"][:8] for c in CHECKS if c["rvid"][:8] not in Q05_EVIDENCE]
    if missing:
        print(f"Q05_EVIDENCE 缺 {len(missing)} 题登记：{missing}", file=sys.stderr)
        return 1
    empty = [f"{k}.{f}" for k, v in Q05_EVIDENCE.items()
             for f in ("competing", "neutral") if not v.get(f)]
    for k, v in Q05_EVIDENCE.items():
        o = v.get("observable")
        if isinstance(o, dict):
            empty += [f"{k}.observable[{c}]" for c, s in o.items() if not s]
        elif not o:
            empty.append(f"{k}.observable")
    if empty:
        print(f"Q05_EVIDENCE 有空字段：{empty}", file=sys.stderr)
        return 1

    # ── 硬前置 2：known_role 必须是四值枚举之一 ──
    bad_role = [(c["rvid"][:8], c["known_role"]) for c in CHECKS
                if c["known_role"] not in ("已知部分", "已知整体", "差量", "答案副本")]
    if bad_role:
        print(f"known_role 非法取值：{bad_role}", file=sys.stderr)
        return 1

    # ── 硬前置 3：relation 必须是五类之一，且五类都要有题 ──
    bad_rel = [(c["rvid"][:8], c["relation"]) for c in CHECKS
               if c["relation"] not in RELATION_RULES]
    if bad_rel:
        print(f"relation 非法取值：{bad_rel}", file=sys.stderr)
        return 1
    covered = {c["relation"] for c in CHECKS}
    if covered != set(RELATION_RULES):
        print(f"五类关系未覆盖：缺 {sorted(set(RELATION_RULES) - covered)}",
              file=sys.stderr)
        return 1

    rvids = [c["rvid"] for c in CHECKS]
    if len(set(rvids)) != len(rvids):
        print("CHECKS 内有重复 RVID", file=sys.stderr)
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

    # 与上一批 RVID 重叠检查（防止把已核题重复计入进度）
    prev_path = os.path.join(REPO, "scripts/iqc/runs/FE1470_q03_batch2.json")
    prev_ids: set[str] = set()
    if os.path.exists(prev_path):
        with open(prev_path, encoding="utf-8") as f:
            prev_ids = {i["rvid"] for i in json.load(f).get("items", [])}

    out = {
        "title": "FE-1471｜Q03 独立核验第三批（计划约 20，实核 29；legacy + bar-model）",
        "batch": {
            "scope": "numeric_judge ∩ both 剩余中的 legacy:* + bar-model；计划约 20 题",
            "selection_rule": "优先 legacy:* 与 bar-model；覆盖五类题意关系",
            "relation_rules": RELATION_RULES,
            # ── 记账（与 summary.total 分开：一个是「计划做多少」，一个是「实际做了多少」）──
            "ledger": LEDGER,
            # 批外引用规则：缺陷调查可以引用批外题目，只要独立留证；
            # 「批外发现」与「本批完成数量」分账，不必为满足门禁而扩批。
            "out_of_batch_refs": {
                "rule": ("缺陷/调查可以引用批外题目，但必须独立保留其 RVID、输入与"
                         "核查证据；批外发现不计入本批完成数量。"),
                "count": 0,
                "items": [],
                "note": ("本批实际做法是扩批（7 条补入并现场核对），"
                         "所以当前没有批外引用；此字段为后续批次预留口径。"),
            },
            "not_selected_why": (
                "clock(8) 的存储答案是 h*60+m 编码，独立推导会退化成反推编码规则；"
                "estimation-canvas / shape-gallery / direction-grid 的同质题"
                "已在 FE-1468 逐题核完，重复不增证据"),
        },
        "chain": ["input_basis", "known_role", "target_object", "derivation",
                  "config_role", "applicable_conditions", "原值比较", "verdict"],
        "known_role_distribution": {},
        "provenance": {**prov, **_script_provenance()},
        "contrast_pairs": CONTRAST_PAIRS,
        "known_defects": KNOWN_DEFECTS,
        "summary": {},
        "items": results,
    }
    from collections import Counter

    def _triple(r: dict) -> tuple:
        """一题的多码候选三字段组（同码复用同组三字段）。"""
        return tuple(
            (c["code"], c["observable_evidence"], c["competing_explanations"],
             c["neutral_feedback"]) for c in (r.get("q05_candidates") or []))

    ok = [r for r in results if r["verdict"] == "MATCH"]
    _record_total = sum(len(r.get("q05_candidates") or []) for r in results)
    # ★ Q05 去重口径（2026-10-21 复审）：
    #   82 是**候选记录数**，不是 82 种有区分依据的错法。
    #   逐条比对三字段后发现实际只有 29 组：27 道多错误码题各码复用同组
    #   三字段（共 80 条），2 道单码题各 1 条。同一观察事实可以被多个假设共享，
    #   正确做法是明确「当前不能区分」，而不是换措辞制造虚假区分力。
    _distinct_groups = len({_triple(r) for r in results if r.get("q05_candidates")})
    out["summary"] = {
        "total": len(results),
        "match": len(ok),
        "mismatch": sum(1 for r in results if r["verdict"] == "MISMATCH"),
        "not_found": sum(1 for r in results if r["verdict"] == "RVID_NOT_FOUND"),
        "drift": sum(1 for r in results if r.get("input_binding", {}).get("drift")),
        "overlap_with_batch2": sorted({r["rvid"][:8] for r in results} &
                                      {i[:8] for i in prev_ids}),
        "by_relation": dict(Counter(r["relation"] for r in results)),
        "by_renderer": dict(Counter(r["renderer"] for r in results)),
        "visual_leak_items": sorted(r["rvid"][:8] for r in results if r.get("visual_leak")),
        "unreachable_signal_items": sorted(
            r["rvid"][:8] for r in results if r.get("unreachable_signal")),
        "defect_hit_items": sorted(r["rvid"][:8] for r in results if r.get("known_defects")),
        "q05_candidates_total": _record_total,
        "q05_candidate_records": _record_total,
        "q05_candidate_wording": (
            "`q05_candidates_total` / `q05_candidate_records` 是**候选记录数**"
            "（每道题的错误码各算一条），**不是**有区分依据的错法种数。"
            "同一道题的多码复用同一组三字段，因此记录数天然大于独立证据组数。"),
        "q05_distinct_evidence_groups": _distinct_groups,
        "q05_dedup_note": (
            f"去重后只有 {_distinct_groups} 组三字段（题），"
            f"却产生 {_record_total} 条候选记录——差额来自同一组三字段被各错误码复用。"
            "这不等于「错法有 82 种」，也不要求把每条记录改写成不同句子；"
            "同一观察事实可以被多个假设共享，关键是明确「当前不能区分什么」。"),
        "q05_completed": 0,
        "q05_completed_note": (
            "Q05 继续 **0 题完成**。本批只做到「已观察到什么 → 与哪些解释相容 → "
            "现有字段不能区分什么 → 可以给什么不越权的反馈」这四步的登记，"
            "不构成「错误诊断已可用」的结论。"),
        # ★ 关键口径：MATCH 是「题意级通过」，不等于「无保留完成」
        "match_definition": ("MATCH 只表示「按题面独立推导的结果与存储答案相等」。"
                             "它**不**表示该题的交互/配置无问题——"
                             "上列 visual_leak / unreachable_signal / "
                             "known_defects 是与之独立的另一笔账，必须分开读"),
        "risk_tier_note": (
            "`known_defects` 里的 15 条是「已登记的交互／配置风险条目」，"
            "不是 15 条已确证产品故障。每条带 `evidence_tier`"
            "（static_fact / inference / needs_runtime）与 `confirmed` 标志；"
            "`confirmed=false` 的条目不得被引用为「已发生的评分故障」。"),
    }
    out["known_role_distribution"] = dict(
        Counter(r["known_role"] for r in results))

    # ── 账目自洽：ledger 必须与现场实核结果对得上，不许「说 20 做 29 不吭声」──
    # 注意：这里**不再**强制「差额必须未解释」。
    # 复审裁决：不要求门禁把这批永久锁定在「差额必须未解释」的状态；
    # 29 条 RVID 身份全部明确，缺的是「初始选样名单没落盘」这一过程记录。
    led = out["batch"]["ledger"]
    traced = {r8 for v in led["traced_extra_breakdown"].values() for r8 in v}
    ledger_problems: list[str] = []
    if led["verified"] != len(results):
        ledger_problems.append(
            f"ledger.verified={led['verified']} ≠ 实核 {len(results)}")
    # 可追溯补入的每一条都必须真在本批里
    missing = traced - {r["rvid"][:8] for r in results}
    if missing:
        ledger_problems.append(f"traced_extra 里有批外 RVID：{sorted(missing)}")
    if len(traced) != led["traced_extra"]:
        ledger_problems.append(
            f"traced_extra={led['traced_extra']} ≠ 明细条数 {len(traced)}")
    # 身份完整性：29 条必须都有完整 UUID（不接受短 id、不接受重复）
    ids = [r["rvid"] for r in results]
    if len(set(ids)) != len(ids):
        ledger_problems.append("实核结果里有重复 RVID")
    for i in ids:
        if len(i) != 36 or i.count("-") != 4:
            ledger_problems.append(f"RVID 不是完整 UUID：{i!r}")
    # 计划/实际的差必须可解释：要么差额为 0，要么 selection_record 明确记录
    # 「初始名单未落盘」——记录缺失本身是允许的，**沉默**不允许。
    plan_delta = led["verified"] - led["quota"]
    if plan_delta != 0:
        if not led.get("selection_record", {}).get("missing_reason"):
            ledger_problems.append(
                f"实核 {led['verified']} 与计划 {led['quota']} 不一致（差 "
                f"{plan_delta}），但 selection_record 未说明原因")
        if not led.get("identity_complete"):
            ledger_problems.append(
                "存在计划/实际不一致，但 identity_complete 非 True——"
                "必须明确 29 条身份是否完整")
    out["batch"]["ledger"]["consistent"] = not ledger_problems
    out["batch"]["ledger"]["problems"] = ledger_problems
    if ledger_problems:
        print(f"账目不自洽：{ledger_problems}", file=sys.stderr)
        return 1

    os.makedirs(os.path.join(REPO, "scripts/iqc/runs"), exist_ok=True)
    path = os.path.join(REPO, "scripts/iqc/runs/FE1471_q03_batch3.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    for r in results:
        if r["verdict"] == "RVID_NOT_FOUND":
            print(f"NOTFOUND {r['rvid'][:8]}")
            continue
        flags = []
        if r.get("visual_leak"):
            flags.append("LEAK:" + ",".join(r["visual_leak"]))
        if r.get("unreachable_signal"):
            flags.append("SIGNAL")
        print(f"{r['verdict']:8s} {r['renderer']:20s} {r['relation']:16s}"
              f" {r['known_role']:6s} {r['derivation']['expr']:14s}"
              f" = {r['computed']:<4} stated={r['stated_answer']!r:5}"
              f" {r['rvid'][:8]} {' '.join(flags)}")
    print("\n", json.dumps(out["summary"], ensure_ascii=False, indent=1))
    print("out:", path)
    ok_all = (out["summary"]["mismatch"] == 0 and out["summary"]["drift"] == 0
              and out["summary"]["not_found"] == 0
              and not out["summary"]["overlap_with_batch2"])
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())