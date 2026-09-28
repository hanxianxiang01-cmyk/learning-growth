"""数据模型 —— 严格对齐 01_schema_postgresql_v1.3.1.sql。

表结构由 Alembic 迁移管理（app.core.database.Base 不自动建表）。
这里的 ORM 仅用于类型化读写，字段名 = snake_case DDL 列名。
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Guardian(Base):
    __tablename__ = "guardian"

    guardian_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Child(Base):
    __tablename__ = "child"
    __table_args__ = (Index("idx_child_guardian", "guardian_id"),)

    child_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guardian.guardian_id"), nullable=False)
    nickname: Mapped[str] = mapped_column(String(64), nullable=False)
    grade: Mapped[str] = mapped_column(String(32), nullable=False)
    region_code: Mapped[str | None] = mapped_column(String(32))
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TextbookProfile(Base):
    __tablename__ = "textbook_profile"
    __table_args__ = (UniqueConstraint("child_id", "subject", "effective_from", name="textbook_profile_child_id_subject_effective_from_key"),)

    textbook_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    region_code: Mapped[str | None] = mapped_column(String(32))
    publisher: Mapped[str | None] = mapped_column(String(128))
    edition: Mapped[str | None] = mapped_column(String(64))
    grade: Mapped[str | None] = mapped_column(String(32))
    term: Mapped[str | None] = mapped_column(String(32))
    current_unit: Mapped[str | None] = mapped_column(String(128))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class AbilityNode(Base):
    __tablename__ = "ability_node"
    __table_args__ = (Index("idx_ability_domain", "subject", "domain_code"),)

    ability_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    domain_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    level_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AbilityEdge(Base):
    __tablename__ = "ability_edge"
    __table_args__ = (
        CheckConstraint("relation_type IN ('prerequisite','supports','next')", name="ability_edge_relation_type_check"),
    )

    from_ability_id: Mapped[str] = mapped_column(ForeignKey("ability_node.ability_id"), primary_key=True)
    to_ability_id: Mapped[str] = mapped_column(ForeignKey("ability_node.ability_id"), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(24), primary_key=True, nullable=False)
    strength: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")


class AbilityState(Base):
    __tablename__ = "ability_state"
    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 4", name="ability_state_level_check"),
        CheckConstraint("fit_band_min BETWEEN 1 AND 5", name="ability_state_fit_band_min_check"),
        CheckConstraint("fit_band_max BETWEEN 1 AND 5", name="ability_state_fit_band_max_check"),
        CheckConstraint(
            "fit_band_min IS NULL OR fit_band_max IS NULL OR fit_band_min <= fit_band_max",
            name="ability_state_check",
        ),
    )

    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), primary_key=True)
    ability_id: Mapped[str] = mapped_column(ForeignKey("ability_node.ability_id"), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    fit_band_min: Mapped[int | None] = mapped_column(SmallInteger)
    fit_band_max: Mapped[int | None] = mapped_column(SmallInteger)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trend: Mapped[str] = mapped_column(String(16), nullable=False, default="watch")
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Resource(Base):
    __tablename__ = "resource"
    __table_args__ = (Index("idx_resource_ability", "ability_id", "status"),)

    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ability_id: Mapped[str] = mapped_column(ForeignKey("ability_node.ability_id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ResourceVersion(Base):
    __tablename__ = "resource_version"
    __table_args__ = (
        UniqueConstraint("resource_id", "version_no", name="resource_version_resource_id_version_no_key"),
        Index("idx_resource_version_lookup", "resource_id", "review_status", "difficulty"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="resource_version_difficulty_check"),
        CheckConstraint("transfer_distance BETWEEN 0 AND 4", name="resource_version_transfer_distance_check"),
    )

    resource_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resource.resource_id"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    ui_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_models: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    hint_policy: Mapped[dict] = mapped_column(JSON, nullable=False)
    mastery_rule: Mapped[dict | None] = mapped_column(JSON)
    transfer_distance: Mapped[int | None] = mapped_column(SmallInteger)
    review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    reviewer_1: Mapped[str | None] = mapped_column(String(128))
    reviewer_2: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningPlan(Base):
    __tablename__ = "learning_plan"
    __table_args__ = (
        CheckConstraint("status IN ('draft','active','completed','cancelled','expired')", name="ck_learning_plan_valid_window"),
        CheckConstraint("valid_until IS NULL OR valid_until >= valid_from", name="ck_learning_plan_valid_window2"),
        UniqueConstraint("plan_id", "child_id", name="uq_learning_plan_plan_child"),
        Index("idx_plan_child_status", "child_id", "status", "created_at"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False, default="adaptive")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    target_ability_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    fit_band: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rationale: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    generated_by: Mapped[str] = mapped_column(String(32), nullable=False, default="curriculum_engine")
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False, default="curriculum-v1.3")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningSession(Base):
    __tablename__ = "learning_session"
    __table_args__ = (
        ForeignKeyConstraint(
            ["plan_id", "child_id"],
            ["learning_plan.plan_id", "learning_plan.child_id"],
            name="fk_learning_session_plan",
            ondelete="RESTRICT",
        ),
        Index("idx_session_child_time", "child_id", "started_at"),
        Index("idx_session_plan", "plan_id", postgresql_where="plan_id IS NOT NULL"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    subject: Mapped[str] = mapped_column(String(16), nullable=False)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")


class TaskInstance(Base):
    __tablename__ = "task_instance"
    __table_args__ = (
        CheckConstraint("assigned_difficulty BETWEEN 1 AND 5", name="task_instance_assigned_difficulty_check"),
        Index("idx_task_child_status", "child_id", "status", "assigned_at"),
    )

    task_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_session.session_id"), nullable=False)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    ability_id: Mapped[str] = mapped_column(ForeignKey("ability_node.ability_id"), nullable=False)
    resource_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resource_version.resource_version_id"), nullable=False)
    assigned_difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    strategy_policy: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="assigned")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Attempt(Base):
    __tablename__ = "attempt"
    __table_args__ = (
        UniqueConstraint("task_instance_id", "attempt_no", name="attempt_task_instance_id_attempt_no_key"),
        CheckConstraint("max_hint_level BETWEEN 0 AND 4", name="attempt_max_hint_level_check"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_instance.task_instance_id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    correct: Mapped[bool | None] = mapped_column(Boolean)
    client_elapsed_ms: Mapped[int | None] = mapped_column(Integer)
    max_hint_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    diagnosis: Mapped[dict | None] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LearningEvent(Base):
    __tablename__ = "learning_event"
    __table_args__ = (
        Index("idx_event_child_time", "child_id", "occurred_at"),
        Index("idx_event_session_seq", "session_id", "seq_no"),
        Index("idx_event_task", "task_instance_id", "event_type"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("learning_session.session_id"))
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task_instance.task_instance_id"))
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("attempt.attempt_id"))
    agent_turn_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    seq_no: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MasteryEvidence(Base):
    __tablename__ = "mastery_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('attempt_standard','attempt_transfer','retention_check','stability_window','transfer_window','explanation')",
            name="mastery_evidence_evidence_type_check",
        ),
        CheckConstraint("correctness IS NULL OR correctness BETWEEN 0 AND 1", name="mastery_evidence_correctness_check"),
        CheckConstraint("independence IS NULL OR independence BETWEEN 0 AND 1", name="mastery_evidence_independence_check"),
        CheckConstraint("stability IS NULL OR stability BETWEEN 0 AND 1", name="mastery_evidence_stability_check"),
        CheckConstraint("transfer IS NULL OR transfer BETWEEN 0 AND 1", name="mastery_evidence_transfer_check"),
        CheckConstraint(
            "(evidence_type IN ('attempt_standard','attempt_transfer','retention_check','explanation') AND cardinality(source_evidence_ids)=0) OR (evidence_type IN ('stability_window','transfer_window') AND cardinality(source_evidence_ids)>0)",
            name="mastery_evidence_check",
        ),
        Index("idx_evidence_ability_time", "child_id", "ability_id", "occurred_at", postgresql_where="valid = true"),
    )

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    ability_id: Mapped[str] = mapped_column(ForeignKey("ability_node.ability_id"), nullable=False)
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task_instance.task_instance_id"))
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("attempt.attempt_id"))
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    correctness: Mapped[float | None] = mapped_column(Numeric(5, 4))
    independence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    stability: Mapped[float | None] = mapped_column(Numeric(5, 4))
    transfer: Mapped[float | None] = mapped_column(Numeric(5, 4))
    source_evidence_ids: Mapped[list] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    context_family: Mapped[str | None] = mapped_column(String(64))
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False, default="mastery-v1.3")
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GrowthSnapshot(Base):
    __tablename__ = "growth_snapshot"
    __table_args__ = (
        UniqueConstraint("child_id", "period_type", "period_start", "period_end", name="growth_snapshot_child_id_period_type_period_start_period_end_key"),
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    period_type: Mapped[str] = mapped_column(String(16), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    ability_states: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GrowthReport(Base):
    __tablename__ = "growth_report"
    __table_args__ = (UniqueConstraint("snapshot_id", "report_version", name="growth_report_snapshot_id_report_version_key"),)

    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("growth_snapshot.snapshot_id"), nullable=False)
    report_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    evidence_refs: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConsentRecord(Base):
    __tablename__ = "consent_record"
    __table_args__ = (Index("idx_consent_child", "child_id", "consent_type", "granted_at"),)

    consent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guardian_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guardian.guardian_id"), nullable=False)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AudioAsset(Base):
    __tablename__ = "audio_asset"

    audio_asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("child.child_id"), nullable=False)
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task_instance.task_instance_id"))
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    consent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("consent_record.consent_id"), nullable=False)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())