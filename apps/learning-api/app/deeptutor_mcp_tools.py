#!/usr/bin/env python3
"""Learning Engine 的 MCP tool 样板 —— 供 DeepTutor 通过 MCP 协议调用。

背景（DeepTutor版本锁定_V1.0.md 第 2 节）：
DeepTutor v1.6.x 已演进为 MCP 工具架构（非设计假设的 Capability SPI）。
因此 GATE-R0-SPI 的验证重心从"外部 Capability SPI"转为"MCP tool 外挂 + 零 Core 补丁 + 失败隔离"。

本样板对应 Backlog E3-02/E3-03/E3-04 三个 tool 的接口签名：
- get_learner_state：只读返回能力切片
- submit_attempt：写 Attempt/Event 并返回 diagnosis + next_action
- get_teaching_action：仅返回允许的教学动作（不含自由教育决策）

注意：本样板为骨架，真实落库依赖 Sprint 1 的 E2 服务实现。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    content: list[dict] = field(default_factory=list)
    is_error: bool = False


# ---- MCP tool 定义（DeepTutor 通过 MCP 发现这些 tool） ----

TOOLS = [
    {
        "name": "get_learner_state",
        "description": "只读返回指定孩子在指定学科下的能力切片（ability_id, level, confidence, evidence_count）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "child_id": {"type": "string", "format": "uuid"},
                "subject": {"type": "string", "enum": ["math", "english"]},
            },
            "required": ["child_id", "subject"],
        },
    },
    {
        "name": "submit_attempt",
        "description": "提交一次作答，写入 Attempt/Event，返回 diagnosis（E01~E07）与 next_action，不返回答案。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_instance_id": {"type": "string", "format": "uuid"},
                "attempt_no": {"type": "integer", "minimum": 1},
                "response": {"type": "object"},
                "used_hint_levels": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["task_instance_id", "attempt_no", "response"],
        },
    },
    {
        "name": "get_teaching_action",
        "description": "按 Hint 状态机返回下一教学动作（QUESTION/STRUCTURE_HINT/STEP_HINT/TEACH），不含自由教育决策。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "attempt_id": {"type": "string", "format": "uuid"},
                "requested_level": {"type": "integer", "minimum": 1, "maximum": 4},
            },
            "required": ["attempt_id"],
        },
    },
]


# ---- 占位实现（Sprint 1 接入真实 service） ----

def get_learner_state(child_id: str, subject: str) -> ToolResult:
    # TODO(E2-01): 接入 LearnerProfileService
    return ToolResult(content=[{"type": "text", "text": json.dumps({"abilities": []})}])


def submit_attempt(task_instance_id: str, attempt_no: int, response: dict, used_hint_levels: list | None = None) -> ToolResult:
    # TODO(E2-02/E2-03): 接入 DiagnosisService + 写 Attempt/Event
    return ToolResult(content=[{"type": "text", "text": json.dumps({"correct": None, "diagnosis": None, "next_action": None})}])


def get_teaching_action(attempt_id: str, requested_level: int | None = None) -> ToolResult:
    # TODO(E2-06): 接入 StrategyService Hint 状态机
    return ToolResult(content=[{"type": "text", "text": json.dumps({"action_type": "QUESTION", "answer_revealed": False})}])


DISPATCH = {
    "get_learner_state": get_learner_state,
    "submit_attempt": submit_attempt,
    "get_teaching_action": get_teaching_action,
}


def call_tool(name: str, arguments: dict) -> ToolResult:
    fn = DISPATCH.get(name)
    if fn is None:
        return ToolResult(content=[{"type": "text", "text": f"unknown tool: {name}"}], is_error=True)
    return fn(**arguments)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="列出 MCP tools")
    args = ap.parse_args()
    if args.list:
        print(json.dumps(TOOLS, ensure_ascii=False, indent=2))
    else:
        print("Learning Engine MCP tools 样板（运行 --list 查看 tool 列表）")