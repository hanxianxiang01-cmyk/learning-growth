"""BUG-1451 回归：derive_stability / derive_transfer 的"最近 window 条"必须取尾。

约定（BUG-1448 定版）：_load_evidences 按 occurred_at 升序（老→新）加载，
全链"最近"一律取尾部切片。此前 stability/transfer 仍用 [:WINDOW] 取头，
与 C/I 维度（[-window:]）和 decide_review（[-3:]）方向相反——
练得多的孩子稳定性/迁移窗口被陈旧证据占死。本测锁定方向语义。
"""
import uuid

from app.services.mastery import (
    Evidence,
    derive_stability,
    derive_transfer,
)

RVS = [uuid.UUID(int=n) for n in (11, 12, 13, 14, 15, 16)]
SESS = [uuid.UUID(int=n) for n in (21, 22)]


def _ev(*, corr, hint=0, rv, sess, etype="attempt_standard", ctx=None):
    return Evidence(
        evidence_id=uuid.uuid4(),
        evidence_type=etype,
        correctness=corr,
        max_hint_level=hint,
        resource_version_id=rv,
        session_id=sess,
        context_family=ctx,
    )


def test_stability_window_uses_recent_not_stale():
    # 3 条陈旧全错（老）+ 5 条近期全对（新）——取尾=全对 S=1.0；取头（缺陷态）=混入 0 分
    evs = [
        _ev(corr=0.0, rv=RVS[0], sess=SESS[0]),
        _ev(corr=0.0, rv=RVS[1], sess=SESS[0]),
        _ev(corr=0.0, rv=RVS[2], sess=SESS[1]),
    ] + [
        _ev(corr=1.0, rv=RVS[i % 6], sess=SESS[i % 2]) for i in range(5)
    ]
    res = derive_stability(evs)
    assert res.sufficient is True
    assert res.value == 1.0, (
        f"稳定性窗口取到了陈旧证据（S={res.value}）——[:WINDOW] 方向回归"
    )


def test_transfer_window_uses_recent_not_stale():
    # 3 条陈旧迁移全错 + 2 条近期迁移全对（双 ctx、双 sess）——取尾=T=1.0
    # 5 条：最老 1 条错 + 最新 4 条对（窗口=4）。
    # 取尾（修复态）=全对 T=1.0；取头（缺陷态 [:4]）=混入 0 分 T=0.75。
    evs = [
        _ev(corr=0.0, rv=RVS[0], sess=SESS[0], etype="attempt_transfer", ctx="A"),
        _ev(corr=1.0, rv=RVS[1], sess=SESS[1], etype="attempt_transfer", ctx="B"),
        _ev(corr=1.0, rv=RVS[2], sess=SESS[0], etype="attempt_transfer", ctx="C"),
        _ev(corr=1.0, rv=RVS[3], sess=SESS[1], etype="attempt_transfer", ctx="D"),
        _ev(corr=1.0, rv=RVS[4], sess=SESS[0], etype="attempt_transfer", ctx="E"),
    ]
    res = derive_transfer(evs)
    assert res.sufficient is True
    assert res.value == 1.0, (
        f"迁移窗口取到了陈旧证据（T={res.value}）——[:WINDOW_MAX] 方向回归"
    )
