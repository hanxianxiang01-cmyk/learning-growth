#!/usr/bin/env python3
"""FE-1460 确定性校验器·规则集 v1（裁决 §二 五域，无 LLM 依赖）。

纪律：
- 阈值/状态词读 rules.json；题库发现只走 FE-1459 manifest（本模块是纯函数规则，
  item 由调用方注入——单测用夹具负例，全库扫描用 manifest+DB）
- 不把所有题型强转算术：无法独立推导 → UNVERIFIED；语义争议 → REVIEW_REQUIRED
- 已知修复不误报：现行口径只看 published；旧版缺陷夹具由 scan 侧 mapping 校验链闭合
"""
import json
import re
from fractions import Fraction

# ---------- Q01 资源与版本 ----------

def q01_version_chain(items, migration_rows):
    """items: {rvid: item}；migration_rows: [old,new] 映射。
    链闭合：每映射 old 已让位 & new=published & 同 resource_id & version_no 递增。"""
    out = []
    for old, new in migration_rows:
        o, n = items.get(old), items.get(new)
        if o is None or n is None:
            out.append(("Q01-CHAIN-MISSING", "P1", f"{old[:8]}→{new[:8]} 映射端缺行", new)); continue
        if n["review_status"] != "published":
            out.append(("Q01-NOT-PUBLISHED", "P1", f"新版状态={n['review_status']}", new))
        if o["review_status"] not in ("superseded", "qa_retired", "qa_staged"):
            out.append(("Q01-OLD-STATE", "P1", f"旧版状态={o['review_status']}（应已让位）", old))
        if o["resource_id"] != n["resource_id"]:
            out.append(("Q01-RESOURCE-MISMATCH", "P0", "新旧非同一逻辑资源", new))
        if n["version_no"] <= o["version_no"]:
            out.append(("Q01-VERSION-ORDER", "P1", f"v{o['version_no']}→v{n['version_no']}", new))
    return out


def q01_multi_published(items):
    """同 resource_id 多 published = P0（分组键=逻辑身份 resource_id）。"""
    from collections import Counter
    rc = Counter(i["resource_id"] for i in items.values() if i["review_status"] == "published")
    return [("Q01-DUP-PUBLISHED", "P0", f"{rid} 有 {n} 个 published", rid)
            for rid, n in rc.items() if n > 1]


# ---------- Q02 Schema 与契约 ----------

def q02_schema_contract(item):
    ui = item["ui_schema"]
    v = str(ui.get("schema_version") or "")
    rid = item["resource_version_id"]
    if v == "2.0":
        errs = []
        if not isinstance(ui.get("workspaces"), list) or not ui["workspaces"]:
            errs.append("workspaces 缺失/空")
        else:
            if not ui["workspaces"][0].get("renderer"):
                errs.append("renderer 缺失")
        if not ui.get("response_contract"):
            errs.append("response_contract 缺失")
        return [("Q02-V2-INCOMPLETE", "P1", e, rid) for e in errs]
    if v == "1.0":
        errs = []
        if not ui.get("kind"): errs.append("kind 缺失")
        if not ui.get("response_schema"): errs.append("response_schema 缺失")
        return [("Q02-V1-INCOMPLETE", "P1", e, rid) for e in errs]  # V1 无 renderer 字段不算缺陷
    return [("Q02-BLOCKED_SCHEMA", "P1", f"schema_version={v!r} 未知形态", rid)]


# ---------- Q03 独立答案（PoC math_reference 沉淀；不调产品 Judge）----------

_NUM = r"(\d+(?:\.\d+)?)"


def q03_arithmetic(item):
    """适用模板=P0 已人工验证的窄集（PoC truth_reference 同源）。宁 UNVERIFIED 不误报。"""
    rid = item["resource_version_id"]
    stem = re.sub(r"\*\*", "", item["content"].get("stem") or "")
    ans = item["content"].get("answer")
    if ans is None:
        return [("Q03-NO-ANSWER-FIELD", "P2", "content 无 answer", rid)]
    # 判断型 check（请检查…正确填1错误填0）：独立核验被引公式，再映射 0/1 答案轴
    if re.search("(请)?检查|正确填1.{0,6}错误填0|错误填0.{0,6}正确填1", stem):
        claim = re.search(QUOTE_CLAIM, stem)
        if claim:
            val = _eval_chain(claim.group(1))
            if val is not None and val["rhs"] is not None:
                return _cmp_check(val["lhs"], val["rhs"], ans, rid)
        return [("Q03-UNVERIFIED", "P3", "判断型无法定位被验等式（含二级推导类保守放行）", rid)]
    # 链式开放算式（9+9+9= / 8 - 3 = ?）：答案=链值
    m = _CHAIN_RE.search(stem)
    if m and not m.group(2):   # 组2=等号后的数字；无=开放式（9+9+9=）才与 answer 比
        val = _eval_chain(m.group(1))
        if val:
            return _cmp_val(val["lhs"], ans, rid)
    mm = re.search(r"(\d+)\s*个.*?每[个组袋]里?有?(\d+)", stem)
    if mm:
        return _cmp_val(int(mm.group(1)) * int(mm.group(2)), ans, rid)
    mm = re.search(r"从(\d+)出发.*?向右跳(\d+).*?跳(\d+)次", stem)
    if mm:
        return _cmp_val(int(mm.group(1)) + int(mm.group(2)) * int(mm.group(3)), ans, rid)
    mm = re.search(r"每排.*?(\d+)\s*(?:人|个).*?(\d+)\s*排", stem)
    if mm:
        return _cmp_val(int(mm.group(1)) * int(mm.group(2)), ans, rid)
    return [("Q03-UNVERIFIED", "P3", "无独立推导模板（不强转算术）", rid)]


_QUOTE_CHARS = "\u201c\u201d\""
QUOTE_CLAIM = "[" + _QUOTE_CHARS + "]([^" + _QUOTE_CHARS + "]+)[" + _QUOTE_CHARS + "]"
_CHAIN_RE = re.compile(r"(\d+(?:\s*[+\-]\s*\d+)+\s*=)\s*(\d+)?")


def _eval_chain(expr):
    """安全求值 '12 - 5 + 2 = 9' 或 '9+9+9='；返回 {lhs, rhs(可空)}。"""
    if "=" in expr:
        left, right = expr.split("=", 1)
        right = right.strip()
    else:
        left, right = expr, ""
    toks = re.findall(r"\d+|[+\-]", left)
    if not toks or len(toks) % 2 == 0:
        return None
    try:
        acc = int(toks[0])
        for i in range(1, len(toks), 2):
            acc = acc + int(toks[i + 1]) if toks[i] == "+" else acc - int(toks[i + 1])
    except (ValueError, IndexError):
        return None
    return {"lhs": acc, "rhs": int(right) if right.isdigit() else None}


def _cmp_val(expected, ans, rid):
    try:
        ok = Fraction(str(expected)) == Fraction(str(ans))
    except Exception:
        ok = str(expected) == str(ans)
    if ok:
        return [("Q03-OK", "P3", f"独立推导={expected}==answer", rid)]
    return [("Q03-ANSWER_MISMATCH", "P0", f"独立推导={expected} vs DB answer={ans}", rid)]


def _cmp_check(lhs_val, rhs_claimed, ans, rid):
    """判断型：被验等式 lhs==rhs_claimed → 期望填 1（对）/0（错）。"""
    expect = 1 if lhs_val == rhs_claimed else 0
    try:
        ok = int(ans) == expect
    except Exception:
        ok = str(ans) == str(expect)
    if ok:
        return [("Q03-OK", "P3", f"判断核验 {lhs_val}=={rhs_claimed} → 填{expect}，answer 一致", rid)]
    return [("Q03-ANSWER_MISMATCH", "P0", f"判断核验期望={expect} vs DB answer={ans}", rid)]


# ---------- Q05 错误模型同质 ----------

def q05_error_models(item):
    ems = item.get("error_models") or []
    rid = item["resource_version_id"]
    if not ems:
        return [("Q05-EMPTY", "P3", "无错误模型（部分题合法）", rid)]
    homo = [e for e in ems if isinstance(e, dict) and e.get("code") and e.get("code") == e.get("pattern")]
    if len(homo) == len(ems):
        return [("Q05-HOMOGENEOUS", "P2", f"{len(ems)} 条 code==pattern 同质占位", rid)]
    return []


# ---------- Q06 Hint 阶梯 ----------

_LEAK_PATTERNS = [
    (r"答案是\s*[:：]?", "直接'答案是X'"),
    (r"(应该|该)(选|填|点).{0,4}(加|减|乘|除)[号]", "指定正确选项"),
]


def q06_hint_ladder(item):
    hp = item.get("hint_policy") or {}
    lad = hp.get("ladder") if isinstance(hp, dict) else None
    out = []
    rid = item["resource_version_id"]
    if not isinstance(lad, list):
        return [("Q06-LADDER-TYPE", "P1", "ladder 缺失/非列表", rid)]
    if len(lad) < 2:
        out.append(("Q06-LADDER-SHORT", "P2", f"提示仅 {len(lad)} 级", rid))
    ans = str(item["content"].get("answer", ""))
    stem = item["content"].get("stem") or ""
    stem_disclosed = bool(ans) and re.search(r"(?<![\d.])" + re.escape(ans) + r"(?![\d.])", stem)
    for i, h in enumerate(lad):
        t = h if isinstance(h, str) else str(h.get("text") or h.get("hint") or "")
        # 泄露判定=提示引入题面未披露的答案信息；题面已含该值则 Hint 复述不构成泄露（增量=0）
        if i < 2 and ans and not stem_disclosed and re.search(r"(?<![\d.])" + re.escape(ans) + r"(?![\d.])", t):
            out.append(("Q06-HINT-LEAK", "P1", f"L{i+1} 直接含答案 {ans!r}：{t[:40]}", rid))
        for pat, why in _LEAK_PATTERNS:
            if re.search(pat, t):
                out.append(("Q06-LEAK-PATTERN", "P1", f"L{i+1} {why}：{t[:40]}", rid))
    return out


# ---------- Q10 快照漂移检测 ----------

def q10_snapshot_integrity(expected_sha, items_with_audit_sha):
    import hashlib
    canon = json.dumps([[i["resource_id"], i["version_no"], i["resource_version_id"],
                         i["review_status"], i["_audit_sha"]]
                        for i in sorted(items_with_audit_sha, key=lambda x: (x["resource_id"], x["version_no"]))],
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest() == expected_sha


def q06_stem_leak(item):
    """题面强披露语境含答案（照抄即对候选）。判定=答案紧邻披露标记
    （= / ＝ / 标价 / 组成 / 面积），而非题面任意普通数字——
    首版裸数字匹配 12/18 误报教训固化为窄语境。0/1 判断轴与符号答案排除。"""
    ans = str(item["content"].get("answer", ""))
    stem = (item["content"].get("stem") or "").replace("**", "")
    rid = item["resource_version_id"]
    if not ans or ans in ("0", "1", "-", "+") or re.search(r"填1|填0|正确填|错误填", stem):
        return []
    pat = r"(?:[=＝]\s*|标价|组成\s*|面积\s*[=＝]?|答案是)" + re.escape(ans) + r"(?![\d.])"
    if re.search(pat, stem):
        return [("Q06-STEM-LEAK", "P1", f"题面披露语境含答案 {ans}：照抄即对候选（弱披露=答案为题面输入数——归语义线）", rid)]
    return []
