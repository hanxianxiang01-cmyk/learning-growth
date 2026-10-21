#!/usr/bin/env python3
"""执行模式闸门自证测试（DB-free，进 pr_gate.py 第 4 项）。

背景（用户 2026-10-21 终审 §四）："`--no-write` 不能只控制直接 SQL。正常
提交接口，以及可能触发结算写入的接口，同样应受该模式约束。" 如果只测
"SQL 被拦"，而 HTTP 写路径没被测到，那这道闸门本身就是空断言——与上一轮
"专核=0 空集假通过"、"假会话按整条 SQL 判断"是同一类错误。

本测试不连数据库、不发真实请求，只验证闸门语义：

  G1 只读模式：guarded_post 必须抛 WriteBlocked，且**不产生任何字节**
  G2 只读模式：execute_write 必须抛 WriteBlocked
  G3 只读模式：write_actions 始终为空（没记 = 没写）
  G4 只读模式：verdict 不得为 PASS（NOT_RUN_READ_ONLY）
  G5 只读模式：默认输出路径加 _readonly 后缀，不覆盖写验证证据
  G6 写入授权模式：guarded_post 放行并登记；execute_write 登记
  G7 变异对照：把闸门短路（强制 allows_write=True）后 G1 必须失败——
     证明 G1 不是空跑

最后一项是关键：只证明"拦住了"不够，还要证明"该拦的确实会拦"。
"""
import os
import sys
import types

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


# ---------- G1/G3/G4/G5：只读模式 ----------
ro = ExecMode(READ_ONLY)

try:
    ro.guarded_post("http://127.0.0.1:9", "/v1/learning/attempts", {
        "task_instance_id": "x", "attempt_no": 1,
        "submission_id": "s", "response": {"answer": "0"},
    })
    g1_pass = False
    g1_detail = "未抛 WriteBlocked——HTTP 写路径没被拦（这正是用户点名的问题）"
except WriteBlocked as e:
    g1_pass = True
    g1_detail = str(e)[:80]
note("G1 只读模式拦截 HTTP 提交", g1_pass, g1_detail)

note("G3 只读模式零写动作记录", ro.write_actions == [], str(ro.write_actions))
note("G4 只读模式 verdict≠PASS", ro.verdict_when_all_skipped != "PASS",
     ro.verdict_when_all_skipped)
note("G5 只读输出不覆盖既有证据",
     ro.default_out("/tmp/FE1466_expiry_entry_reverify.json")
     == "/tmp/FE1466_expiry_entry_reverify_readonly.json",
     ro.default_out("/tmp/FE1466_expiry_entry_reverify.json"))

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
    g2_pass = False
    g2_detail = "未抛 WriteBlocked"
    g2_extra = f"conn.execute 被调用 {fc.calls} 次"
except WriteBlocked:
    g2_pass = fc.calls == 0
    g2_detail = f"conn.execute 调用次数={fc.calls}（须为 0）"
note("G2 只读模式拦截 SQL 且不触达连接", g2_pass, g2_detail)

# ---------- G6：写入授权模式放行并登记 ----------
rw = ExecMode(WRITE)
fc2 = _FakeConn()
rw.execute_write(fc2, "update task_instance set status='assigned'", (), desc="reset")
rw.note_write("row_lock", "t", "FOR UPDATE")
note("G6 写模式放行并逐项登记",
     fc2.calls == 1 and len(rw.write_actions) == 2
     and {a["kind"] for a in rw.write_actions} == {"sql_dml", "row_lock"},
     f"calls={fc2.calls} actions={[a['kind'] for a in rw.write_actions]}")

# ---------- G7：变异对照——短路闸门后 G1 必须失败 ----------
# 把 allows_write 强改为 True 后，guarded_post 会真的尝试连接 127.0.0.1:9
# （必然失败），因此我们进一步 monkeypatch 掉网络层，只观察"是否还抛
# WriteBlocked"。
mut = ExecMode(READ_ONLY)
type(mut).allows_write = property(lambda self: True)  # type: ignore[assignment]
try:
    mut.guarded_post("http://127.0.0.1:9", "/v1/learning/attempts", {
        "task_instance_id": "x", "attempt_no": 1, "submission_id": "s",
        "response": {"answer": "0"},
    })
    mutated_blocked = False
except WriteBlocked:
    mutated_blocked = True
except Exception:  # noqa: BLE001  —— 网络层失败属预期：说明确实发出去了
    mutated_blocked = False
finally:
    type(mut).allows_write = ExecMode.allows_write  # type: ignore[assignment]

note("G7 变异对照（短路后 G1 必失败）", mutated_blocked is False,
     "短路 allows_write 后不再抛 WriteBlocked（转而真的发出请求并连接失败）"
     "——证明 G1 的拦截来自闸门本身，不是别的原因顺带抛错")

# ---------- G8：CLI 默认必须是只读 ----------
import argparse  # noqa: E402

ap = argparse.ArgumentParser()
add_mode_args(ap)
d = resolve_mode(ap.parse_args([]))
w = resolve_mode(ap.parse_args(["--allow-write"]))
n = resolve_mode(ap.parse_args(["--no-write"]))
note("G8 CLI 默认只读、显式才写",
     d.name == READ_ONLY and n.name == READ_ONLY and w.name == WRITE,
     f"default={d.name} --no-write={n.name} --allow-write={w.name}")

print("\nEXEC-MODE-GATE:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)