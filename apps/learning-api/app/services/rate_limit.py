"""按身份计的滑动窗口频率限流（防脚本刷接口）。

## 它和「每日 30 题」不是一回事

2026-11-01 取消了每日题数上限，但**接口防滥用必须留着**。两者的区别是：

| | 每日题数上限（已取消） | 频率限流（本模块） |
|---|---|---|
| 目的 | 限制孩子一天学多少 | 限制脚本一分钟打多少次 |
| 正常孩子会不会撞到 | 会（30 题很常见） | 不会（1 分钟提交 20 次不可能） |
| 撞到之后 | 一天不能再学 | 等几十秒就能继续 |

把「孩子学得多」当成滥用来拦，是我们这次要改掉的东西；
把「一秒发 200 个请求」放过去，才是真的没有防护。

## 为什么用内存窗口

单进程 uvicorn 部署下够用，且不需要为限流再写一张表（写库反而会把
防护变成数据库压力）。代价是进程重启后窗口清零——对「防脚本」这个目标
完全可接受：脚本重启不了我们的进程。若将来上多副本，这里必须换成
Redis 或库表实现，**否则每个副本各自 20 次，实际上限乘以副本数**。
"""
from __future__ import annotations

import math
import time
from collections import deque

# bucket 名 → {身份 key → 该窗口内的命中时间戳}
_WINDOWS: dict[str, dict[str, deque[float]]] = {}


class RateLimited(Exception):
    """超过频率限制。由 API 层转成 429 + Retry-After。"""

    def __init__(self, retry_after_seconds: float):
        # 向上取整：报 59 秒但实际要等 59.5 秒，客户端会准点早半秒重试再吃一次 429。
        self.retry_after_seconds = max(1, math.ceil(retry_after_seconds))
        super().__init__(f"请求过于频繁，请 {self.retry_after_seconds} 秒后再试")


def check(
    *,
    bucket: str,
    key: str,
    limit: int,
    window_seconds: float = 60.0,
    now: float | None = None,
) -> None:
    """记一次命中；超限抛 `RateLimited`。

    - `bucket` 区分用途（submit / next_task），互不挤占额度；
    - `key` 是身份（child_id），不同孩子互不影响；
    - `now` 可注入，测试不必真的等一分钟。
    """
    if limit <= 0:
        # 显式关闭（演练/压测）。默认配置里不会出现 0。
        return
    moment = time.monotonic() if now is None else now
    window = _WINDOWS.setdefault(bucket, {})
    hits = window.setdefault(key, deque())

    # 滑出窗口的命中先丢掉，再判断——顺序反了会把「刚过期」也算在窗口内。
    while hits and moment - hits[0] >= window_seconds:
        hits.popleft()

    if len(hits) >= limit:
        # 最早那次命中滑出窗口时才能再放行一次，这就是等待时间。
        retry_after = window_seconds - (moment - hits[0])
        raise RateLimited(retry_after)

    hits.append(moment)

    # 每个 visitor 在窗口字典里留一个 key，长期运行会一直涨。窗口一旦过去，
    # 那些 key 对决策毫无用处，只是内存。超过阈值时清掉彻底过期的 key。
    if len(window) > _SWEEP_THRESHOLD:
        _sweep(window, moment, window_seconds)


# 何时清理：字典超过这个规模就扫一次。定成常量而非配置——
# 它不是业务参数，调它不会改变任何一次放行/拒绝的结果。
_SWEEP_THRESHOLD = 512


def _sweep(window: dict[str, deque[float]], now: float, window_seconds: float) -> None:
    """丢掉「所有命中都已滑出窗口」的 key。

    判据是**最后**一次命中都已过期（`now - hits[-1] >= window`），
    而不是看 deque 是否为空：空的 deque 说明这个 key 刚刚才被算过一次，
    下一毫秒就要用，清掉等于把它的历史抹了。
    """
    stale = [k for k, hits in window.items() if hits and now - hits[-1] >= window_seconds]
    for k in stale:
        del window[k]


def reset() -> None:
    """清空所有窗口（测试与本地联调用）。"""
    _WINDOWS.clear()


def current_hits(bucket: str, key: str) -> int:
    """当前窗口内的命中数（诊断/测试断言用，不参与决策）。"""
    return len(_WINDOWS.get(bucket, {}).get(key, ()))
