"""FitBand —— ZPD 任务难度带计算 + Curriculum next_task 推荐。

原则（基线）：输出的是"个体适配难度带"，不修改 Resource 的客观难度。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FitBand:
    child_id: str
    ability_id: str
    band_min: int  # 1..5
    band_max: int  # 1..5

    def to_dict(self) -> dict:
        return {
            "child_id": self.child_id,
            "ability_id": self.ability_id,
            "min": self.band_min,
            "max": self.band_max,
        }


def compute_fit_band(*, level: int, confidence: float) -> tuple[int, int]:
    """由能力等级 + 置信度推导适配难度带（1-5）。

    - level 越高、confidence 越高，难度带上移；
    - 输出区间保证 band_min <= band_max。
    """
    base = {
        0: (1, 1),
        1: (1, 2),
        2: (2, 3),
        3: (3, 4),
        4: (4, 5),
    }.get(level, (1, 1))

    # confidence 低时收窄并下移，避免冒险
    if confidence < 0.4:
        band_min = max(1, base[0])
        band_max = max(band_min, base[0])
    elif confidence < 0.7:
        band_min, band_max = base
    else:
        band_min = min(5, base[1])
        band_max = min(5, base[1] + 1)

    band_min = max(1, min(5, band_min))
    band_max = max(band_min, min(5, band_max))
    return band_min, band_max


@dataclass
class NextTaskHint:
    ability_id: str
    difficulty: int
    reason: str


def next_task_recommendation(
    *,
    fit_band: tuple[int, int],
    mastered: bool,
    need_review: bool,
) -> NextTaskHint:
    """Curriculum next_task 的纯决策：给难度 + 理由。

    输入已由 repository 层准备（前置能力、复习需求等），这里只做难度带内决策。
    """
    band_min, band_max = fit_band
    if need_review:
        # 复习需求优先，取难度带下沿
        return NextTaskHint(ability_id="", difficulty=band_min, reason="review_required")
    if mastered:
        # 已掌握，向难度带上沿推进
        return NextTaskHint(ability_id="", difficulty=band_max, reason="advance")
    return NextTaskHint(ability_id="", difficulty=band_min, reason="practice")