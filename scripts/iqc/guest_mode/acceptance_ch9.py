"""V1.4 纯游客模式 —— 方案第九章 8 项验收（真实库 + 真实 HTTP 应用层）。

授权边界（用户 10-29 18:5x 确认）：**在 h_db 继续，严格零残留**。
  - 只碰 child / guardian / learning_* / guest_* 等用户数据表
  - **绝不触碰 resource_version**（225 题正式题库）与 resource
  - 每轮造的一次性游客，验完立即物理删除
  - 结束后与基线 `output/guest_mode/db_baseline_before.json` 逐项核对

八项验收（原文，docx 第 156–163 段）：
  1 无需注册登录即可开始学习
  2 每位游客拥有独立且有效的身份
  3 服务端验证身份并隔离个人学习数据
  4 每日 30 题限制真实生效
  5 7 天数据保存与清理机制真实运行
  6 游客会话过期或失效后不能访问旧数据
  7 原有学习流程回归通过
  8 隐私说明与真实数据处理方式一致

凭据只从环境变量读（治理门禁 R2 查凭据字面量）。

用法：
    DATABASE_URL=postgresql+psycopg://user:CHANGE_ME@HOST:PORT/DB \
    ~/.workbuddy/binaries/python/envs/learning-engine/bin/python scripts/iqc/guest_mode/acceptance_ch9.py
可选：
    IQC_QUOTA_LIMIT=3      # 先用小配额验证链路（默认 30，即方案真实值）
    IQC_CLEANUP_INTERVAL=5 # lifespan 清理循环间隔秒（默认 5，便于观察到真实运行）
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
API = REPO / "apps" / "learning-api"
sys.path.insert(0, str(API))

BASELINE = REPO / "output" / "guest_mode" / "db_baseline_before.json"

QA_CHILD = uuid.UUID("00000000-0000-0000-0000-000000000099")
PUBLIC_GUEST = uuid.UUID("00000000-0000-0000-0000-000000000001")

RESULTS: list[tuple[str, bool, str]] = []


def rec(item: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((item, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {item}")
    if detail:
        print(f"        {detail}")


def banner(t: str) -> None:
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("[rc=2] 未设 DATABASE_URL（凭据只走环境变量，不落文件）")
        return 2

    quota_limit = int(os.environ.get("IQC_QUOTA_LIMIT", "30"))
    interval = int(os.environ.get("IQC_CLEANUP_INTERVAL", "5"))
    # 必须在 import app 之前设，Settings 在 import 期就实例化
    os.environ["GUEST_DAILY_TASK_LIMIT"] = str(quota_limit)
    os.environ["GUEST_CLEANUP_INTERVAL_SECONDS"] = str(interval)
    os.environ["GUEST_RETENTION_DAYS"] = "7"
    os.environ["SELECTION_TRACE_ENABLED"] = "true"

    import json

    import httpx
    from starlette.testclient import TestClient

    from app.core.config import get_settings
    from app.core.database import AsyncSessionLocal
    from app.main import app
    from app.services import guest_quota
    from app.services.guest_cleanup import purge_one_guest, run_cleanup
    from sqlalchemy import text

    get_settings.cache_clear()
    st = get_settings()
    banner("配置（本轮验收实际生效值）")
    print(f"  guest_daily_task_limit      = {st.guest_daily_task_limit}")
    print(f"  guest_retention_days        = {st.guest_retention_days}")
    print(f"  guest_quota_timezone        = {st.guest_quota_timezone}")
    print(f"  guest_cookie_secure         = {st.guest_cookie_secure}（本地 http 必须 False）")
    print(f"  guest_cleanup_enabled       = {st.guest_cleanup_enabled}")
    print(f"  cleanup interval            = {interval}s")

    if not BASELINE.exists():
        print(f"[rc=2] 基线快照缺失：{BASELINE}")
        return 2
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_child = set(base["ids"]["child"])
    base_guardian = set(base["ids"]["guardian"])

    created_children: list[uuid.UUID] = []

    def snapshot_counts() -> dict:
        """同步：全部用 psycopg 同步连接，不能在同步上下文里当 coroutine 调。"""
        import psycopg

        url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
        out = {}
        with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
            for t in (
                "child", "guardian", "learning_session", "task_instance", "attempt",
                "learning_event", "mastery_evidence", "ability_state",
                "guest_identity", "guest_session", "guest_daily_quota", "guest_cleanup_run",
            ):
                cur.execute(f"SELECT count(*) FROM {t}")
                out[t] = cur.fetchone()[0]
        return out

    counts_before = snapshot_counts()
    print("\n验收前计数:", json.dumps(counts_before, ensure_ascii=False))

    def _quota_used(child_id: str) -> int:
        """A 当日已计入配额的题数（guest_daily_quota 行数，主键幂等）。"""
        import psycopg
        u = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
        with psycopg.connect(u, autocommit=True) as cc, cc.cursor() as cu:
            cu.execute("SELECT count(*) FROM guest_daily_quota WHERE child_id=%s", (child_id,))
            return cu.fetchone()[0]

    banner("验收 1 + 2：无需注册登录即可开始学习 / 每位游客独立且有效的身份")
    with TestClient(app) as client:  # with 触发 lifespan → 清理循环真实启动
        # 游客 A：不带任何凭据，直接 bootstrap
        rA = client.post("/v1/guest/bootstrap")
        rec("1.1 POST /v1/guest/bootstrap 无需任何凭据即 200", rA.status_code == 200,
            f"status={rA.status_code}")
        if rA.status_code != 200:
            print(rA.text[:400])
            return 1
        bodyA = rA.json()
        gidA = bodyA.get("guest_id") or bodyA.get("child_id")
        print(f"        游客A id={gidA}")
        print(f"        Set-Cookie: {rA.headers.get('set-cookie','(无)')[:150]}")

        # Cookie 属性核查（HttpOnly / SameSite / Path）
        ck = rA.headers.get("set-cookie", "")
        rec("2.1 会话凭证走 HttpOnly Cookie（JS 读不到）", "httponly" in ck.lower(), ck[:120])
        rec("2.2 Cookie 带 SameSite（防 CSRF）", "samesite" in ck.lower())
        rec("2.3 明文 token 不进响应体", "token" not in json.dumps(bodyA).lower(),
            f"响应键={sorted(bodyA)}")

        # 游客 A 的身份可查
        rMe = client.get("/v1/guest/me")
        rec("2.4 GET /v1/guest/me 用 Cookie 就能取到身份（无 child_id 入参）",
            rMe.status_code == 200, f"status={rMe.status_code} body={str(rMe.json())[:160]}")

        # 游客 B：全新 client = 全新浏览器（无 Cookie）
        with TestClient(app) as clientB:
            rB = clientB.post("/v1/guest/bootstrap")
            gidB = (rB.json().get("guest_id") or rB.json().get("child_id")) if rB.status_code == 200 else None
            rec("2.5 另一浏览器 bootstrap 得到不同 id（两个 id 而非同一个）",
                rB.status_code == 200 and gidB != gidA, f"A={gidA} B={gidB}")
            if gidA:
                created_children.append(uuid.UUID(str(gidA)))
            if gidB:
                created_children.append(uuid.UUID(str(gidB)))

            # 同一浏览器重复 bootstrap 必须复用身份，不能每次都变新游客
            rA2 = client.post("/v1/guest/bootstrap")
            gidA2 = rA2.json().get("guest_id") or rA2.json().get("child_id")
            rec("2.6 同一浏览器重复 bootstrap 复用同一 id（不是每次变新游客）",
                gidA2 == gidA, f"first={gidA} second={gidA2}")

            rec("2.7 两个游客 id 都不是旧的固定公共游客 ID …0001",
                str(gidA) != str(PUBLIC_GUEST) and str(gidB) != str(PUBLIC_GUEST),
                f"A={gidA}")
            rec("2.8 两个游客 id 都不是 QA child …0099",
                str(gidA) != str(QA_CHILD) and str(gidB) != str(QA_CHILD))

            banner("验收 3：服务端验证身份并隔离个人学习数据")
            # A 开课 + 答题
            rS = client.post("/v1/learning/sessions", json={"subject": "math"})
            rec("3.1 A 能开课（POST /v1/learning/sessions）", rS.status_code in (200, 201),
                f"status={rS.status_code} body={str(rS.json())[:200]}")
            sidA = rS.json().get("session_id") if rS.status_code in (200, 201) else None

            rT = client.post("/v1/learning/tasks/next", json={"session_id": sidA, "subject": "math"})
            ok_t = rT.status_code == 200 and rT.json().get("task_instance_id")
            rec("3.2 A 能取到题（POST /v1/learning/tasks/next）", bool(ok_t),
                f"status={rT.status_code} body={str(rT.json())[:200]}")
            tidA = rT.json().get("task_instance_id") if ok_t else None

            if tidA:
                rSub = client.post("/v1/learning/attempts",
                                   json={"task_instance_id": tidA, "attempt_no": 1, "response": {}})
                rec("3.3 A 能提交作答", rSub.status_code == 200,
                    f"status={rSub.status_code} body={str(rSub.json())[:160]}")

            # B 用 A 的 session_id → 必须拒（404 而非 403，不给枚举能力）
            if sidA:
                rX = clientB.post("/v1/learning/tasks/next", json={"session_id": sidA, "subject": "math"})
                rec("3.4 B 拿 A 的 session_id 取题被拒（404，不泄露该 id 存在）",
                    rX.status_code == 404, f"status={rX.status_code} body={rX.text[:160]}")

                rR = clientB.get(f"/v1/learning/sessions/{sidA}/result")
                rec("3.5 B 读 A 的 session 结果被拒（404）", rR.status_code == 404,
                    f"status={rR.status_code}")

            # B 用 A 的 task_instance_id 提交 → 必须拒
            if tidA:
                rXA = clientB.post("/v1/learning/attempts",
                                   json={"task_instance_id": tidA, "attempt_no": 1, "response": {}})
                rec("3.6 B 往 A 的 task 写答案被拒（404）", rXA.status_code == 404,
                    f"status={rXA.status_code} body={rXA.text[:160]}")

            # 请求体里塞别人的 child_id → 必须拒
            rClaim = clientB.post("/v1/learning/sessions",
                                  json={"subject": "math", "child_id": str(gidA)})
            rec("3.7 B 在 body 里冒用 A 的 child_id 开课被拒（404）",
                rClaim.status_code == 404, f"status={rClaim.status_code} body={rClaim.text[:160]}")

            # 无 Cookie 直接访问 → 401
            with TestClient(app) as anon:
                r401 = anon.post("/v1/learning/sessions", json={"subject": "math"})
                rec("3.8 无 Cookie 访问业务端点被拒（401）", r401.status_code == 401,
                    f"status={r401.status_code}")

            # 各自的记录互不可见
            if sidA:
                rOwn = client.get(f"/v1/learning/sessions/{sidA}/result")
                rec("3.9 A 自己仍能读自己的 session（隔离未误伤本人）",
                    rOwn.status_code == 200, f"status={rOwn.status_code}")

            banner(f"验收 4：每日 {quota_limit} 题限制真实生效")
            # **不清台账**：3.3 节替 A 提交的那一题（tidA）应当继续算数——
            # 它正是 4.4 需要的「已计过账的老题」。清掉会让 4.4 变成假验证
            # （拿一道没计过账的题去测「老题放行」，配额本就该拒它）。
            # 4.1 改为断言「累计达到上限」，而不是「本循环成功 N 题」。
            used_before = _quota_used(str(gidA))
            print(f"        循环前 A 已计入 {used_before} 题（来自 3.3 节）")
            used = 0
            denied = None
            # 复用 A 的 session，连续取题+提交直到被拒
            for i in range(quota_limit + 3):
                rTi = client.post("/v1/learning/tasks/next", json={"session_id": sidA, "subject": "math"})
                if rTi.status_code != 200:
                    print(f"        第 {i+1} 次取题失败 status={rTi.status_code} {rTi.text[:120]}")
                    break
                tid = rTi.json().get("task_instance_id")
                if not tid:
                    print(f"        第 {i+1} 次取题没返回 task_instance_id：{str(rTi.json())[:160]}")
                    break
                rS2 = client.post("/v1/learning/attempts",
                                  json={"task_instance_id": tid, "attempt_no": 1, "response": {}})
                if rS2.status_code == 429:
                    denied = rS2
                    print(f"        第 {i+1} 次提交被拒 429，本循环成功 {used} 题")
                    break
                if rS2.status_code != 200:
                    print(f"        第 {i+1} 次提交异常 status={rS2.status_code} {rS2.text[:150]}")
                    break
                used += 1
            total_used = used_before + used
            rec(f"4.1 累计恰好 {quota_limit} 题后触发 429（不多不少）",
                total_used == quota_limit and denied is not None,
                f"循环前 {used_before} + 本循环 {used} = {total_used}（上限 {quota_limit}），"
                f"429={'已触发' if denied else '未触发'}")
            if denied is not None:
                d = denied.json()
                det = d.get("detail", {})
                rec("4.2 429 带业务码 LE-4291（前端可据此显示提示）",
                    isinstance(det, dict) and det.get("code") == "LE-4291",
                    f"detail={str(det)[:200]}")
                rec("4.3 429 响应含配额摘要（used/limit，可解释）",
                    isinstance(det, dict) and "quota" in det,
                    f"quota={str(det.get('quota'))[:160]}")
                # 4.5 文案里的题数必须与配置同源（曾硬编码「30」，配额改小就说谎）
                q = det.get("quota") or {}
                msg = det.get("message", "")
                rec("4.5 429 提示语中的题数 == quota.limit（文案与配置同源）",
                    str(q.get("limit")) in msg, f"message={msg!r} limit={q.get('limit')}")

            # 同一题重试不应被配额误拒（判定顺序：先看是不是老题）
            if tidA:
                rRetry = client.post("/v1/learning/attempts",
                                     json={"task_instance_id": tidA, "attempt_no": 9, "response": {}})
                rec("4.4 已满配额时，重做「已计过的老题」不被 429 误拒",
                    rRetry.status_code != 429,
                    f"status={rRetry.status_code}（老题应放行或走判分，不是配额拒绝）")

            banner("验收 5：7 天数据保存与清理机制真实运行")
            # lifespan 的清理循环应已按 interval 跑过（guest_cleanup_run 有行）
            time.sleep(interval + 3)
            runs = snapshot_counts().get("guest_cleanup_run", 0)
            rec("5.1 lifespan 清理循环真实运行过（guest_cleanup_run 有运行记录行）",
                runs > counts_before.get("guest_cleanup_run", 0),
                f"验收前 {counts_before.get('guest_cleanup_run',0)} 行 → 现在 {runs} 行")

            # 造一个「已过期」的游客（expires_at 在过去），验证真被清掉
            import asyncio

            async def mk_expired() -> uuid.UUID:
                from app.services.guest import create_guest
                async with AsyncSessionLocal() as db:
                    ident, _tok = await create_guest(db, retention_days=7)
                    cid = ident.child_id
                    # 直接把 expires_at 推到 1 天前（created_at 也推，满足 CHECK）
                    await db.execute(text(
                        """UPDATE guest_identity
                           SET created_at = now() - interval '8 days',
                               last_activity_at = now() - interval '8 days',
                               expires_at = now() - interval '1 day'
                           WHERE child_id = :c"""
                    ), {"c": cid})
                    await db.commit()
                    return cid

            expired_cid = asyncio.run(mk_expired())
            created_children.append(expired_cid)
            print(f"        造已过期游客 child={expired_cid}")

            # 注意：**不能**断言「purged 来自我这次手动调用」——后台 lifespan 循环
            # 可能已经先把它清掉了，那样 purged=0 会造成假失败（形态：判据绑错主体）。
            # 正确断言是**终态**：过期游客必须消失，且至少有一轮清理记录。
            async def do_cleanup():
                async with AsyncSessionLocal() as db:
                    return await run_cleanup(db)

            summary = asyncio.run(do_cleanup())
            print(f"        手动 run_cleanup summary={summary}")

            async def gone(cid):
                import psycopg
                url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
                with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
                    cur.execute("SELECT count(*) FROM child WHERE child_id=%s", (str(cid),))
                    n_child = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM guest_identity WHERE child_id=%s", (str(cid),))
                    n_id = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM guardian WHERE guardian_id NOT IN (SELECT guardian_id FROM child)")
                    n_orphan = cur.fetchone()[0]
                    return n_child, n_id, n_orphan

            nc, ni, norph = asyncio.run(gone(expired_cid))
            rec("5.2 已过期游客被清理机制真实清掉（child+identity 都没了）",
                nc == 0 and ni == 0, f"child 残留={nc} identity 残留={ni}")
            rec("5.3 被清游客不留孤儿 guardian（名下无孩子的 guardian 一并删）",
                norph == 0, f"孤儿 guardian={norph}")
            rec("5.4 清理有可 SQL 核对的运行记录（方案 4.3 要求「实际运行」而非只过单测）",
                snapshot_counts()["guest_cleanup_run"] > 0,
                f"guest_cleanup_run 行数={snapshot_counts()['guest_cleanup_run']}")
            if nc == 0:
                if expired_cid in created_children:
                    created_children.remove(expired_cid)  # 已被清理，不必再删

            # 未过期游客绝不能被清
            async def still_alive(cid):
                import psycopg
                url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
                with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
                    cur.execute("SELECT count(*) FROM child WHERE child_id=%s", (str(cid),))
                    return cur.fetchone()[0]

            alive = asyncio.run(still_alive(gidA)) if gidA else 0
            rec("5.5 未过期游客（A）没被误删", alive == 1, f"A 的 child 行数={alive}")

            # 既有 20 个 child 一个都不能少
            snap_now = snapshot_counts()
            rec("5.6 清理没碰任何既有 child（20 个基线 child 全在）",
                snap_now["child"] >= len(base_child), f"现在 child={snap_now['child']}，基线={len(base_child)}")

            banner("验收 6：会话过期或失效后不能访问旧数据")
            # 6.1 logout 后立即失效
            rOut = client.post("/v1/guest/logout")
            rec("6.1 POST /v1/guest/logout 成功", rOut.status_code == 200,
                f"status={rOut.status_code}")
            rAfter = client.get("/v1/guest/me")
            rec("6.2 登出后 /v1/guest/me 被拒（401，会话已失效）",
                rAfter.status_code == 401, f"status={rAfter.status_code}")
            if sidA:
                rData = client.get(f"/v1/learning/sessions/{sidA}/result")
                rec("6.3 登出后读不到旧学习数据（401）", rData.status_code == 401,
                    f"status={rData.status_code}")

            # 6.4 会话过期（把 expires_at 推到过去）后失效
            async def expire_session(cid):
                async with AsyncSessionLocal() as db:
                    await db.execute(text(
                        "UPDATE guest_session SET expires_at = now() - interval '1 hour' "
                        "WHERE child_id = :c"), {"c": cid})
                    await db.commit()

            with TestClient(app) as clientC:
                rC = clientC.post("/v1/guest/bootstrap")
                gidC = rC.json().get("guest_id") or rC.json().get("child_id")
                if gidC:
                    created_children.append(uuid.UUID(str(gidC)))
                asyncio.run(expire_session(uuid.UUID(str(gidC))))
                rExp = clientC.get("/v1/guest/me")
                rec("6.4 会话到期后不能访问旧数据（401）", rExp.status_code == 401,
                    f"status={rExp.status_code}")

            # 6.5 伪造 token 无效（TestClient 支持 cookies 参数，不必用异步 transport）
            with TestClient(app, cookies={"guest_session": "x" * 43}) as clientF:
                rForged = clientF.get("/v1/guest/me")
                rec("6.5 伪造/未知 token 被拒（401）", rForged.status_code == 401,
                    f"status={rForged.status_code}")

            banner("验收 7：原有学习流程回归通过")
            # 完整走一遍 A 的链路：bootstrap→session→task→submit→result
            with TestClient(app) as clientD:
                rD = clientD.post("/v1/guest/bootstrap")
                gidD = rD.json().get("guest_id") or rD.json().get("child_id")
                if gidD:
                    created_children.append(uuid.UUID(str(gidD)))
                rSD = clientD.post("/v1/learning/sessions", json={"subject": "math"})
                sidD = rSD.json().get("session_id") if rSD.status_code in (200, 201) else None
                rTD = clientD.post("/v1/learning/tasks/next", json={"session_id": sidD, "subject": "math"})
                tidD = rTD.json().get("task_instance_id") if rTD.status_code == 200 else None
                rSubD = clientD.post("/v1/learning/attempts",
                                     json={"task_instance_id": tidD, "attempt_no": 1,
                                           "response": {}}) if tidD else None
                rResD = clientD.get(f"/v1/learning/sessions/{sidD}/result") if sidD else None
                ok_flow = all([
                    rD.status_code == 200, rSD.status_code in (200, 201),
                    rTD.status_code == 200 and tidD,
                    rSubD is not None and rSubD.status_code == 200,
                    rResD is not None and rResD.status_code == 200,
                ])
                rec("7.1 完整链路 bootstrap→session→task→submit→result 全通",
                    bool(ok_flow),
                    f"bootstrap={rD.status_code} session={rSD.status_code} task={rTD.status_code} "
                    f"submit={rSubD.status_code if rSubD else '-'} result={rResD.status_code if rResD else '-'}")
                if rSubD is not None and rSubD.status_code == 200:
                    b = rSubD.json()
                    rec("7.2 判分结果字段齐全（correct / diagnosis / next_action）",
                        "correct" in b and "next_action" in b, f"keys={sorted(b)[:12]}")
                if rResD is not None and rResD.status_code == 200:
                    b = rResD.json()
                    rec("7.3 session result 含 completed_count（既有契约字段仍在）",
                        "completed_count" in b, f"keys={sorted(b)[:12]}")

                # QA 钉题通道仍只给 QA child
                rPin = clientD.post("/v1/learning/tasks/next",
                                    json={"session_id": sidD, "subject": "math",
                                          "pin_resource_version_id": "00000000-0000-0000-0000-000000000000"})
                rec("7.4 非 QA child 用 pin 钉题仍被拒（403，既有红线未松动）",
                    rPin.status_code == 403, f"status={rPin.status_code}")

            banner("验收 8：隐私说明与真实数据处理方式一致")
            # token 只存哈希：库里不应出现任何明文 token
            import psycopg
            url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
            with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
                cur.execute("SELECT session_token_hash FROM guest_session LIMIT 5")
                hashes = [r[0] for r in cur.fetchall()]
            rec("8.1 库内 session_token_hash 全为 64 位十六进制（sha256，非明文）",
                bool(hashes) and all(len(h) == 64 and all(ch in "0123456789abcdef" for ch in h)
                                     for h in hashes),
                f"抽样 {len(hashes)} 条，长度={[len(h) for h in hashes]}")
            # 8.2 必须是真查，不能硬编码 True（恒真断言 = 没验）
            with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
                cur.execute("SELECT count(*) FROM guardian WHERE display_name IS NOT NULL")
                named = cur.fetchone()[0]
            rec("8.2 游客 guardian 不存姓名（display_name 全为 NULL，只有演示家长有名）",
                named <= 1, f"display_name 非空的 guardian={named}（基线仅「演示家长」1 个）")
            with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
                cur.execute("""SELECT column_name FROM information_schema.columns
                               WHERE table_name='guardian' ORDER BY ordinal_position""")
                gcols = [r[0] for r in cur.fetchall()]
            rec("8.3 guardian 表无手机号/邮箱等 PII 列",
                not any(k in " ".join(gcols).lower() for k in ("phone", "email", "id_card")),
                f"guardian 列={gcols}")
            rec("8.4 数据保留期 7 天与配置一致", st.guest_retention_days == 7,
                f"guest_retention_days={st.guest_retention_days}")

    # ===== 零残留清理 =====
    banner("零残留清理（授权要求：验完立即物理删除本轮造的所有游客）")
    import asyncio

    async def purge_all():
        purged = []
        async with AsyncSessionLocal() as db:
            for cid in created_children:
                try:
                    await purge_one_guest(db, child_id=cid)
                    await db.commit()
                    purged.append(str(cid))
                except Exception as e:
                    await db.rollback()
                    print(f"        删除 {cid} 失败：{type(e).__name__}: {e}")
        return purged

    done = asyncio.run(purge_all())
    print(f"        已删 {len(done)}/{len(created_children)} 个本轮游客")

    # 兜底：删掉任何 guest_identity 里的残留（只删游客，不碰 20 个基线 child）。
    # **复用 purge_one_guest**，不再手写 SQL——手写版曾把 DELETE child 排在
    # task_instance 之前，撞 task_instance_child_id_fkey（第二次 traceback 的原因）。
    # 同一件事只在一处实现，删除顺序以 guest_cleanup 的外键拓扑序为唯一事实源。
    import psycopg
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
        cur.execute("SELECT child_id FROM guest_identity")
        leftover = [r[0] for r in cur.fetchall()]

    async def purge_leftover():
        async with AsyncSessionLocal() as db:
            for cid in leftover:
                try:
                    await purge_one_guest(db, child_id=cid)
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    print(f"        兜底删 {cid} 失败：{type(e).__name__}: {e}")

    if leftover:
        asyncio.run(purge_leftover())
    # 运行记录表是本轮验收产物，清空（TRUNCATE 不涉及外键）
    with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
        cur.execute("TRUNCATE guest_cleanup_run")
        # 再兜一层孤儿 guardian（purge_one_guest 只在名下无 child 时删）
        cur.execute("DELETE FROM guardian WHERE guardian_id NOT IN (SELECT guardian_id FROM child)")
    print(f"        兜底清掉 guest_identity 残留 {len(leftover)} 条 + 运行记录表 + 孤儿 guardian")

    counts_after = snapshot_counts()
    print("\n验收后计数:", json.dumps(counts_after, ensure_ascii=False))

    banner("零残留核对（与基线逐项比对）")
    import psycopg
    with psycopg.connect(url, autocommit=True) as c, c.cursor() as cur:
        cur.execute("SELECT child_id::text FROM child ORDER BY child_id")
        now_child = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT guardian_id::text FROM guardian ORDER BY guardian_id")
        now_guardian = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT count(*) FROM resource_version")
        rv_now = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM resource_version WHERE review_status='published'")
        pub_now = cur.fetchone()[0]

    rec("R1 基线 20 个 child 一个不少", base_child <= now_child,
        f"基线 {len(base_child)} ⊆ 现在 {len(now_child)}")
    rec("R2 本轮造的 child 全部删除（无多余 child）", now_child == base_child,
        f"多出={sorted(now_child - base_child)}")
    rec("R3 guardian 回到基线（仅 1 个演示家长）", now_guardian == base_guardian,
        f"基线={sorted(base_guardian)} 现在={sorted(now_guardian)}")
    rec("R4 四张 guest 表全部归零",
        all(counts_after[t] == 0 for t in
            ("guest_identity", "guest_session", "guest_daily_quota", "guest_cleanup_run")),
        str({t: counts_after[t] for t in ("guest_identity", "guest_session",
                                         "guest_daily_quota", "guest_cleanup_run")}))
    rec("R5 **resource_version 总数未变（304）**", rv_now == base["tables"]["resource_version"],
        f"{base['tables']['resource_version']} → {rv_now}")
    rec("R6 **published 仍是 225（正式题库分毫未动）**", pub_now == 225,
        f"published={pub_now}")
    rec("R7 learning_session 回到基线", counts_after["learning_session"] == counts_before["learning_session"],
        f"{counts_before['learning_session']} → {counts_after['learning_session']}")
    rec("R8 task_instance 回到基线", counts_after["task_instance"] == counts_before["task_instance"],
        f"{counts_before['task_instance']} → {counts_after['task_instance']}")
    rec("R9 attempt / learning_event / mastery_evidence 回到基线",
        counts_after["attempt"] == counts_before["attempt"]
        and counts_after["learning_event"] == counts_before["learning_event"]
        and counts_after["mastery_evidence"] == counts_before["mastery_evidence"],
        f"attempt {counts_before['attempt']}→{counts_after['attempt']} "
        f"event {counts_before['learning_event']}→{counts_after['learning_event']} "
        f"evidence {counts_before['mastery_evidence']}→{counts_after['mastery_evidence']}")
    rec("R10 ability_state 回到基线", counts_after["ability_state"] == counts_before["ability_state"],
        f"{counts_before['ability_state']} → {counts_after['ability_state']}")

    banner(f"总结论：{sum(1 for _,ok,_ in RESULTS if ok)}/{len(RESULTS)} PASS")
    fails = [(i, d) for i, ok, d in RESULTS if not ok]
    if fails:
        print(f"FAIL {len(fails)} 项：")
        for i, d in fails:
            print(f"  - {i}  {d}")
        return 1
    print("方案第九章 8 项验收 + 10 项零残留核对：全部 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
