#!/usr/bin/env python3
"""执行模式闸门自证测试（DB-free，进 pr_gate.py 第 4 项）。

背景（用户 2026-10-21 终审 §四）："`--no-write` 不能只控制直接 SQL。正常
提交接口，以及可能触发结算写入的接口，同样应受该模式约束。" 如果只测
"SQL 被拦"，而 HTTP 写路径没被测到，那这道闸门本身就是空断言——与
"专核=0 空集假通过"、"假会话按整条 SQL 判断"是同一类错误。

2026-10-21 复审补正（用户 §二.1 / §二.2），两处实质缺陷：

  ① G7 的 finally 恢复错了对象。`type(mut) is ExecMode`，所以
     `finally: type(mut).allows_write = ExecMode.allows_write` 取到的
     **已经是被替换后的属性**，恢复成了变异值。已在本测试内用
     `original = ExecMode.allows_write` 先存后还。
  ② "捕获到任意 Exception"不能证明到达 HTTP 发送入口——异常也可能来自
     序列化、日志或参数处理。改为**注入 transport 并计数**，三段式证明：
        S1 正常只读 → transport 调用 0 次
        S2 变异短路 → 同一输入确实到达 transport（计数 ≥1）
        S3 恢复原属性 → 新建只读实例再次被拦，transport 仍 0 次
  ③ 副作用不能按 HTTP 方法判：`GET /sessions/{sid}/result` 会执行结算。
     新增 G9/G10 覆盖 effect-GET。

本测试不连数据库、不发真实请求（transport 全部注入替身）。
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "rt1464"))

from exec_mode import (  # noqa: E402
    READ_ONLY, WRITE, ExecMode, WriteBlocked, add_mode_args, resolve_mode,
)

fails = []


def note(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


class CountingTransport:
    """替身 transport：只计数，不联网。证明"请求是否真的到了发送入口"。"""

    def __init__(self, result=(200, {"ok": True})):
        self.calls = []
        self.result = result

    def __call__(self, url, body, method, timeout):
        self.calls.append({"url": url, "method": method,
                           "body_len": len(body) if body else 0})
        return self.result


PAYLOAD = {"task_instance_id": "x", "attempt_no": 1,
           "submission_id": "s", "response": {"answer": "0"}}
API = "http://127.0.0.1:9"


# ---------- G1/G3/G4/G5：只读模式 ----------
ro_t = CountingTransport()
ro = ExecMode(READ_ONLY, transport=ro_t)

try:
    ro.guarded_post(API, "/v1/learning/attempts", PAYLOAD)
    g1_pass, g1_detail = False, "未抛 WriteBlocked——HTTP 写路径没被拦"
except WriteBlocked as e:
    g1_pass, g1_detail = True, str(e)[:70]
note("G1 只读模式拦截 HTTP 提交", g1_pass, g1_detail)

# G1b：这里才是"零字节"的硬证据——不能靠"抛了异常"推断。
note("G1b 只读模式 transport 零调用（未发出任何字节）",
     ro_t.calls == [], f"calls={ro_t.calls}")

note("G3 只读模式零写动作记录", ro.write_actions == [], str(ro.write_actions))
note("G4 只读模式 verdict≠PASS", ro.verdict_when_all_skipped != "PASS",
     ro.verdict_when_all_skipped)
note("G5 只读输出不覆盖既有证据",
     ro.default_out("/tmp/FE2026_x.json") == "/tmp/FE2026_x_readonly.json",
     ro.default_out("/tmp/FE2026_x.json"))


# ---------- G2：SQL 写同样被拦 ----------
class _FakeConn:
    def __init__(self):
        self.calls = 0

    def execute(self, sql, params=()):
        self.calls += 1
        return None


fc = _FakeConn()
try:
    ro.execute_write(fc, "update task_instance set status='cancelled'", (), desc="T3")
    g2_pass, g2_detail = False, "未抛 WriteBlocked"
except WriteBlocked:
    g2_pass = fc.calls == 0
    g2_detail = f"conn.execute 调用次数={fc.calls}（须为 0）"
note("G2 只读模式拦截 SQL 且不触达连接", g2_pass, g2_detail)


# ---------- G6：写入授权模式放行并登记 ----------
rw_t = CountingTransport()
rw = ExecMode(WRITE, transport=rw_t)
fc2 = _FakeConn()
rw.execute_write(fc2, "update task_instance set status='assigned'", (), desc="reset")
rw.note_write("row_lock", "t", "FOR UPDATE")
rw.guarded_post(API, "/v1/learning/attempts", PAYLOAD)
note("G6 写模式放行并逐项登记",
     fc2.calls == 1 and len(rw.write_actions) == 3 and len(rw_t.calls) == 1
     and {a["kind"] for a in rw.write_actions}
     == {"sql_dml", "row_lock", "http_post"},
     f"calls={fc2.calls} transport={len(rw_t.calls)} "
     f"actions={[a['kind'] for a in rw.write_actions]}")


# ---------- G7 三段式变异对照（用户 §二.1 的最小验收） ----------
# 关键修正：先保存**原对象**再替换；finally 归还保存的对象，而不是重新读取
# 那个已经被替换掉的类属性。
original_allows_write = ExecMode.allows_write      # ← 变异前保存
mut_t = CountingTransport(result=(0, {"unreachable": "injected"}))
mut = ExecMode(READ_ONLY, transport=mut_t)

try:
    ExecMode.allows_write = property(lambda self: True)   # 短路闸门
    try:
        mut.guarded_post(API, "/v1/learning/attempts", PAYLOAD)
        s2_blocked = False
    except WriteBlocked:
        s2_blocked = True
    except Exception as e:  # noqa: BLE001
        s2_blocked = f"意外异常 {e!r}（既没被闸门拦，也没到 transport）"
finally:
    ExecMode.allows_write = original_allows_write         # ← 归还保存的对象

note("G7-S2 变异短路后不再被闸门拦（G1 非空跑）", s2_blocked is False,
     "短路后不再抛 WriteBlocked" if s2_blocked is False else str(s2_blocked))
note("G7-S2b 变异短路后请求确实到达 transport（证明确实到了发送入口）",
     len(mut_t.calls) == 1, f"transport calls={len(mut_t.calls)}（须为 1）")

# G7-S3：恢复后必须真的恢复。这是原缺陷的直接回归锁。
note("G7-S3 原属性已恢复（只读实例再次放行为 False）",
     ExecMode(READ_ONLY).allows_write is False,
     f"新建 READ_ONLY.allows_write={ExecMode(READ_ONLY).allows_write}")

s3_t = CountingTransport()
s3 = ExecMode(READ_ONLY, transport=s3_t)
try:
    s3.guarded_post(API, "/v1/learning/attempts", PAYLOAD)
    s3_blocked = False
except WriteBlocked:
    s3_blocked = True
note("G7-S3b 恢复后新建只读实例仍被拦且 transport 零调用",
     s3_blocked and s3_t.calls == [],
     f"blocked={s3_blocked} calls={len(s3_t.calls)}")


# ---------- G8：CLI 默认必须是只读 ----------
ap = argparse.ArgumentParser()
add_mode_args(ap)
d = resolve_mode(ap.parse_args([]))
w = resolve_mode(ap.parse_args(["--allow-write"]))
n = resolve_mode(ap.parse_args(["--no-write"]))
note("G8 CLI 默认只读、显式才写",
     d.name == READ_ONLY and n.name == READ_ONLY and w.name == WRITE,
     f"default={d.name} --no-write={n.name} --allow-write={w.name}")

# ---------- G8b：两个开关同时给必须拒绝执行 ----------
class _Both:
    no_write = True
    allow_write = True


refused = False
try:
    resolve_mode(_Both())
except SystemExit as e:
    refused = "拒绝执行" in str(e)
note("G8b --no-write 与 --allow-write 同时出现必须拒绝（不二选一继续跑）",
     refused, "已拒绝" if refused else "竟然选了一个继续跑")


# ---------- G9/G10：副作用 GET（用户 §二.2） ----------
ro2_t = CountingTransport()
ro2 = ExecMode(READ_ONLY, transport=ro2_t)
try:
    ro2.guarded_effect_get(API, "/v1/learning/sessions/s1/result")
    g9_blocked = False
except WriteBlocked:
    g9_blocked = True
note("G9 只读模式拦截有副作用的 GET（结算 result）",
     g9_blocked and ro2_t.calls == [],
     f"blocked={g9_blocked} transport={len(ro2_t.calls)}（GET 也可能写，不能按方法判）")

rw2_t = CountingTransport()
rw2 = ExecMode(WRITE, transport=rw2_t)
rw2.guarded_effect_get(API, "/v1/learning/sessions/s1/result")
note("G10 写模式放行 effect-GET 并登记",
     len(rw2_t.calls) == 1 and rw2_t.calls[0]["method"] == "GET"
     and rw2.write_actions and rw2.write_actions[0]["kind"] == "http_effect_get",
     f"transport={rw2_t.calls}")

# G11：纯只读探测在只读模式下仍可用（不能把健康检查也拦死）
ro3_t = CountingTransport()
ro3 = ExecMode(READ_ONLY, transport=ro3_t)
ro3.guarded_get(API, "/healthz")
note("G11 纯只读探测 GET 在只读模式仍放行（不误伤健康检查）",
     len(ro3_t.calls) == 1 and ro3.write_actions == [],
     f"transport={len(ro3_t.calls)} write_actions={ro3.write_actions}")

print("\nEXEC-MODE-GATE:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)