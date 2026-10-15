import re
def parse_num(s):
    try:
        return float(s)
    except Exception:
        return None
HINT_RE = {}

def parse_num(s):
    try:
        return float(s)
    except Exception:
        return None


def recompute(rend, ct):
    """返回 (method, recomputed_or_note)。method∈{recompute, rule, signoff}"""
    stem = ct.get('stem') or ''
    ans = ct.get('answer')
    # --- 纯算术可重算类 ---
    if rend in ('number-input', 'formula-board'):
        # a+b= / a-b= 直算
        m = re.search(r'=((?:\d+\s*[+＋]\s*)+)(\d+)\s*=', stem) or re.search(r'^((?:\d+\s*[+＋]\s*)+\d+)\s*=', stem)
        m2 = re.search(r'((?:\d+\s*[+＋]\s*)+\d+)\s*=', stem)
        if m2:
            return 'recompute', sum(int(x) for x in re.findall(r'\d+', m2.group(1)))
        m = re.search(r'(\d+)\s*[-－]\s*(\d+)\s*=', stem)
        if m:
            return 'recompute', int(m.group(1)) - int(m.group(2))
        # □+a=b / b-a=□ / a-□=b / a□b=c 符号题
        m = re.search(r'(\d+)\s*[-－]\s*(\d+)\s*=\s*[□]', stem)
        if m:
            return 'recompute', int(m.group(1)) - int(m.group(2))
        m = re.search(r'[□]\s*\+\s*(\d+)\s*=\s*(\d+)', stem)
        if m:
            return 'recompute', int(m.group(2)) - int(m.group(1))
        m = re.search(r'(\d+)\s*[○]\s*(\d+)\s*=\s*(\d+)', stem)
        if m:
            a, b, c = map(int, m.groups())
            return 'recompute', ('减号' if a - b == c else '加号')
        m = re.search(r'(\d+)排.*每排(\d+)', stem)
        if m:
            return 'recompute', int(m.group(1)) * int(m.group(2))
        m = re.search(r'(\d+)里面有几个十', stem)
        if m:
            return 'recompute', int(m.group(1)) // 10
        m = re.search(r'(\d+)写成.*(\d+)个十和几个一', stem)
        if m:
            return 'recompute', int(m.group(1)) % 10
        return 'signoff', 'stem 模式未覆盖'
    if rend == 'grouping-board':
        m = re.search(r'(\d+)颗.*平均分给(\d+)个', stem)
        if m:
            return 'recompute', int(m.group(1)) // int(m.group(2))
        return 'signoff', '未匹配等分结构'
    if rend == 'array-board':
        m = re.search(r'每行摆(\d+)个.*共摆(\d+)行', stem)
        if m:
            return 'recompute', int(m.group(1)) * int(m.group(2))
        return 'signoff', '未匹配阵列结构'
    if rend == 'column-arithmetic':
        m = re.search(r'(\d+)\s*[-－+＋]\s*(\d+)', stem)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            return 'recompute', a - b if '-' in m.group(0) else a + b
        return 'signoff', '未匹配竖式'
    if rend == 'number-line':
        m = re.search(r'从(\d+)出发，向(左|右)每次跳(\d+)，连续跳(\d+)次', stem)
        if m:
            start, d, step, n = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
            return 'recompute', start + (n * step if d == '右' else -n * step)
        return 'signoff', '未匹配跳步结构'
    if rend == 'bar-model':
        m = re.search(r'分别放着(\d+)本和(\d+)本', stem)
        if m:
            return 'recompute', int(m.group(1)) + int(m.group(2))
        m = re.search(r'(\d+)本书.*多(\d+)本', stem)
        if m:
            return 'recompute', int(m.group(1)) + int(m.group(2))
        return 'signoff', '未匹配线段图结构'
    if rend == 'object-counter':
        m = re.search(r'左边.*?(\d+)块.*右边.*?(\d+)块', stem)
        if m:
            return 'recompute', int(m.group(1)) + int(m.group(2))
        m = re.search(r'左边(\d+)个.*右边(\d+)个', stem)
        if m:
            return 'recompute', int(m.group(1)) + int(m.group(2))
        return 'signoff', '未匹配计数结构'
    if rend == 'ten-frame':
        m = re.search(r'已有(\d+)个.*再放(\d+)个', stem)
        if m:
            return 'recompute', int(m.group(1)) + int(m.group(2))
        return 'signoff', '未匹配十格框结构'
    if rend == 'shape-canvas':
        m = re.search(r'底边(\d+)格、高(\d+)格', stem)
        if m:
            return 'recompute', int(m.group(1)) * int(m.group(2))
        return 'signoff', '未匹配面积结构'
    if rend == 'ruler':
        m = re.search(r'刻度 \*?\*?(\d+)\*?\*?，右头对着刻度 \*?\*?(\d+)', stem)
        if m:
            return 'recompute', int(m.group(2)) - int(m.group(1))
        m = re.search(r'端点在刻度(\d+)和(\d+)', stem)
        if m:
            return 'recompute', int(m.group(2)) - int(m.group(1))
        m = re.search(r'左端放在刻度(\d+)、右端放在刻度(\d+)', stem)
        if m:
            return 'recompute', int(m.group(2)) - int(m.group(1))
        return 'signoff', '未匹配刻度结构'
    if rend == 'place-value':
        m = re.search(r'位值卡片\[([\d,\s]+)\]', stem)
        if m:
            digits = [int(x) for x in m.group(1).split(',')]
            v = 0
            for dg in digits:
                v = v * 10 + dg
            return 'recompute', v
        return 'signoff', '未匹配位值结构'
    if rend == 'money-board':
        nums = re.findall(r'(\d+)角', stem)
        if '总价' in stem or '凑' in stem:
            # 两件标价求和；单件标价直接=答案
            m2 = re.search(r'标价(\d+)角，另一件标价(\d+)角', stem)
            if m2:
                return 'recompute', int(m2.group(1)) + int(m2.group(2))
            m1 = re.search(r'一支笔标价(\d+)角，一块橡皮标价(\d+)角', stem)
            if m1:
                return 'recompute', int(m1.group(1)) + int(m1.group(2))
            m3 = re.search(r'标价(\d+)角', stem)
            if m3:
                return 'recompute', int(m3.group(1))
        return 'signoff', '未匹配货币结构'
    if rend == 'clock':
        m = re.search(r'调整到(\d+)点(半)?整?', stem)
        if m:
            h = int(m.group(1)); half = bool(m.group(2))
            return 'rule', h * 60 + (30 if half else 0)
        return 'signoff', '未匹配钟面结构'
    if rend == 'direction-grid':
        m = re.search(r'\((\d+),(\d+)\)出发，到\((\d+),(\d+)\)', stem)
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            return 'rule', f'曼哈顿距离={abs(x1-x2)+abs(y1-y2)}（路径口径待确认）'
        return 'signoff', '未匹配坐标结构'
    if rend in ('estimation-canvas',):
        return 'signoff', '散点图内容未声明于 content，无法独立计数'
    if rend in ('shape-gallery',):
        return 'signoff', '图形盘卡片构成未声明于 content'
    if rend in ('pattern-board',):
        return 'signoff', '规律板空格内容/答案语义需人工定义'
    return 'signoff', f'未知 renderer {rend}'


