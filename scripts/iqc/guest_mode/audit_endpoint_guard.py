"""对外暴露端点的鉴权覆盖审计（游客模式）。

口径演进（三轮踩过的坑，写下来避免重复）：
  v1 按 app/api/*.py 源码扫描 → 抽出 25 个端点，但 curriculum / hint 从未注册，
     不是对外端点。5 个 MISS 里 2 个是纯噪音。**源码 ≠ 对外暴露**。
  v2 按 app.routes 枚举 → fastapi 0.141.1 用 _IncludedRouter 延迟包含，
     .routes 上只有 7 项、子路由不展开，只抽出 1 个端点。**载体 ≠ 内容**。
  v3（本脚本）双事实源交叉校验：
       (a) app.openapi()["paths"] —— 运行时真实对外承诺的路径集合；
       (b) 递归 original_router 拿叶子 APIRoute 的 dependant —— 依赖树。
     两者必须一致（判据 E）。任一解析漏项都会让 PASS 失去意义。

判据：
  A. 每个对外端点，依赖树里必须出现 require_guest
  B. 例外须在 EXEMPT 显式登记理由；未登记 = FAIL
  C. EXEMPT 每项必须命中真实路径（防名单写错 → 空跑，形态 32）
  D. EXEMPT 不得覆盖已带 require_guest 的端点（防豁免掩盖已实现）
  E. OpenAPI 与路由解析两个事实源必须一致（防解析漏项却报 PASS）

退出码：0 = 全通过；1 = 判据失败；2 = 解析失效（环境问题）。

用法：
    ~/.workbuddy/binaries/python/envs/learning-engine/bin/python scripts/iqc/guest_mode/audit_endpoint_guard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "apps" / "learning-api"))

# 允许不带 require_guest 的对外端点：理由必须写清楚"为什么不需要身份"。
EXEMPT = {
    "/": "根路由：仅回服务名与 ok，无业务语义",
    "/health": "存活探针：编排/负载均衡要求无凭据可访问",
    "/health/db": "探针：仅回 DB 可达性布尔，不含任何业务数据",
    "/v1/content/v2-catalog": "只读资源目录：无 child 维度数据，无归属可校验",
    "/v1/diagnosis/": "无状态纯函数（入参→诊断码），不读不写任何 child 数据",
    "/v1/guest/bootstrap": "游客身份唯一入口：此刻尚无 Cookie，要求鉴权即死循环",
    "/v1/guest/logout": "登出须容错无会话调用（幂等），否则过期 Cookie 清不掉",
    "/v1/guest/qa-session": "E2E 取票口；鉴权由 selection_trace_enabled 开关 + QA_CHILD 判定承担",
    "/v1/guest/admin/cleanup": "运维口；鉴权由 selection_trace_enabled 开关承担（关闭即 404）",
    "/v1/guest/admin/cleanup-runs": "运维口；同上",
}

SKIP = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


def walk_apiroutes(routes, base: str = ""):
    """递归展开路由树，产出 (full_path, methods, route)。

    路径拼接的易错点：叶子 APIRoute.path **已包含**中间层 router 自己的 prefix
    （guest.router(prefix="/guest") 下叶子就是 "/guest/bootstrap"）。所以嵌套层
    不能再累加前缀，否则得到 /v1/guest/guest/bootstrap。只有最外层 include 的
    prefix 需要补——由调用方作为 base 传入。
    """
    for r in routes:
        orig = getattr(r, "original_router", None)
        if orig is not None:
            yield from walk_apiroutes(getattr(orig, "routes", []) or [], base)
            continue
        sub = getattr(r, "routes", None)
        if sub is not None:
            yield from walk_apiroutes(sub, base)
            continue
        p = getattr(r, "path", None)
        if p is not None:
            yield (base + p) or "/", sorted(getattr(r, "methods", None) or []), r


def has_guest(dependant, depth: int = 0) -> bool:
    if dependant is None or depth > 25:
        return False
    if getattr(getattr(dependant, "call", None), "__name__", "") == "require_guest":
        return True
    return any(has_guest(s, depth + 1) for s in (getattr(dependant, "dependencies", []) or []))


def main() -> int:
    from app.main import app

    spec_paths = set(app.openapi().get("paths", {}))
    if not spec_paths:
        print("[rc=2] OpenAPI 无任何路径——解析失效，不能当成「没有端点」")
        return 2

    route_map: dict[str, dict] = {}
    for top in app.routes:
        top_base = ""
        orig = getattr(top, "original_router", None)
        if orig is not None:
            ctx = getattr(top, "include_context", None)
            top_base = (getattr(ctx, "prefix", "") or "") + (getattr(orig, "prefix", "") or "")
        for path, methods, r in walk_apiroutes([top], top_base):
            if path in SKIP:
                continue
            for m in methods:
                if m in ("HEAD", "OPTIONS"):
                    continue
                route_map.setdefault(path, {})[m] = {
                    "func": getattr(getattr(r, "endpoint", None), "__name__", "?"),
                    "guarded": has_guest(getattr(r, "dependant", None)),
                }

    fails: list[str] = []
    only_spec = sorted(spec_paths - set(route_map))
    only_route = sorted(set(route_map) - spec_paths)
    if only_spec:
        fails.append(f"E OpenAPI 有但解析未找到（漏项）：{only_spec}")
    if only_route:
        fails.append(f"E 解析有但 OpenAPI 没有：{only_route}")
    print(f"E 两事实源一致（OpenAPI {len(spec_paths)} / 解析 {len(route_map)}）："
          f"{'PASS' if not only_spec and not only_route else 'FAIL'}")

    rows = [
        {"method": m, "path": p, **info}
        for p in sorted(spec_paths)
        for m, info in sorted(route_map.get(p, {}).items())
    ]
    print(f"\n对外暴露端点 {len(rows)} 个")
    print("=" * 88)
    print(f"{'方法':<7}{'路径':<46}{'函数':<28}{'鉴权'}")
    print("-" * 88)

    guarded = 0
    for r in rows:
        if r["guarded"]:
            mark, guarded = "OK", guarded + 1
        elif r["path"] in EXEMPT:
            mark = "EXEMPT"
        else:
            mark = "MISS"
            fails.append(f"A 未鉴权且未登记豁免：{r['method']} {r['path']} → {r['func']}")
        print(f"{r['method']:<7}{r['path']:<46}{r['func']:<28}{mark}")

    print("=" * 88)
    print(f"带 require_guest：{guarded} / {len(rows)}；豁免登记：{len(EXEMPT)}")

    live = {r["path"] for r in rows}
    stale = sorted(p for p in EXEMPT if p not in live)
    if stale:
        fails.append(f"C 豁免名单含不存在路径（名单失效）：{stale}")
    print(f"C 豁免名单全部命中真实路径：{'PASS' if not stale else 'FAIL'}")

    overlap = sorted({r["path"] for r in rows if r["guarded"]} & set(EXEMPT))
    if overlap:
        fails.append(f"D 已带鉴权却仍登记豁免（豁免掩盖实现）：{overlap}")
    print(f"D 豁免未掩盖已鉴权端点：{'PASS' if not overlap else 'FAIL'}")

    print("=" * 88)
    if fails:
        print(f"结论：FAIL（{len(fails)} 项）")
        for f in fails:
            print("  - " + f)
        return 1
    print("结论：PASS（对外端点要么带 require_guest，要么理由已登记）")
    return 0


if __name__ == "__main__":
    sys.exit(main())