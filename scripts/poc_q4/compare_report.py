#!/usr/bin/env python3
"""G3：AI 输出 vs 冻结 Gold 的分歧表（模型输出 JSONL 落盘后运行）。
输入 promptfoo 结果（每行含 rvid+输出 JSON），输出误报/漏报/一致性统计。"""
import json, sys
gold = {g["rvid"]: g for g in map(json.loads, open("truth_reference.jsonl"))}
def norm(s):
    s = str(s).strip().strip("[]").replace(" ", "").replace("'", "")
    return {"True":"1","False":"0"}.get(s, s)
def main(path):
    rows = [json.loads(l) for l in open(path)]
    agree = mism = 0; m = []
    for r in rows:
        g = gold.get(r["rvid"]);
        if not g: continue
        a_ok = norm(r.get("independent_answer","")) == norm(g["independent_expected"])
        agree += a_ok; mism += not a_ok
        m.append({"seq": g["seq"], "rvid": r["rvid"][:8], "ai_answer": r.get("independent_answer"),
            "gold": g["independent_expected"], "agree": a_ok,
            "ai_risks": r.get("risk_code"), "gold_note": g.get("note","")})
    out = {"n": len(m), "agree": agree, "mismatch": mism,
        "consistency": round(agree/len(m)*100,1) if m else None, "rows": m}
    json.dump(out, open("g3_consistency_report.json","w"), ensure_ascii=False, indent=1)
    print(f"G3: {agree}/{len(m)} 一致 = {out['consistency']}%（目标≥80%）")
    return 0
if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
