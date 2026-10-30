#!/usr/bin/env python3
"""FE-1466 Q07 收尾纪律：验证脚本的执行模式闸门（**内部辅助模块，不是新工具**）。

用户 2026-10-21 终审 §四 的执行约定，落成两类显式模式：

  READ_ONLY（默认，--no-write）
      只做只读核查：只读 SQL + 只读 HTTP（GET）。不发起正常作答提交、
      不改任何任务状态。未执行的场景一律标 SKIPPED_NOT_RUN，且 verdict
      不得为 PASS——只读跑一遍不能冒充"已验证"。

  QA_WRITE_AUTHORIZED（显式 --allow-write）
      授权对 QA child（…0099）做真实提交与状态变更；每一步写动作都必须
      登记进 write_actions，写什么、写在哪条样本上、为验证哪条断言。

两条硬约束（用户明确指出，此前脚本都没做到）：

  ① --no-write 不能只控制直接 SQL。正常提交接口 /v1/learning/attempts，
     以及任何可能触发结算写入的接口，同样受该模式约束。因此本模块把
     HTTP 写请求也纳入闸门：读写分流的唯一入口是 guarded_post()。
  ② 锁测也不是只读测试。即使最终三表计数相同，它仍执行过
     SELECT ... FOR UPDATE（持锁阻塞他人）与 UPDATE task_instance 状态
     变更 + 收尾复位。这类动作必须按"写动作"登记，不得记作"零变化"。

2026-10-21 复审补正（用户 §二.2）：**按副作用控制，不能按 HTTP 方法控制**。
    GET 不等于只读——`GET /v1/learning/sessions/{sid}/result` 是会执行结算的
    结果接口，可能带来状态或证据写入。因此本模块区分两类 GET：
      guarded_get()            纯探测（健康检查、状态查询）——两模式都放行
      guarded_effect_get()     有副作用的 GET（如结算）——受闸门约束
    只拦 POST 等于漏掉结算路径，与"只拦 SQL"是同一个错误的另一种形态。

另外：transport 可注入（默认走 urllib），使测试能**计数**而不真的发出请求。
    "捕获到任意 Exception"不能证明到达了发送入口——异常也可能来自序列化或
    参数处理。要证明闸门有效，必须能数清 transport 被调用了几次。

用法：
    from exec_mode import add_mode_args, resolve_mode
    ap.add_argument(...); add_mode_args(ap)
    mode = resolve_mode(ap.parse_args())
    mode.guarded_post(api, path, payload)      # 只读模式下抛 WriteBlocked
    mode.execute_write(conn, sql, params, desc="...")   # 同上，且登记
    mode.skip("A-NEW-SUB-EXPIRED", "需要真实提交")      # 生成跳过记录
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

READ_ONLY = "READ_ONLY"
WRITE = "QA_WRITE_AUTHORIZED"


class WriteBlocked(RuntimeError):
    """只读模式下试图执行写动作（SQL 或 HTTP）。"""


@dataclass
class ExecMode:
    name: str
    write_actions: list[dict] = field(default_factory=list)
    # 注入点：测试可替换成计数用替身，从而证明"是否真的到了发送入口"。
    # 默认走 urllib，生产行为不变。
    transport: object | None = None

    # ---------- 基本判断 ----------
    @property
    def allows_write(self) -> bool:
        return self.name == WRITE

    @property
    def verdict_when_all_skipped(self) -> str:
        # 只读跑一遍绝不允许落到 PASS：那是把"没验证"包装成"已验证"。
        return "NOT_RUN_READ_ONLY"

    def assert_can_write(self, action: str) -> None:
        if not self.allows_write:
            raise WriteBlocked(
                f"只读模式（--no-write）拒绝写动作：{action}。"
                f"如需 QA 写入验证，显式加 --allow-write。"
            )

    # ---------- 写动作台账 ----------
    def note_write(self, kind: str, target: str, detail: str) -> None:
        """登记一次写动作。kind: sql_dml / http_post / row_lock / state_restore。"""
        self.write_actions.append({"kind": kind, "target": target, "detail": detail})

    # ---------- SQL 写 ----------
    def execute_write(self, conn, sql: str, params=(), *, desc: str):
        self.assert_can_write(desc)
        self.note_write("sql_dml", desc, sql.strip().splitlines()[0][:120])
        return conn.execute(sql, params)

    # ---------- HTTP 写 ----------
    def _send(self, url: str, body: bytes | None, method: str, timeout: float):
        """唯一的实际发送点。测试通过注入 transport 计数。"""
        if self.transport is not None:
            return self.transport(url, body, method, timeout)
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"}, method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return e.code, {"raw": raw.decode(errors="replace")}
        except urllib.error.URLError as e:
            return 0, {"unreachable": repr(e)}

    def guarded_post(self, api: str, path: str, payload: dict, timeout: float = 60.0):
        """唯一的写请求入口。只读模式下不发出任何字节，直接抛 WriteBlocked。

        注意：这里是"写请求闸门"，不是"SQL 闸门"——用户明确要求
        --no-write 必须同时覆盖正常提交接口及其可能触发的结算写入。
        """
        self.assert_can_write(f"POST {path}")
        self.note_write(
            "http_post", path,
            json.dumps({k: v for k, v in payload.items()
                        if k in ("task_instance_id", "attempt_no", "submission_id")},
                       ensure_ascii=False),
        )
        return self._send(api.rstrip("/") + path, json.dumps(payload).encode(),
                          "POST", timeout)

    def guarded_effect_get(self, api: str, path: str, timeout: float = 15.0):
        """**有副作用**的 GET（如 session 结算 result）：受闸门约束。

        用户 §二.2 指出的缺口：结算读取路径可能带来状态或证据写入，
        "只拦 POST" 会漏掉它。GET 是方法，不是副作用判据。
        """
        self.assert_can_write(f"GET {path}（有副作用：结算/状态写入）")
        self.note_write("http_effect_get", path,
                        "有副作用的 GET（结算路径）——只读模式不调用")
        return self._send(api.rstrip("/") + path, None, "GET", timeout)

    def guarded_get(self, api: str, path: str, timeout: float = 15.0):
        """**纯只读探测**（健康检查/状态查询）。两种模式下都允许。

        仅限真的没有写语义的接口。任何会触发结算或状态变更的 GET 必须走
        guarded_effect_get()——不要在这里放宽判据。
        """
        return self._send(api.rstrip("/") + path, None, "GET", timeout)

    # ---------- 跳过记录 ----------
    @staticmethod
    def skip(case: str, why: str, **extra) -> dict:
        return {
            "case": case,
            "passed": None,
            "skipped": "SKIPPED_NOT_RUN",
            "reason": why,
            **extra,
        }

    # ---------- 落盘 ----------
    def record(self) -> dict:
        return {
            "execution_mode": self.name,
            "write_authorized": self.allows_write,
            "write_actions": self.write_actions,
            "write_action_count": len(self.write_actions),
            "mode_note": (
                "只读核查：未发起任何作答提交、未改任何任务状态；"
                "以下 SKIPPED_NOT_RUN 场景属未验证，不构成证据。"
                if not self.allows_write else
                "显式授权 QA 写入验证：write_actions 逐项登记了本次对 QA child "
                "产生的写动作（含锁测的状态变更与收尾复位）。"
            ),
        }

    def default_out(self, base_path: str) -> str:
        """只读跑不许覆盖既有写验证证据：默认落 _readonly 后缀。"""
        if self.allows_write:
            return base_path
        stem, dot, ext = base_path.rpartition(".")
        return f"{stem}_readonly{dot}{ext}" if dot else f"{base_path}_readonly"


def add_mode_args(ap: argparse.ArgumentParser) -> None:
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--no-write", dest="no_write", action="store_true",
        help="只读核查（默认）：不发起作答提交、不改任务状态，未执行场景标 SKIPPED_NOT_RUN",
    )
    g.add_argument(
        "--allow-write", dest="allow_write", action="store_true",
        help="显式授权 QA 写入验证：允许对 QA child 真实提交/变更状态，写动作逐项登记",
    )


def resolve_mode(args) -> ExecMode:
    """把 CLI 参数解析成执行模式。

    用户 §二.2：`--allow-write` 与 `--no-write` 同时出现时应**拒绝执行**，
    不能选其中一个继续跑。argparse 的互斥组已挡住多数情况，但本函数仍显式
    再判一次——因为 resolve_mode 也可能被不经 argparse 的调用方使用，
    那种情况下"悄悄选一个"正是最危险的失败形态。
    """
    no_write = getattr(args, "no_write", False)
    allow_write = getattr(args, "allow_write", False)
    if no_write and allow_write:
        raise SystemExit(
            "拒绝执行：--no-write 与 --allow-write 同时出现，语义冲突。"
            "请明确二选一（默认只读，需要 QA 写入验证时显式加 --allow-write）。"
        )
    if allow_write:
        return ExecMode(WRITE)
    return ExecMode(READ_ONLY)