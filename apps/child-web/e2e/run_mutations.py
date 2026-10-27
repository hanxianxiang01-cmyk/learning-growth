#!/usr/bin/env python3
"""D2 spec 变异测试执行器（M1–M7）。

用途：复现 `78bbcb0` 的负对照，证明 D2 断言有区分力。
验收方可在不触碰生产库的前提下自行重跑。

用法（在 apps/child-web 目录下，且 3100 已起）：
    python run_mutations.py            # 跑基线 + 全部 M1-M7
    python run_mutations.py M4 M7      # 只跑指定变异（仍会先跑基线）
    python run_mutations.py --list     # 只看变异清单，不执行
    python run_mutations.py --log-dir ./d2_logs   # 另存每次执行原始日志

前置：
    1. 前端已起：NEXT_DIST_DIR=.next-e2e-h4 PORT=3100 npx next dev -p 3100
    2. 本脚本与 fe1472-d2-directed.spec.mjs 同目录，且会被拷到 apps/child-web/e2e/

## 判定口径（2026-10-23 验收整改后）

第一版只用 `" failed" in out` 判断成败，验收方指出这不足以证明材料——若
Playwright 根本没跑起来（配置错、浏览器缺失、端口没起），`out` 里既没有
" failed" 也没有通过的测试，会被误判成「PASS」，即把「没跑」当成「结果不变」。
这对 `PASS_SAME` 类变异（M2）尤其致命：它本来就期望结果不变，正好与崩溃同形。

现在的判定同时校验三件事，缺一不可：

  A **进程返回码** `r.returncode`：0=全通过、1=有失败、其他=基础设施错误。
     只有 0 才可能是 PASS；非 0 且 failed==0 一律判 `ERROR`（不是 PASS）。
  B **实际执行的测试数**：从 list reporter 的汇总行解析 passed/failed/flaky。
     `executed == 0` 一律判 `NOT_RUN`，**永远不可能匹配 PASS_SAME**。
  C **与未变异基线的题数比对**：先跑一次原 spec 拿到基线题数，`PASS_SAME`
     要求「执行题数 == 基线题数 且 failed==0」。这样 M2 的主张才是完整的：
     「删掉该断言后，其余 N 个测试**确实都跑了**且结果不变」。

三种实测态与期望的匹配表：

    实测态     | 含义                        | 可满足的期望
    -----------|-----------------------------|------------------
    PASS       | rc=0 且 failed=0 且真实执行 | PASS_SAME / PASS
    FAIL       | 有测试失败（rc!=0 且 failed>0）| FAIL
    ERROR      | rc!=0 但无失败测试（跑不起来）| 不可满足任何期望
    NOT_RUN    | executed==0（一条都没跑）    | 不可满足任何期望

注意（血泪教训）：
    - 变异文件必须在 `e2e/` 目录内运行，不能拷到 /tmp——playwright.config.mjs
      的 testDir 是 "./e2e"，跑到外面会因路径退级直接断言失败（假阴性）。
    - 每个变异都要求"真的改变被观察量"，不是"删掉一行断言"。
      M2 就属于反例：删断言结果不变，因为当前实现确实带该字段。
    - **变异打错目标 ≠ 检测器失效**：替换串必须唯一，`build()` 里已硬校验。
    - **M3 与 M7 曾经是同一个变异**：`captured.body = JSON.parse(...)` 在 spec 里
      只有一处（`stubBackend` 内），而 `stubBackend` 是三个用例共用的拦截器。
      改它天然覆盖所有提交，所以旧 M7 写的"M3 的更彻底版：连 H3b 一起覆盖"
      **不成立**——两者除注释外逐字相同，多算一条"符合预期"等于凑数。
      2026-10-23 已把 M7 换成独立目标（未知条上限误用 `visual.max_value`）。
    - **`test-results/` 堆积会让后续变异整条 NOT_RUN**：Playwright 每次运行前会
      清空 `test-results/`，失败用例还会写截图。跑满几轮后该目录文件数增长，
      某些环境对"一次删除大量文件"有安全拦截，于是 `npx playwright test`
      直接以非 0 退出、**一条用例都没执行**。日志里的特征串是
      `SAFE_DELETE_BULK_CONFIRM_REQUIRED`。
      这不是"测试结果不变"，判定器会正确报 `NOT_RUN`；处理办法是先手工清空
      `apps/child-web/test-results/`（该目录在 `.gitignore` 内）再重跑。
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "fe1472-d2-directed.spec.mjs")
E2E_DIR = os.path.normpath(os.path.join(HERE, "..", "e2e"))
BASE_URL = os.environ.get("E2E_WEB_BASE", "http://127.0.0.1:3100")

# 未变异基线的题数下限（仅作 sanity check；真实基线数运行时实测）
FALLBACK_BASELINE = 35

# list reporter 的汇总行：
#     35 passed (1.5m)
#      1 failed
#     34 passed (1.5m)
#      2 did not run
SUMMARY_RE = re.compile(
    r"^\s*(\d+)\s+(passed|failed|flaky|skipped|interrupted|did\s+not\s+run)\b",
    re.MULTILINE,
)

# (编号, 说明, 原文, 替换文, 期望)
# 期望 "FAIL" 表示该变异必须让测试失败（证明断言有区分力）；
# 期望 "PASS_SAME" 表示结果不变但断言数减少（说明"删断言"不构成证伪）。
MUTATIONS = [
    (
        "M1",
        "H4b 负例的 representation_required 改 false —— 闸门不应再触发",
        # **必须带唯一尾上下文**：`answer_placeholder: "输入数字"` 在 buildTask（D2 三题）
        # 与 H4b task 里都出现。若只匹配到 `"输入数字"`，replace(count=1) 会先命中
        # buildTask，H4b 根本没被改到 → 实测 PASS，误判为"断言没区分力"。
        # buildTask 后面跟的是 `,\n      visual: {`；H4b 后面直接是 `\n    }`。
        # 加 `\n    }` 使其唯一。这正演示了「变异打错目标 ≠ 检测器失效」。
        '        answer_type: "number",\n        representation_required: true\n      },\n      answer_placeholder: "输入数字"\n    }',
        '        answer_type: "number",\n        representation_required: false\n      },\n      answer_placeholder: "输入数字"\n    }',
        "FAIL",
    ),
    (
        "M2",
        "删掉 representation 显式断言 —— 故意用错误方法，看是否真能证伪",
        'expect(body.response.representation, "提交体必须携带 representation；缺失即失败（原版在此静默跳过）")\n      .toBeTruthy();',
        "",
        "PASS_SAME",
    ),
    (
        "M3",
        "拦截时 delete body.response.representation —— 让被观察量真的缺失",
        '      captured.body = JSON.parse(req.postData() ?? "{}");',
        '      captured.body = JSON.parse(req.postData() ?? "{}");\n      if (captured.body?.response) delete captured.body.response.representation; // M3',
        "FAIL",
    ),
    (
        "M4",
        "提交前不恢复正确未知量，停在 unknownMax（模拟旧版缺陷）",
        "    await setSlider(unknown, c.other);\n    const restored = await readSlider(unknown);",
        "    await setSlider(unknown, c.unknownMax); // M4\n    const restored = await readSlider(unknown);",
        "FAIL",
    ),
    (
        "M5",
        "已知条期望改成 known+1 —— 正确表征断言应拒绝",
        'expect(baseBar.value, `已知条应等于题面已知量 ${c.known}`).toBe(c.known);',
        'expect(baseBar.value, "M5").toBe(c.known + 1);',
        "FAIL",
    ),
    (
        "M6",
        "H3b 误用正确值当错误值 —— 前置断言应拒绝",
        "const WRONG_UNKNOWN = c.unknownMax; // 15，既非正确答案 7，也非合计 18",
        "const WRONG_UNKNOWN = c.other; // M6",
        "FAIL",
    ),
    (
        "M7",
        "未知条上限误用 visual.max_value —— 「滑条上限=该条 max」这条断言应拒绝",
        # 2026-10-23 改：原 M7 写的是"M3 的更彻底版：连 H3b 一起覆盖"，但实测
        # `captured.body = JSON.parse(...)` 在 spec 里**只有一处**（stubBackend 内），
        # 而 stubBackend 是三个用例共用的拦截器——改它本来就覆盖所有提交。
        # 所以原 M3 与 M7 除注释外完全相同，是两个同一变异的副本，
        # 「M7 更彻底」不成立，多算一条符合预期属于凑数。
        # 现换成真正独立的一条：验证 spec 是否真的断言了
        # 「未知条滑条上限 = 该条自己的 max（unknownMax），不是 visual.max_value」。
        # 这与 DEF-D2-NUM-DEADCFG 的结论直接相关（max_value 不进滑条上限）。
        '{ id: "unknown", label: "未知", min: 0, max: c.unknownMax, unknown: true }',
        '{ id: "unknown", label: "未知", min: 0, max: c.maxValue, unknown: true }',
        "FAIL",
    ),
]


def list_mutations():
    for mid, desc, _a, _b, expect in MUTATIONS:
        print(f"  {mid}: {desc}  [期望 {expect}]")


def parse_stats(out: str) -> dict:
    """从 list reporter 输出里解析汇总计数。解析不到就是 {}（→ executed=0 → NOT_RUN）。"""
    stats: dict[str, int] = {}
    for n, kind in SUMMARY_RE.findall(out):
        kind = " ".join(kind.split())
        stats[kind] = stats.get(kind, 0) + int(n)
    return stats


def classify(r, stats: dict) -> tuple[str, dict]:
    """把一次执行归入 PASS / FAIL / ERROR / NOT_RUN，并返回明细计数。

    关键区分（离线自测踩到过）：`skipped` 与 `did not run` **不是执行证据**。
    第一版把 executed 算成 passed+failed+flaky+skipped+did_not_run，于是
    「2 did not run」被判成 ERROR——但语义上它是 NOT_RUN：一条都没真跑。
    现在 `ran` 只数 passed/failed/flaky，`skipped`/`did_not_run` 单独记录。
    """
    passed = stats.get("passed", 0)
    failed = stats.get("failed", 0)
    flaky = stats.get("flaky", 0)
    skipped = stats.get("skipped", 0)
    did_not_run = stats.get("did not run", 0)
    ran = passed + failed + flaky          # 真正跑出结果的测试数
    detail = {
        "rc": r.returncode, "passed": passed, "failed": failed,
        "flaky": flaky, "skipped": skipped, "did_not_run": did_not_run,
        "ran": ran, "executed": ran + skipped + did_not_run,
    }
    # 一条都没真正跑出结果：无论 rc 是什么，都不能当作"结果不变"
    if ran == 0:
        return "NOT_RUN", detail
    if failed > 0:
        return "FAIL", detail
    if r.returncode != 0:
        # 有测试执行、无失败测试，但进程非 0 → 跑不起来/配置错/超时，属基础设施错误
        return "ERROR", detail
    return "PASS", detail


def build(mid, old, new, src_text):
    """构造变异，并强制检查**命中唯一性**。

    为什么必须查唯一：若替换串在 spec 里出现多处，`replace(count=1)` 会命中
    第一处而不是我们想改的地方，变异实际没生效，测试仍 PASS——此时很容易
    误判成"断言没有区分力"，去放宽判据。**这是变异构造错误，不是检测器失效。**
    （本项目第三次踩同类：M1 曾因 `answer_placeholder: "输入数字"` 在 D2 与 H4b
    两处都出现，实际改的是 buildTask，H4b 未被改动。）
    """
    hits = src_text.count(old)
    if hits == 0:
        raise SystemExit(f"**{mid} 变异未命中**：原文片段在 spec 中找不到，说明 spec 已变更，需更新变异定义")
    if hits > 1:
        raise SystemExit(
            f"**{mid} 变异命中 {hits} 处，拒绝执行**：替换串不唯一，"
            f"replace(count=1) 会改错位置导致假阴性。请加唯一上下文后再试。"
        )
    return src_text.replace(old, new, 1)


def _run_file(path_in_e2e: str, log_path: str | None):
    env = dict(os.environ, E2E_WEB_BASE=BASE_URL)
    r = subprocess.run(
        ["npx", "playwright", "test", path_in_e2e,
         "--project=chrome-system", "--reporter=list"],
        cwd=os.path.normpath(os.path.join(E2E_DIR, "..")),
        env=env, capture_output=True, text=True,
    )
    out = r.stdout + r.stderr
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"$ npx playwright test {path_in_e2e} --project=chrome-system --reporter=list\n")
            f.write(f"# returncode = {r.returncode}\n\n")
            f.write(out)
    return r, out


def get_baseline(log_dir: str | None) -> int | None:
    """跑一次未变异 spec，拿到基线执行题数。拿不到返回 None。"""
    log = os.path.join(log_dir, "baseline.log") if log_dir else None
    r, out = _run_file("e2e/fe1472-d2-directed.spec.mjs", log)
    kind, detail = classify(r, parse_stats(out))
    print(f"  基线：rc={detail['rc']} 执行={detail['ran']} "
          f"passed={detail['passed']} failed={detail['failed']} → {kind}")
    if kind != "PASS":
        print("  ✗ 基线本身不通过／没跑起来，无法作为 PASS_SAME 的对照基准。")
        return None
    return detail["passed"]


def run_one(mid, desc, old, new, expect, src_text, baseline, log_dir):
    mutated = build(mid, old, new, src_text)
    # 必须在 e2e/ 内运行（playwright.config.mjs 的 testDir 是 ./e2e）
    path = os.path.join(E2E_DIR, f"mut-{mid}.spec.mjs")
    with open(path, "w", encoding="utf-8") as f:
        f.write(mutated)
    try:
        log = os.path.join(log_dir, f"mut-{mid}.log") if log_dir else None
        r, out = _run_file(f"e2e/mut-{mid}.spec.mjs", log)
        actual, d = classify(r, parse_stats(out))

        # 期望匹配：三态严格分开，NOT_RUN / ERROR 永不通过
        if expect == "PASS_SAME":
            ok = (actual == "PASS" and baseline is not None
                  and d["passed"] == baseline and d["failed"] == 0)
            why = ("基线题数=" + str(baseline))
        elif expect in ("FAIL", "PASS"):
            ok = actual == expect and d["ran"] > 0
            why = ""
        else:
            ok = False
            why = f"未知期望 {expect}"

        mark = "✓" if ok else "✗"
        print(f"{mark} {mid}  期望={expect}  实测={actual}  "
              f"[rc={d['rc']} 执行={d['ran']} passed={d['passed']} "
              f"failed={d['failed']}]  {desc}")
        if not ok:
            if actual in ("NOT_RUN", "ERROR"):
                print(f"      **未取得证据**：实测={actual}，"
                      f"rc={d['rc']} 真正执行题数={d['ran']}"
                      f"（skipped={d['skipped']} did_not_run={d['did_not_run']}）。"
                      f"这表示测试没真正跑起来，不能读作「结果不变」。")
            elif expect == "PASS_SAME" and baseline is not None and d["passed"] != baseline:
                print(f"      **题数不符**：基线 {baseline} 题、本次 {d['passed']} 题通过，"
                      f"不能主张「其余测试都跑了且结果不变」。")
            else:
                print(f"      {why}")
        # 摘出 Expected/Received 便于人工核对
        keys = [l.strip() for l in out.splitlines()
                if l.strip().startswith(("Expected:", "Received:", "Error:"))][:6]
        for k in keys:
            print(f"      {k}")
        return ok, actual, d
    finally:
        # 收尾必删：变异产物留在仓库里会污染下一轮。
        # 2026-10-23 实测踩到：本轮 M7 的 mut-M7.spec.mjs 因为删除动作被环境
        # 安全策略拦下而残留（日志里出现 SAFE_DELETE_BULK_CONFIRM_REQUIRED），
        # 但脚本当时**静默吞掉**了——于是 `git status` 里多出一个未跟踪文件，
        # 下一轮 `mut-M7` 会被 Playwright 一并当成正式用例收集。
        # 修法：删不掉就明确报出来，不假装收尾成功。
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as e:
            print(f"      **收尾失败**：无法删除 {path}（{e}）——"
                  f"请手工删除，否则会污染下一轮的用例收集。")


def selftest() -> int:
    """判定器自证：不需要浏览器、不需要前端，纯离线合成输出。

    为什么必须有这一层：验收方的意见是「M2 证据偏弱」。若只改代码不做自证，
    下一个人还是只能相信"我这次跑过了"。这里把七种典型输出固化成用例，
    并对**同一条输出**同时跑新判定与旧判定（`' failed' in out`），
    把"旧逻辑会把没跑读成 PASS"直接打印出来当证据。
    """
    class R:
        def __init__(self, rc):
            self.returncode = rc

    cases = [
        ("真通过（35 passed, rc=0）", 0, "  35 passed (1.5m)\n", "PASS"),
        ("真失败（34 passed + 1 failed, rc=1）", 1,
         "  34 passed (1.5m)\n  1 failed\n", "FAIL"),
        ("浏览器缺失（rc=1，无任何计数）", 1,
         "Error: browserType.launch: Executable doesn't exist at ...\n", "NOT_RUN"),
        ("配置错（只有 2 did not run）", 1, "  2 did not run\n", "NOT_RUN"),
        ("全部 skipped（0 条真跑）", 0, "  2 skipped\n", "NOT_RUN"),
        ("rc=2 但测试执行了（异常退出）", 2, "  35 passed (1.5m)\n", "ERROR"),
        ("空输出 + rc=0（旧逻辑判 PASS）", 0, "", "NOT_RUN"),
        ("空输出 + rc=1", 1, "", "NOT_RUN"),
    ]

    def old_logic(rc, out):
        """2026-10-23 之前的判定，留着当反例。"""
        failed = " failed" in out and " 0 failed" not in out
        return "FAIL" if failed else "PASS"

    print("── 变异结果判定器自证（离线，无需浏览器）──")
    bad = 0
    old_wrong = 0
    for name, rc, out, want in cases:
        kind, d = classify(R(rc), parse_stats(out))
        ok = kind == want
        bad += 0 if ok else 1
        old = old_logic(rc, out)
        old_bad = old != want and not (want == "PASS" and old == "PASS")
        if old_bad:
            old_wrong += 1
        print(f"  {'✓' if ok else '✗'} {name:<34} 新={kind:<8} 旧={old:<5} "
              f"正确={want}" + ("" if ok else "   ← 新判定错误"))
        if old_bad:
            print(f"       ↑ 旧判定把「{name}」误读为 {old}，"
                  f"这正是验收方指出的 M2 证据偏弱点")
    print(f"\n 旧判定在这 {len(cases)} 种输入上错了 {old_wrong} 次；新判定错 {bad} 次")
    print(f"MUTATION-CLASSIFIER-SELFTEST: {'PASS' if bad == 0 else 'FAIL'}")
    return 0 if bad == 0 else 1


def main():
    argv = [a for a in sys.argv[1:] if a != "--list"]
    log_dir = None
    if "--log-dir" in argv:
        i = argv.index("--log-dir")
        log_dir = argv[i + 1] if i + 1 < len(argv) else None
        del argv[i:i + 2]
    no_baseline = "--no-baseline" in argv
    argv = [a for a in argv if a != "--no-baseline"]

    if "--list" in sys.argv:
        print("可用变异：")
        list_mutations()
        return 0
    if "--selftest" in sys.argv:
        return selftest()
    if not os.path.exists(SPEC):
        raise SystemExit(f"找不到 spec：{SPEC}")
    if not os.path.isdir(E2E_DIR):
        raise SystemExit(f"找不到 e2e 目录：{E2E_DIR}（本脚本须放在 apps/child-web/e2e/ 旁）")
    src = open(SPEC, encoding="utf-8").read()

    print("== D2 变异测试 ==")
    print(f"spec = {SPEC}")
    print(f"base = {BASE_URL}")
    if log_dir:
        print(f"log  = {os.path.abspath(log_dir)}")
    print()
    # **基线之前**先清残留：残留会让 baseline 把变异用例一起收集，
    # 题数虚高，PASS_SAME 的「题数相等」判据随之失真。
    stale = [f for f in os.listdir(E2E_DIR)
             if f.startswith("mut-") and f.endswith(".spec.mjs")]
    if stale:
        print(f"  ⚠ 发现上一轮残留的变异文件 {len(stale)} 个：{stale}")
        for f in stale:
            try:
                os.remove(os.path.join(E2E_DIR, f))
                print(f"    已删除 {f}")
            except OSError as e:
                raise SystemExit(f"**无法删除残留 {f}（{e}），拒绝继续**："
                                 f"残留会让基线题数失真。请手工删除后重跑。")
        print()

    # 基线：PASS_SAME 必须与它对比题数，否则"没跑"会被当成"结果不变"
    if no_baseline:
        baseline = FALLBACK_BASELINE
        print(f"  基线：--no-baseline，使用声明值 {baseline} 题"
              f"（**未实测，证据力弱于默认模式**）")
    else:
        baseline = get_baseline(log_dir)
        if baseline is None and any(m[4] == "PASS_SAME"
                                    for m in MUTATIONS if not argv or m[0] in argv):
            print("\n基线不可用，PASS_SAME 类变异无法取得证据 —— 不继续执行。")
            print("\nMUTATION: 0/0 符合预期（基线未建立）")
            return 2
    print()

    picks = [m for m in MUTATIONS if not argv or m[0] in argv]
    rows = [run_one(m[0], m[1], m[2], m[3], m[4], src, baseline, log_dir) for m in picks]
    oks = [r[0] for r in rows]
    total, ok = len(oks), sum(oks)
    not_run = [m[0] for (m, r) in zip(picks, rows) if r[1] in ("NOT_RUN", "ERROR")]
    print(f"\nMUTATION: {ok}/{total} 符合预期")
    if not_run:
        print(f"未取得证据的变异：{not_run}（测试未真正执行，结果不可读作「不变」）")
    return 0 if ok == total and total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())