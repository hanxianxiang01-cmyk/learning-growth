"""Pydantic schema —— 数据校验与 API 契约。

命名与 DDL snake_case 一致，字段精度对齐冻结基线 V1.3.1。
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---- 基础模型 ----

class GuardianCreate(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)


class GuardianOut(GuardianCreate):
    model_config = ConfigDict(from_attributes=True)
    guardian_id: uuid.UUID
    status: str
    created_at: datetime


class ChildCreate(BaseModel):
    guardian_id: uuid.UUID
    nickname: str = Field(max_length=64)
    grade: str = Field(max_length=32)
    region_code: str | None = Field(default=None, max_length=32)
    birth_year: int | None = None


class ChildOut(ChildCreate):
    model_config = ConfigDict(from_attributes=True)
    child_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


# ---- 能力图谱 ----

class AbilityNodeCreate(BaseModel):
    ability_id: str = Field(max_length=64)
    subject: str = Field(max_length=16)
    domain_code: str = Field(max_length=64)
    name: str = Field(max_length=128)
    definition: str
    level_schema: dict[str, Any]


class AbilityNodeOut(AbilityNodeCreate):
    model_config = ConfigDict(from_attributes=True)
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


class AbilityEdgeCreate(BaseModel):
    from_ability_id: str = Field(alias="from_ability_id")
    to_ability_id: str
    relation_type: str = Field(pattern="^(prerequisite|supports|next)$")
    strength: str = "medium"


class AbilityEdgeOut(AbilityEdgeCreate):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ---- 资源 ----

class ResourceCreate(BaseModel):
    ability_id: str
    resource_type: str = Field(max_length=32)
    title: str = Field(max_length=256)
    created_by: str | None = None


class ResourceOut(ResourceCreate):
    model_config = ConfigDict(from_attributes=True)
    resource_id: uuid.UUID
    status: str
    created_at: datetime


class ResourceVersionCreate(BaseModel):
    resource_id: uuid.UUID
    version_no: int
    difficulty: int = Field(ge=1, le=5)
    task_type: str = Field(max_length=32)
    content: dict[str, Any]
    ui_schema: dict[str, Any]
    error_models: list[Any] = Field(default_factory=list)
    hint_policy: dict[str, Any]
    mastery_rule: dict[str, Any] | None = None
    transfer_distance: int | None = Field(default=None, ge=0, le=4)


class ResourceVersionOut(ResourceVersionCreate):
    model_config = ConfigDict(from_attributes=True)
    resource_version_id: uuid.UUID
    review_status: str
    created_at: datetime


# ---- 学习会话链 ----

class LearningPlanCreate(BaseModel):
    child_id: uuid.UUID
    subject: str = Field(max_length=16)
    plan_type: str = "adaptive"
    target_ability_ids: list[str] = Field(default_factory=list)
    fit_band: dict[str, Any] = Field(default_factory=dict)
    rationale: dict[str, Any] = Field(default_factory=dict)
    generated_by: str = "curriculum_engine"
    rule_version: str = "curriculum-v1.3"


class LearningPlanOut(LearningPlanCreate):
    model_config = ConfigDict(from_attributes=True)
    plan_id: uuid.UUID
    status: str
    valid_from: datetime
    valid_until: datetime | None
    created_at: datetime


class LearningSessionCreate(BaseModel):
    child_id: uuid.UUID
    subject: str = Field(max_length=16)
    plan_id: uuid.UUID | None = None


class LearningSessionOut(LearningSessionCreate):
    model_config = ConfigDict(from_attributes=True)
    session_id: uuid.UUID
    status: str
    started_at: datetime
    ended_at: datetime | None


class TaskInstanceCreate(BaseModel):
    session_id: uuid.UUID
    child_id: uuid.UUID
    ability_id: str
    resource_version_id: uuid.UUID
    assigned_difficulty: int = Field(ge=1, le=5)
    strategy_policy: dict[str, Any]


class TaskInstanceOut(TaskInstanceCreate):
    model_config = ConfigDict(from_attributes=True)
    task_instance_id: uuid.UUID
    status: str
    assigned_at: datetime


# ---- 核心教学载荷 ----

class AttemptRequest(BaseModel):
    """提交一次作答（对齐 OpenAPI AttemptRequest）。"""
    task_instance_id: uuid.UUID
    attempt_no: int = Field(ge=1)
    response: dict[str, Any]
    client_elapsed_ms: int | None = Field(default=None, ge=0)
    used_hint_levels: list[int] = Field(default_factory=list)


class DiagnosisResult(BaseModel):
    """教育诊断（HTTP 2xx 载荷，对齐 OpenAPI DiagnosisResult）。"""
    code: str = Field(pattern="^E0[1-7]$")
    label: str
    confidence: float = Field(ge=0, le=1)
    evidence_scope: str


class NextAction(BaseModel):
    type: str = Field(pattern="^(RETRY|HINT|TEACH|COMPLETE|NEXT_TASK)$")
    hint_level: int | None = None
    policy_id: str | None = None


class AttemptResult(BaseModel):
    attempt_id: uuid.UUID
    correct: bool | None
    diagnosis: DiagnosisResult | None
    next_action: NextAction | None


class MasteryDecision(BaseModel):
    ability_id: str
    old_level: int
    new_level: int
    decision: str = Field(pattern="^(unchanged|candidate_upgrade|upgraded|review_required|downgraded_after_review)$")
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


# ---- 能力状态 ----

class AbilityStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    child_id: uuid.UUID
    ability_id: str
    level: int
    confidence: float
    fit_band_min: int | None
    fit_band_max: int | None
    evidence_count: int
    trend: str
    last_evidence_at: datetime | None


class LearnerProfile(BaseModel):
    child_id: uuid.UUID
    grade: str | None
    active_abilities: list[AbilityStateOut]
    strengths: list[str]
    developing: list[str]
    observations: list[str]