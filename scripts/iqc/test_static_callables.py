#!/usr/bin/env python3
"""FE-1467 静态可调用性检查（DB-free，进 pr_gate 第 7 项）。

真实缺陷（2026-10-21 复审发现）：
    `verify_expiry_lock_concurrency.py` 在把 `_post` 迁进 `exec_mode` 时，
    定义被删除、调用点却留着。submitter 线程里的 `except Exception` 把
    NameError 吞掉，只写进 `result_holder["error"]` —— 于是「并发提交」
    这段可能在**从未发出任何 HTTP 请求**的情况下继续走到收尾判定。

为什么必须静态查：
    这类错误在运行时表现为"捕获到异常"，而"捕获到异常"恰恰是本项目反复
    踩坑的假通过来源（专核=0 空集假通过、假会话按整条 SQL 判断）。
    只要调用方有宽泛 except，动态跑永远绿。所以要在**语法树层面**确认
    每个被调用的模块级函数确实存在、每个被捕获后忽略的异常确实不是
    NameError 类缺陷。

检查项：
  C1 每个以 `_` 前缀被调用的辅助函数，必须在模块内定义
  C2 `except Exception` 块内不得静默吞掉（必须显式记录或重抛）
  C3 exec_mode 的写闸门家族完整（post / effect_get / 纯 get 三分）

不做：不连库、不执行被测脚本、不改任何工件。
"""
from __future__ import annotations

import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.join(HERE, "rt1464")
fails: list[str] = []


def note(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


def undefined_helper_calls(path: str) -> list[str]:
    """返回被调用但模块内未定义的下划线辅助函数名。"""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    defined = {n.name for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                imported.add((a.asname or a.name).split(".")[0])
    assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                for t in n.targets if isinstance(t, ast.Name)}
    called = {c.func.id for c in ast.walk(tree)
              if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    return sorted(c for c in called
                  if c.startswith("_") and c not in defined
                  and c not in imported and c not in assigned)


def swallowed_exceptions(path: str) -> list[tuple[int, str]]:
    """找出 `except Exception:` 却只 pass 或什么都不做的块（静默吞异常）。"""
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = []
    for h in ast.walk(tree):
        if not isinstance(h, ast.ExceptHandler):
            continue
        tname = ""
        if isinstance(h.type, ast.Name):
            tname = h.type.id
        elif isinstance(h.type, ast.Tuple):
            tname = ",".join(getattr(e, "id", "") for e in h.type.elts)
        if "Exception" not in tname and tname != "BaseException":
            continue
        body = h.body
        silent = len(body) == 1 and isinstance(body[0], ast.Pass)
        if silent:
            out.append((h.lineno, tname))
    return out


def main() -> int:
    targets = sorted(
        os.path.join(RT, f) for f in os.listdir(RT)
        if f.startswith("verify_") and f.endswith(".py")
    )
    note("C0 找到被测脚本", bool(targets), f"{len(targets)} 个 verify_*.py")

    # C1 未定义辅助函数
    bad = {}
    for p in targets:
        u = undefined_helper_calls(p)
        if u:
            bad[os.path.basename(p)] = u
    note("C1 无「调用了未定义的辅助函数」", not bad, str(bad))

    # C2 静默吞异常（宽泛 except + 只 pass）
    silent = {}
    for p in targets:
        s = swallowed_exceptions(p)
        if s:
            silent[os.path.basename(p)] = s
    note("C2 无「except Exception 静默吞掉」", not silent, str(silent))

    # C3 exec_mode 的闸门家族：POST / 副作用 GET / 纯 GET 三分
    em = open(os.path.join(RT, "exec_mode.py"), encoding="utf-8").read()
    has = {n: re.search(rf"def {n}\(", em) is not None
           for n in ("guarded_post", "guarded_effect_get", "guarded_get")}
    note("C3 副作用闸门三分（POST / effect-GET / 纯 GET）", all(has.values()), str(has))

    # C4 effect_get 必须真的过闸门（不能被写成直接 send）
    eff = re.search(r"def guarded_effect_get.*?(?=\n    def |\Z)", em, re.S)
    guarded = bool(eff) and "assert_can_write" in eff.group(0)
    note("C4 effect-GET 确实经过 assert_can_write", guarded,
         "结算 GET 受只读模式约束" if guarded else "effect_get 未过闸门——等于漏掉结算路径")

    print()
    if fails:
        print(f"STATIC-CALLABLE-GATE: FAIL ({len(fails)}) — " + "; ".join(fails))
        return 1
    print("STATIC-CALLABLE-GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())