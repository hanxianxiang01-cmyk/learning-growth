#!/usr/bin/env python3
"""V1.4 题库交付包·一致性审计脚本 v2（Gate 2 权威工具；PC-v1 §10 规则 + FE-1432e 核验修复）

用法:
    python3 consistency_audit.py <questions.json>
    # questions.json 顶层含 "questions": [...]（与 v2 批格式一致），或直接为题目列表。

退出码: 0=全通过, 1=存在违规, 2=输入错误。纯标准库零依赖。
v2 修复（FE-1432e 核验 P0-A/P0-B/P1-C/P1-D，经我方独立反例+金样例正例交叉验收）：
  R1 answer 拒 {type,value} 包装/空值（含 content.answer 双位置冲突检测）
  R3 direction 仅 start→target 判直线（消除起点自比较误报）+ 终点格编码数值匹配
  R7 estimation max/min/tolerance 必填 + 目标±容差不得贴/超滑条边界
  R8 context_family 缺失也判 FAIL
回归基线：fixtures/gold_positive.json 须 0 违规、fixtures/negative_cases.json 须恰 4 条（FE-1432h 起：新增 clock 数组锚点 G-6/T-6，原基线 3 条）。
Gate 3 Config×Parser 仍须由权威仓库 audit-155-config.mjs 复跑；本脚本不能代替 Gate 3。
"""
import json
import sys
from pathlib import Path

VOCAB_FAMILY = {
    'school_objects', 'comparison', 'before_after', 'lineup_position',
    'shopping', 'sharing', 'time_schedule',
}


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def get_ws(q):
    schema = q.get('task_ui_schema') or {}
    ws = schema.get('workspaces', []) if isinstance(schema, dict) else []
    return ws[0] if isinstance(ws, list) and ws and isinstance(ws[0], dict) else {}


def coord(cfg, name):
    obj = cfg.get(name) or {}
    if not isinstance(obj, dict):
        return None
    return (obj.get('row', obj.get('r')), obj.get('col', obj.get('c')))


def minute_value(v):
    # FE-1432h：canonical clock config = 数组 [hour, minute]（R17 parser readTime 唯一形态）。
    # 原 v2 兼容 dict/HH:MM 仅为审计旧 trial155；数组分支经交付方提案（reports/
    # gate2_v2_clock_array_support_proposal.diff）验收方裁决合并。
    if isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in v):
        h, m = v
        if not (1 <= h <= 12):
            return 'INVALID'
        return m
    if isinstance(v, dict):
        v = v.get('minute', v.get('m'))
    elif isinstance(v, str) and ':' in v:
        v = v.rsplit(':', 1)[1]
    elif isinstance(v, str) and ':' not in v:
        return None
    if v is None:
        return None
    try:
        iv = int(v)
        if str(v).strip() not in {str(iv), f'{iv:02d}'} and not isinstance(v, int):
            raise ValueError('not integer minute')
        return iv
    except (ValueError, TypeError):
        return 'INVALID'


def audit(questions):
    errs = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            errs.append(f'#{i+1}: 题目不是 JSON 对象')
            continue
        qid = q.get('question_id') or f'#{i+1}'
        ws = get_ws(q)
        r = q.get('renderer_id') or ws.get('renderer')
        cfg = ws.get('config') or {}
        if not isinstance(cfg, dict):
            errs.append(f'{qid} [{r}] config 不是对象')
            cfg = {}

        # R1: 不接受 {type,value} 包装或空 answer；优先读取试灌交付格式顶层 answer。
        # 兼容后续 content.answer 的合法标量，但两位置同时提供且冲突必须拒收。
        root_present = 'answer' in q
        content = q.get('content')
        nested_present = isinstance(content, dict) and 'answer' in content
        raw = q.get('answer') if root_present else (content.get('answer') if nested_present else None)
        a = raw.get('value') if isinstance(raw, dict) else raw  # 仅供其他规则继续定位既有违规
        if not (root_present or nested_present) or not (is_num(raw) or isinstance(raw, str)):
            errs.append(f'{qid} [{r}] answer 必须为非空可判分标量，不得为 {{type,value}} 包装/空值')
        elif isinstance(raw, str) and not raw.strip():
            errs.append(f'{qid} [{r}] answer 字符串不得为空')
        if root_present and nested_present and q['answer'] != content['answer']:
            errs.append(f'{qid} [{r}] 顶层 answer 与 content.answer 冲突')

        # R2: 找零数值关系。
        if r == 'money-board' and isinstance(cfg.get('target'), dict):
            t = cfg['target']
            if 'paid' in t and 'price' in t:
                if not all(is_num(v) for v in (t['paid'], t['price'])) or not is_num(a):
                    errs.append(f'{qid} money-board: 找零题 paid/price/answer 必须为数值')
                elif t['paid'] - t['price'] != a:
                    errs.append(f"{qid} money-board: paid-price={t['paid'] - t['price']} ≠ answer={a}")

        # R3: 两端坐标各查一次；只有 start→target 进行一次路线计算，禁止 start→start 自比较。
        if r == 'direction-grid':
            grid = cfg.get('grid') or {}
            if not isinstance(grid, dict):
                grid = {}
            rows, cols = grid.get('rows'), grid.get('cols')
            if not (isinstance(rows, int) and not isinstance(rows, bool) and rows > 0 and isinstance(cols, int) and not isinstance(cols, bool) and cols > 0):
                errs.append(f'{qid} direction-grid: grid.rows/cols 必须为正整数')
            start, target = coord(cfg, 'start'), coord(cfg, 'target')
            for side, c in (('start', start), ('target', target)):
                if c is None or not all(isinstance(v, int) and not isinstance(v, bool) for v in c):
                    errs.append(f'{qid} direction-grid: {side} 坐标缺失/非整数')
                    continue
                rr, cc = c
                if rr < 0 or cc < 0:
                    errs.append(f'{qid} direction-grid: {side} 坐标负值（须 0 起）')
                elif isinstance(rows, int) and isinstance(cols, int) and (rr >= rows or cc >= cols):
                    errs.append(f'{qid} direction-grid: {side}={rr},{cc} 越界 {rows}x{cols}（疑 1 起坐标）')
            if start is not None and target is not None and None not in start + target:
                if start[0] == target[0] or start[1] == target[1]:
                    errs.append(f'{qid} direction-grid: 起点到终点为纯直线路线（dr 或 dc=0）')
                if not is_num(a):
                    errs.append(f'{qid} direction-grid: 终点格编码答案必须为数值标量')
                elif isinstance(cols, int) and cols > 0 and all(isinstance(v, int) for v in target):
                    want = target[0] * cols + target[1]
                    if want != a:
                        errs.append(f'{qid} direction-grid: answer={a} ≠ 终点格编码 {want}')

        # R4: 时刻两档；错误输入应输出 FAIL 而不是异常退出。
        if r == 'clock':
            start = cfg.get('start') or {}
            sv = minute_value(start)
            tv = minute_value(cfg.get('target'))
            for label, v in (('start', sv), ('target', tv)):
                if v not in (0, 30):
                    errs.append(f'{qid} clock: {label} 分针 {v} 非整/半点（或缺失/格式错误）')

        # R5: 整除关系。
        if r == 'grouping-board':
            gs = cfg.get('group_size', cfg.get('groupSize'))
            total = cfg.get('total')
            if isinstance(gs, int) and gs > 0 and is_num(total) and float(total) % gs != 0:
                errs.append(f'{qid} grouping-board: total={total} 不能被 group_size={gs} 整除')

        # R6: token 拼接答案不能为单个多位数整型。
        if r == 'pattern-board' and isinstance(a, int) and not isinstance(a, bool) and a >= 10:
            errs.append(f'{qid} pattern-board: 答案 {a} 为多位整型，无法按个位 token 无歧义拼接')

        # R7: 滑条上限≤60 且目标±容差不能触及/超出上下边界。
        if r == 'estimation-canvas':
            mx, mn, tol = cfg.get('max'), cfg.get('min', 0), cfg.get('tolerance')
            target = cfg.get('target', a)
            if not (is_num(mx) and 0 < mx <= 60):
                errs.append(f'{qid} estimation-canvas: max 必填且应在 (0,60]')
            if not (is_num(mn) and is_num(mx) and mn < mx):
                errs.append(f'{qid} estimation-canvas: min/max 值域不合法')
            if not (is_num(tol) and tol > 0):
                errs.append(f'{qid} estimation-canvas: tolerance 缺失或非正')
            elif all(is_num(v) for v in (mx, mn, target)):
                if target - tol <= mn or target + tol >= mx:
                    errs.append(f'{qid} estimation-canvas: 目标 {target}±{tol} 贴/超滑条边界 [{mn},{mx}]')

        # R8: context_family 必填且不得越表。
        cf = q.get('context_family')
        if cf not in VOCAB_FAMILY:
            errs.append(f"{qid}: context_family '{cf}' 缺失或越出受控词表")
    return errs


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    try:
        data = json.loads(Path(argv[1]).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        print(f'输入文件读取/JSON 解析失败：{exc}', file=sys.stderr)
        return 2
    questions = data.get('questions') if isinstance(data, dict) else data
    if not isinstance(questions, list):
        print('输入格式错误：需为题目列表或含 questions 键', file=sys.stderr)
        return 2
    errors = audit(questions)
    print(f'审计 {len(questions)} 题，违规 {len(errors)} 条')
    for error in errors:
        print('  FAIL:', error)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
