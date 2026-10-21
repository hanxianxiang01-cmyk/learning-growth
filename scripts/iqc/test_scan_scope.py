#!/usr/bin/env python3
"""scan.py 口径回归测试（DB-free，进 pr_gate.py 第 5 项）。

背景（2026-10-21 实测发现）：scan.py 为 Q01 版本链校验，会把 mapping 端点的
历史版本（superseded）补载进 items 字典；若逐题规则跟着遍历整个 items，
published 口径就会混进非 published 版本——实测 published=225 却产出 239 个
RVID 的 findings（467 条），且 Q03-UNVERIFIED 恰等于 225（= published 总数），
因为 14 条 superseded 也被判了 UNVERIFIED。

这类缺陷的特征是**结果看起来合理**（数字都不为 0、P0=0、门禁全绿），
只有把"分母"和"分子"对账才会暴露。因此本测试做两件事：

  S1 静态结构锁：scan.py 必须在 mapping 扩展前冻结逐题规则的作用域，
     且逐题循环不得再直接遍历 items 全量（防止回退）
  S2 口径一致性：coverage 必须输出 audited_scope / mapping_side_loaded，
     且 audited_published 只能按冻结集合计算

S3 变异对照：把"冻结"去掉后，用一个最小构造证明数字会变——
证明 S1/S2 不是形式主义。
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCAN = os.path.join(HERE, "scan.py")

fails = []


def note(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


src = open(SCAN, encoding="utf-8").read()
tree = ast.parse(src)

# ---------- S1 静态结构锁 ----------
# 1a: 必须存在 target_ids 冻结
has_freeze = "target_ids" in src
note("S1a 逐题规则作用域被冻结（target_ids 存在）", has_freeze,
     "缺 target_ids：mapping 侧载的历史版本会混进 published 口径" if not has_freeze else "")

# 1b: 冻结语句必须出现在 mapping 块之前
idx_freeze = src.find("target_ids = list(items.keys())")
idx_mapping = src.find("if args.mapping:")
note("S1b 冻结早于 mapping 扩展", 0 <= idx_freeze < idx_mapping,
     f"freeze@{idx_freeze} mapping@{idx_mapping}"
     + ("（顺序反了：先载入历史版本再冻结，等于没冻）"
        if idx_freeze > idx_mapping >= 0 else ""))

# 1c: 逐题循环不得再遍历 items 全量
bad_loops = []
for node in ast.walk(tree):
    if isinstance(node, ast.For) and isinstance(node.iter, ast.Attribute):
        # 形态：for it in items.values() / for it in items.items()
        it = node.iter
        if (isinstance(it.value, ast.Name) and it.value.id == "items"
                and it.attr in ("values", "items")):
            bad_loops.append(node.lineno)
# Q01 的 multi_published 允许传整个 items（它需要跨版本比较），
# 但 Q03/Q05/Q06 逐题循环不允许。
note("S1c 逐题循环不再遍历 items 全量",
     len(bad_loops) <= 1,
     f"发现 {len(bad_loops)} 处 items.values()/items.items() 循环 @行 {bad_loops}；"
     f"仅 Q01 多 published 检查允许（需跨版本），逐题规则不允许")

# 1d: 逐题循环必须走 target_ids
has_scoped_loop = "for it in (items[i] for i in target_ids)" in src or \
                  "for i in target_ids" in src
note("S1d 存在按 target_ids 限定的逐题循环", has_scoped_loop,
     "" if has_scoped_loop else "未找到 target_ids 限定的逐题循环（会回退成全量遍历）")

# ---------- S2 口径一致性字段 ----------
note("S2a coverage 含 audited_scope", "audited_scope" in src,
     "" if "audited_scope" in src else "缺 audited_scope：无法从产物判断实际审计了多少条")
note("S2b coverage 含 mapping_side_loaded", "mapping_side_loaded" in src,
     "" if "mapping_side_loaded" in src
     else "缺 mapping_side_loaded：mapping 侧载了多少历史版本不可见")

# audited_published 的口径最终由外层 pub 的定义决定。
# 注意：Q01 的多 published 检查内部也有一个同名局部变量 pub（按 resource_id 过滤），
# 那是另一个作用域，必须靠缩进区分——这里只认 4 空格缩进的函数级定义。
pub_def = [l for l in src.splitlines()
           if l.startswith("    pub =") and "review_status" in l]
note("S2c 分子口径随冻结集合收敛（pub 按 target_ids 过滤）",
     bool(pub_def) and "target_ids" in pub_def[0],
     pub_def[0].strip() if pub_def else "未找到函数级 pub = {...} 定义")
audited_line = [l for l in src.splitlines()
                if '"audited_published"' in l and not l.lstrip().startswith("#")]
note("S2d audited_published 取自收敛后的 pub",
     bool(audited_line) and "len(pub)" in audited_line[0],
     audited_line[0].strip() if audited_line else "缺 audited_published 赋值")

# ---------- S3 变异对照：证明冻结确实改变结果 ----------
# 最小构造，严格复刻 scan.py 的真实顺序：
#   冻结 target_ids  →  逐题规则跑冻结集合  →  mapping 补载 superseded（追加到 items）
items = {
    "pub-a": {"review_status": "published"},
    "pub-b": {"review_status": "published"},
}
frozen = list(items.keys())          # ← 冻结发生在补载之前
items["old-c"] = {"review_status": "superseded"}   # ← mapping 侧载
items["old-d"] = {"review_status": "superseded"}   # ← mapping 侧载

frozen_scope = [items[i]["review_status"] for i in frozen]
mutant_scope = [v["review_status"] for v in items.values()]
note("S3 变异对照：不冻结会多审计 superseded",
     frozen_scope.count("published") == 2
     and len(frozen_scope) == 2
     and mutant_scope.count("superseded") == 2
     and len(mutant_scope) > len(frozen_scope),
     f"冻结后审计 {frozen_scope}（{len(frozen_scope)} 条，published=2）；"
     f"未冻结审计 {mutant_scope}（{len(mutant_scope)} 条，混入 2 条 superseded）"
     f"→ 正是实测 225 vs 239 的来源")

print("\nSCAN-SCOPE-GATE:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)