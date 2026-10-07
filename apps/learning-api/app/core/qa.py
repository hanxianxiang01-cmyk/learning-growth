"""QA-Simulator 测试池常量（docs/governance/QA_DATA_HYGIENE.md）。

…0099 是唯一的 QA 专用 child：E2E / qa_replay / pin 钉题等一切"机器产生的
测试流量"都归它；真实 child（如 …0001）的数据只能由人产生。

后端侧唯一允许测试机制侵入生产选题逻辑的口子（tasks/next 的
pin_resource_version_id）以本模块为判定依据——非 QA child 调用一律 403。
"""
from __future__ import annotations

import os
import uuid

QA_CHILD_ID = uuid.UUID(os.environ.get("QA_CHILD_ID", "00000000-0000-0000-0000-000000000099"))


def is_qa_child(child_id: object) -> bool:
    """child_id 是否 QA 测试池。容忍 str/UUID/None。"""
    if child_id is None:
        return False
    try:
        return uuid.UUID(str(child_id)) == QA_CHILD_ID
    except (ValueError, AttributeError, TypeError):
        return False
