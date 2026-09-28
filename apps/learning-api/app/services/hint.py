"""StrategyService —— Hint 状态机（受控 Hint 0-4，首次错误不揭答案）。

红线：首次错误不揭答案；answer_revealed 仅在最末层（TEACH 且允许）才可为 True。
"""
from __future__ import annotations

from dataclasses import dataclass

# 动作类型（对齐 OpenAPI hints 接口 action_type 枚举）
ACTION_QUESTION = "QUESTION"
ACTION_STRUCTURE = "STRUCTURE_HINT"
ACTION_STEP = "STEP_HINT"
ACTION_TEACH = "TEACH"


@dataclass
class HintDecision:
    hint_level: int
    action_type: str
    text: str
    answer_revealed: bool
    policy_id: str

    def to_dict(self) -> dict:
        return {
            "hint_level": self.hint_level,
            "action_type": self.action_type,
            "text": self.text,
            "answer_revealed": self.answer_revealed,
            "policy_id": self.policy_id,
        }


_HINT_LADDER = [
    (1, ACTION_QUESTION, "你再读一遍题目，看看条件里给了哪些数？"),
    (2, ACTION_STRUCTURE, "这道题可以分成几步来做，先想第一步要算什么。"),
    (3, ACTION_STEP, "第一步是找出已知和未知，试试把它们列出来。"),
    (4, ACTION_TEACH, "这道题的完整思路是……（教学讲解，不直接给答案）"),
]


def decide_hint(
    *,
    attempt_count: int,
    requested_level: int | None,
    max_level: int = 4,
) -> HintDecision:
    """受控 Hint：按尝试次数逐级上台阶，封顶 max_level。

    - 首次错误（attempt_count 较小）绝不揭答案；
    - hint_level 从 1 起步，每多试一次升一级；
    - answer_revealed 恒为 False（MVP 规则：任何 Hint 都不直接泄答案）。
    """
    level = request_level(requested_level, attempt_count, max_level)
    _, action, text = _HINT_LADDER[level - 1]
    return HintDecision(
        hint_level=level,
        action_type=action,
        text=text,
        answer_revealed=False,
        policy_id=f"hint-{level}",
    )


def request_level(requested: int | None, attempt_count: int, max_level: int) -> int:
    """计算实际 hint_level：请求值封顶在 [1, max_level]，且不越过 attempt 阶梯。"""
    ladder = min(attempt_count, max_level)
    if requested is None:
        return max(1, ladder)
    return max(1, min(requested, max_level, ladder))