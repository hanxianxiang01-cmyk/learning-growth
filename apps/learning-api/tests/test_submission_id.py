"""FE-1410 submission_id 幂等落库契约（模型层防漂移单测，不依赖 DB）。

真实幂等三轨（重放/409/旧轨兼容）已在 scripts/migrate_submission_id.py 迁移 +
运行库冒烟实证；本测试守「ORM 定义与迁移契约一致」，防止列/索引被改坏后
迁移与代码脱节（对齐 test_schema_enum_synced_with_protocol 的防漂移思路）。
"""
import uuid

from app.models import Attempt
from app.services.turn_service import SubmissionConflict


def test_attempt_has_submission_id_column():
    col = Attempt.__table__.columns.get("submission_id")
    assert col is not None, "attempt.submission_id 列缺失（FE-1410 迁移契约）"
    assert col.nullable is True, "submission_id 必须可空（V1 提交走旧轨，双轨并存）"
    # 类型是 UUID
    assert getattr(col.type, "as_uuid", False) is True


def test_submission_id_partial_unique_index():
    idx = next(
        (i for i in Attempt.__table__.indexes if i.name == "uq_attempt_submission_id"),
        None,
    )
    assert idx is not None, "uq_attempt_submission_id 索引缺失"
    assert idx.unique is True, "submission_id 索引必须唯一"
    # 部分索引：WHERE submission_id IS NOT NULL（NULL 不参与唯一，兼容 V1）
    assert idx.dialect_kwargs.get("postgresql_where") is not None, "必须是部分唯一索引"


def test_submission_conflict_is_valueerror_subclass():
    # API 先捕获 SubmissionConflict(409) 再捕获 ValueError(404)：
    # 继承关系保证 except SubmissionConflict 必须在 except ValueError 之前，
    # 且未显式处理时至少落到 ValueError 分支而非逃逸。
    assert issubclass(SubmissionConflict, ValueError)
    err = SubmissionConflict(f"submission_id {uuid.uuid4()} 冲突")
    assert isinstance(err, ValueError)
