#!/usr/bin/env python3
"""V1.4 题库交付包·一致性审计脚本（PC-v1 §10 六类规则的独立可运行版）

用法:
    python3 consistency_audit.py <questions.json>
    # questions.json 顶层含 "questions": [...]（与 trial155/v2 批格式一致），
    # 或直接为题目列表。

退出码: 0=全通过, 1=存在违规（逐题打印）。
本脚本不依赖本项目代码，纯标准库，可直接随任务单发给交付方自检。
"""
import json
import sys

VOCAB_FAMILY = {
    "school_objects", "comparison", "before_after", "lineup_position",
    "shopping", "sharing", "time_schedule",
}


def get_ws(q):
    ws = q.get("task_ui_schema", {}).get("workspaces", [])
    return ws[0] if ws else {}


def ans_scalar(q):
    a = q.get("answer")
    if isinstance(a, dict):
        a = a.get("value")
    return a


def audit(questions):
    errs = []
    for q in questions:
        qid = q.get("question_id", "?")
        r = q.get("renderer_id") or get_ws(q).get("renderer")
        cfg = get_ws(q).get("config", {}) or {}
        a = ans_scalar(q)

        # R1 answer 必须是标量（PC-v1 §4/§5：禁 {type,value} 包装入库形态）
        if isinstance(q.get("answer"), dict) and set(q["answer"].keys()) - {"value", "type"}:
            errs.append(f"{qid} [{r}] answer 含 value/type 之外的包装字段")

        # R2 money-board: change 类 paid - price == answer；凑付类 total == price 语义
        if r == "money-board" and isinstance(cfg.get("target"), dict):
            t = cfg["target"]
            if "paid" in t and "price" in t and isinstance(a, (int, float)):
                if t["paid"] - t["price"] != a:
                    errs.append(f"{qid} money-board: paid-price={t['paid'] - t['price']} ≠ answer={a}")

        # R3 direction-grid: 坐标 0 起且界内；非纯直线（dr、dc 均≠0）
        if r == "direction-grid":
            g = cfg.get("grid", {})
            rows, cols = g.get("rows"), g.get("cols")
            for side in ("start", "target"):
                s = cfg.get(side) or {}
                rr, cc = s.get("row", s.get("r")), s.get("col", s.get("c"))
                if None in (rows, cols, rr, cc):
                    continue
                if rr < 0 or cc < 0:
                    errs.append(f"{qid} direction-grid: {side} 坐标负值（须 0 起）")
                elif rr >= rows or cc >= cols:
                    errs.append(f"{qid} direction-grid: {side}={rr},{cc} 越界 {rows}x{cols}（疑 1 起坐标）")
                if rr is not None and cc is not None:
                    sr = (cfg.get("start") or {}).get("row", (cfg.get("start") or {}).get("r"))
                    sc = (cfg.get("start") or {}).get("col", (cfg.get("start") or {}).get("c"))
                    if None not in (sr, sc) and (rr - sr == 0 or cc - sc == 0):
                        errs.append(f"{qid} direction-grid: 纯直线路线（dr 或 dc=0），无转向教学点")

        # R4 clock: 分针只允许整/半点两档
        if r == "clock":
            st = cfg.get("start", {}) or {}
            def bad_min(v):
                return v is not None and int(v) not in (0, 30)
            if bad_min(st.get("minute", st.get("m"))):
                errs.append(f"{qid} clock: start 分针 {st} 非整/半点")
            tgt = cfg.get("target")
            tm = None
            if isinstance(tgt, str) and ":" in tgt:
                tm = int(tgt.split(":")[1])
            elif isinstance(tgt, dict):
                tm = tgt.get("minute", tgt.get("m"))
            if bad_min(tm):
                errs.append(f"{qid} clock: target 分针 {tgt} 非整/半点，两档 UI 摆不出")

        # R5 grouping-board: total 可被 group_size 整除
        if r == "grouping-board":
            gs = cfg.get("group_size") or cfg.get("groupSize")
            tot = cfg.get("total")
            if isinstance(gs, int) and gs > 0 and isinstance(tot, (int, float)):
                if float(tot) % gs != 0:
                    errs.append(f"{qid} grouping-board: total={tot} 不能被 group_size={gs} 整除")

        # R6 pattern-board: token 拼接标量答案须个位无歧义
        if r == "pattern-board" and isinstance(a, int) and a >= 10:
            errs.append(f"{qid} pattern-board: 答案 {a} 多位数，破坏 token 拼接无歧义前提（改答案轴或换挂）")

        # R7 estimation-canvas: 值域与容差
        if r == "estimation-canvas":
            mx = cfg.get("max")
            tol = cfg.get("tolerance")
            if isinstance(mx, (int, float)) and mx > 60:
                errs.append(f"{qid} estimation-canvas: max={mx} 超滑条值域 60")
            if isinstance(tol, (int, float)) and isinstance(mx, (int, float)) and tol >= mx:
                errs.append(f"{qid} estimation-canvas: tolerance={tol} 贴/超值域边界")

        # R8 context_family 受控词表
        cf = q.get("context_family")
        if cf is not None and cf not in VOCAB_FAMILY:
            errs.append(f"{qid}: context_family '{cf}' 越出受控词表")

    return errs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    questions = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(questions, list):
        print("格式错误：需为题目列表或含 questions 键", file=sys.stderr)
        sys.exit(2)
    errs = audit(questions)
    print(f"审计 {len(questions)} 题，违规 {len(errs)} 条")
    for e in errs:
        print("  FAIL:", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
