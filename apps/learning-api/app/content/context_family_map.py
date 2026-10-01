"""50 题 content.stem → context_family 映射（AC-04 回填评审产物）。

依据：docs/governance/CONTEXT_FAMILY_VOCABULARY.md（词表）
     + 治理文档 §6 三态流程（PASS / REVIEW / REJECT）。
- PASS 44 题：明确归入 canonical family。
- REVIEW 6 题（气球/玩具车/苹果梨/球/玻璃珠/杯子）：日常物品无 canonical family
  （everyday_objects 未走 §10 扩展协议批准），保持 NULL，不硬猜、不伪装。
- REJECT 0 题。

seed 与回填脚本共用本映射；写库前必须过 canonicalize_context_family 校验。
"""
from __future__ import annotations

# stem 完整文本 → family（None = REVIEW，待词表扩展裁决）
STEM_CONTEXT_FAMILY: dict[str, str | None] = {
    # ---- app_check ----
    "小美有6支红笔和4支蓝笔。小东说“一共有10支笔”。请检查：正确填1，错误填0。": "school_objects",
    "小林有8个苹果，吃掉3个。小华算“8 - 3 = 6”。请检查：小华的答案正确填1，错误填0。": "before_after",
    "姐姐有13颗珠子，比弟弟多5颗。小明说“弟弟有18颗珠子”。请检查：正确填1，错误填0。": "comparison",
    "停车场有12辆车，开走5辆，又开来2辆。小杰列式“12 - 5 + 2 = 9”，说现在有9辆。请检查：正确填1，错误填0。": "before_after",
    "小明有9本书，小红比小明多3本。小华说“两个人一共有21本”，他的过程是“9 + 3 = 12，12 + 9 = 21”。请检查：正确填1，错误填0。": "comparison",
    # ---- app_cond ----
    "小雨有4个红气球、3个蓝气球，还带了2本故事书。红气球和蓝气球一共有多少个？": None,  # REVIEW
    "玩具箱里有5辆玩具汽车、3辆玩具火车和2个皮球。玩具汽车和玩具火车一共有多少辆？": None,  # REVIEW
    "桌上有6个苹果、2个梨，还有4支铅笔。苹果和梨一共有多少个？": None,  # REVIEW
    "篮子里原来有12个橘子，吃掉4个，又放进3个苹果。篮子里还剩多少个橘子？": "before_after",
    "小芳有9张贴纸，送给小美3张。她的书包里还有2本练习册。小芳还剩几张贴纸？": "before_after",
    "盒子里有10颗糖，又放进5颗，后来吃掉3颗。旁边还有4块饼干。现在盒子里有多少颗糖？": "before_after",
    # ---- app_model ----
    "左边有6块积木，右边有4块积木。左边比右边多几块？": "comparison",
    "一盒彩纸有13张，其中红色5张，其余是黄色。黄色彩纸有多少张？": "school_objects",
    "小车原来在数轴的11位置，向左走了3格。现在在几的位置？": "before_after",
    "小雨有6本书，小安比小雨多4本。小安有多少本书？": "comparison",
    "小芸比小康少5颗星星。小康有14颗星星。小芸有多少颗？": "comparison",
    "小兰有8颗糖，小杰比小兰多3颗。两个人一共有多少颗糖？": "comparison",
    "公交车上原来有9个人，到第一站上来6人，到第二站下去4人。现在车上有多少人？": "before_after",
    # ---- app_rd ----
    "小青有4支红笔和6支蓝笔。题目问：小青有几支红笔？": "school_objects",
    "乐乐有5个橘子和2本书。题目问：乐乐有几本书？": "school_objects",
    "操场上小东有7个球，小西有3个球。题目问：小西有几个球？": None,  # REVIEW
    "小明有9颗棋子，小亮有6颗棋子，小红有4本故事书。题目问：小亮有几颗棋子？": "school_objects",
    "小云上午画了6朵花，下午画了3棵树。老师问：小云上午画了几朵花？": "time_schedule",
    "小然上午带了8张卡片去学校，中午又借了2本书给同桌，下午买了3支铅笔。题目问：小然上午带了几张卡片？": "time_schedule",
    # ---- app_rel ----
    "盘子里原来有9块饼干，小乐吃了3块。盘子里还剩多少块饼干？": "before_after",
    "小雨有4个红气球，又拿来了3个蓝气球。现在一共有多少个气球？": "before_after",
    "树上原来有6只小鸟，又飞来了2只。现在树上一共有多少只小鸟？": "before_after",
    "小东有8支彩笔，小西有5支彩笔。小东比小西多几支彩笔？": "comparison",
    "盒子里一共有12张贴纸，其中5张是星星贴纸，其余都是圆形贴纸。圆形贴纸有多少张？": "school_objects",
    "有2盒彩笔，每盒都有6支。两盒一共有多少支彩笔？": "school_objects",
    "姐姐有13颗珠子，比弟弟多5颗。弟弟有多少颗珠子？": "comparison",
    "小李有7本故事书，小美比小李多4本。小美有多少本故事书？": "comparison",
    "小安的棋子比小林少6颗。小林有14颗棋子。小安有多少颗棋子？": "comparison",
    "有3个相同的小袋子，每个袋子里有7颗玻璃珠。3个袋子一共有多少颗玻璃珠？": None,  # REVIEW
    "小青有11张贴纸，小雨比小青少4张。两个人一共有多少张贴纸？": "comparison",
    # ---- app_strat ----
    "小明有5支铅笔，妈妈又给了他3支。现在小明有多少支铅笔？": "before_after",
    "盘子里有10块饼干，小明吃了4块。盘子里还剩多少块？": "before_after",
    "小红有8朵花，小蓝有5朵花。小红比小蓝多几朵？": "comparison",
    "小杰有7张卡片，小宁比小杰多4张。小宁有多少张卡片？": "comparison",
    "哥哥有12个贝壳，比妹妹多5个。妹妹有多少个贝壳？": "comparison",
    "书桌上共有15本书，其中6本是故事书，其余是科普书。科普书有多少本？": "school_objects",
    "小宇送给同学3张贴纸后，自己还剩8张。小宇原来有多少张贴纸？": "before_after",
    "小冬有7张卡片，小冬比小夏少4张。小夏有多少张卡片？": "comparison",
    "小明有9本故事书，小红比小明多3本。两个人一共有多少本故事书？": "comparison",
    "停车场原来有8辆车，又开来5辆，后来开走4辆。现在停车场有多少辆车？": "before_after",
    # ---- app_transfer（迁移题，决定 transfer diversity）----
    "晨练时，小海跑了9圈，小森跑了6圈。小海比小森多跑几圈？": "comparison",
    "教室里原来摆了12把椅子，老师又搬来4把。现在一共有多少把椅子？": "before_after",
    "小雨今天走了9千步，小安比小雨多走4千步。小安今天走了多少千步？": "comparison",
    "餐桌上共有18个杯子，其中7个是蓝色的，其余是白色的。白色杯子有多少个？": None,  # REVIEW
    "书架上原来有8本新书，老师又放上5本，后来同学借走4本。现在书架上有多少本书？": "before_after",
}

# 汇总检查：44 PASS + 6 REVIEW = 50；REVIEW 一律 None，不得给猜测值
assert len(STEM_CONTEXT_FAMILY) == 50, f"映射应覆盖 50 题，当前 {len(STEM_CONTEXT_FAMILY)}"
assert sum(1 for v in STEM_CONTEXT_FAMILY.values() if v is None) == 6
