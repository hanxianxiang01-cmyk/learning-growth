-- 儿童学习成长系统 V2.0 - PostgreSQL DDL baseline V1.3.1
-- Gate policy: GATE-R0-SPI is external to schema; GRAY-01 is closed. V1.3.1 adds XLSX-cache delivery Gate only; schema semantics are unchanged from V1.3.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE guardian (
  guardian_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name varchar(64),
  status varchar(16) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE child (
  child_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guardian_id uuid NOT NULL REFERENCES guardian(guardian_id),
  nickname varchar(64) NOT NULL,
  grade varchar(32) NOT NULL,
  region_code varchar(32),
  birth_year smallint,
  status varchar(16) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_child_guardian ON child(guardian_id);

CREATE TABLE textbook_profile (
  textbook_profile_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  subject varchar(16) NOT NULL,
  region_code varchar(32),
  publisher varchar(128),
  edition varchar(64),
  grade varchar(32),
  term varchar(32),
  current_unit varchar(128),
  effective_from date,
  effective_to date,
  UNIQUE(child_id, subject, effective_from)
);

CREATE TABLE ability_node (
  ability_id varchar(64) PRIMARY KEY,
  subject varchar(16) NOT NULL,
  domain_code varchar(64) NOT NULL,
  name varchar(128) NOT NULL,
  definition text NOT NULL,
  level_schema jsonb NOT NULL,
  status varchar(16) NOT NULL DEFAULT 'active',
  version int NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_ability_domain ON ability_node(subject, domain_code);

CREATE TABLE ability_edge (
  from_ability_id varchar(64) NOT NULL REFERENCES ability_node(ability_id),
  to_ability_id varchar(64) NOT NULL REFERENCES ability_node(ability_id),
  relation_type varchar(24) NOT NULL CHECK (relation_type IN ('prerequisite','supports','next')),
  strength varchar(16) NOT NULL DEFAULT 'medium',
  PRIMARY KEY(from_ability_id, to_ability_id, relation_type)
);

CREATE TABLE ability_state (
  child_id uuid NOT NULL REFERENCES child(child_id),
  ability_id varchar(64) NOT NULL REFERENCES ability_node(ability_id),
  level smallint NOT NULL DEFAULT 0 CHECK (level BETWEEN 0 AND 4),
  confidence numeric(5,4) NOT NULL DEFAULT 0,
  fit_band_min smallint CHECK (fit_band_min BETWEEN 1 AND 5),
  fit_band_max smallint CHECK (fit_band_max BETWEEN 1 AND 5),
  evidence_count int NOT NULL DEFAULT 0,
  trend varchar(16) NOT NULL DEFAULT 'watch',
  last_evidence_at timestamptz,
  version int NOT NULL DEFAULT 1,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(child_id, ability_id),
  CHECK (fit_band_min IS NULL OR fit_band_max IS NULL OR fit_band_min <= fit_band_max)
);

CREATE TABLE resource (
  resource_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ability_id varchar(64) NOT NULL REFERENCES ability_node(ability_id),
  resource_type varchar(32) NOT NULL,
  title varchar(256) NOT NULL,
  status varchar(16) NOT NULL DEFAULT 'draft',
  created_by varchar(128),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_resource_ability ON resource(ability_id, status);

CREATE TABLE resource_version (
  resource_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id uuid NOT NULL REFERENCES resource(resource_id),
  version_no int NOT NULL,
  difficulty smallint NOT NULL CHECK (difficulty BETWEEN 1 AND 5),
  task_type varchar(32) NOT NULL,
  content jsonb NOT NULL,
  ui_schema jsonb NOT NULL,
  error_models jsonb NOT NULL DEFAULT '[]'::jsonb,
  hint_policy jsonb NOT NULL,
  mastery_rule jsonb,
  transfer_distance smallint CHECK (transfer_distance BETWEEN 0 AND 4),
  review_status varchar(24) NOT NULL DEFAULT 'draft',
  reviewer_1 varchar(128),
  reviewer_2 varchar(128),
  published_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(resource_id, version_no)
);
CREATE INDEX idx_resource_version_lookup ON resource_version(resource_id, review_status, difficulty);

CREATE TABLE learning_plan (
  plan_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  subject varchar(16) NOT NULL,
  plan_type varchar(32) NOT NULL DEFAULT 'adaptive',
  status varchar(16) NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','completed','cancelled','expired')),
  target_ability_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  fit_band jsonb NOT NULL DEFAULT '{}'::jsonb,
  rationale jsonb NOT NULL DEFAULT '{}'::jsonb,
  generated_by varchar(32) NOT NULL DEFAULT 'curriculum_engine',
  rule_version varchar(32) NOT NULL DEFAULT 'curriculum-v1.3',
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_learning_plan_valid_window CHECK (valid_until IS NULL OR valid_until >= valid_from),
  CONSTRAINT uq_learning_plan_plan_child UNIQUE (plan_id, child_id)
);
CREATE INDEX idx_plan_child_status ON learning_plan(child_id, status, created_at DESC);

CREATE TABLE learning_session (
  session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  subject varchar(16) NOT NULL,
  plan_id uuid,
  CONSTRAINT fk_learning_session_plan FOREIGN KEY (plan_id, child_id) REFERENCES learning_plan(plan_id, child_id) ON DELETE RESTRICT,
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  status varchar(16) NOT NULL DEFAULT 'active'
);
CREATE INDEX idx_session_child_time ON learning_session(child_id, started_at DESC);
CREATE INDEX idx_session_plan ON learning_session(plan_id) WHERE plan_id IS NOT NULL;

CREATE TABLE task_instance (
  task_instance_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES learning_session(session_id),
  child_id uuid NOT NULL REFERENCES child(child_id),
  ability_id varchar(64) NOT NULL REFERENCES ability_node(ability_id),
  resource_version_id uuid NOT NULL REFERENCES resource_version(resource_version_id),
  assigned_difficulty smallint NOT NULL CHECK (assigned_difficulty BETWEEN 1 AND 5),
  strategy_policy jsonb NOT NULL,
  status varchar(16) NOT NULL DEFAULT 'assigned',
  assigned_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);
CREATE INDEX idx_task_child_status ON task_instance(child_id, status, assigned_at);

CREATE TABLE attempt (
  attempt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_instance_id uuid NOT NULL REFERENCES task_instance(task_instance_id),
  attempt_no int NOT NULL,
  response jsonb NOT NULL,
  correct boolean,
  client_elapsed_ms int,
  max_hint_level smallint NOT NULL DEFAULT 0 CHECK (max_hint_level BETWEEN 0 AND 4),
  diagnosis jsonb,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(task_instance_id, attempt_no)
);

CREATE TABLE learning_event (
  event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  session_id uuid REFERENCES learning_session(session_id),
  task_instance_id uuid REFERENCES task_instance(task_instance_id),
  attempt_id uuid REFERENCES attempt(attempt_id),
  agent_turn_id varchar(128),
  event_type varchar(64) NOT NULL,
  seq_no int,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_event_child_time ON learning_event(child_id, occurred_at DESC);
CREATE INDEX idx_event_session_seq ON learning_event(session_id, seq_no);
CREATE INDEX idx_event_task ON learning_event(task_instance_id, event_type);

CREATE TABLE mastery_evidence (
  evidence_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  ability_id varchar(64) NOT NULL REFERENCES ability_node(ability_id),
  task_instance_id uuid REFERENCES task_instance(task_instance_id),
  attempt_id uuid REFERENCES attempt(attempt_id),
  evidence_type varchar(32) NOT NULL CHECK (evidence_type IN ('attempt_standard','attempt_transfer','retention_check','stability_window','transfer_window','explanation')),
  correctness numeric(5,4) CHECK (correctness IS NULL OR correctness BETWEEN 0 AND 1),
  independence numeric(5,4) CHECK (independence IS NULL OR independence BETWEEN 0 AND 1),
  stability numeric(5,4) CHECK (stability IS NULL OR stability BETWEEN 0 AND 1),
  transfer numeric(5,4) CHECK (transfer IS NULL OR transfer BETWEEN 0 AND 1),
  source_evidence_ids uuid[] NOT NULL DEFAULT '{}'::uuid[],
  context_family varchar(64),
  rule_version varchar(32) NOT NULL DEFAULT 'mastery-v1.3',
  valid boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (evidence_type IN ('attempt_standard','attempt_transfer','retention_check','explanation') AND cardinality(source_evidence_ids)=0)
    OR
    (evidence_type IN ('stability_window','transfer_window') AND cardinality(source_evidence_ids)>0)
  )
);
CREATE INDEX idx_evidence_ability_time ON mastery_evidence(child_id, ability_id, occurred_at DESC) WHERE valid=true;

CREATE TABLE growth_snapshot (
  snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  period_type varchar(16) NOT NULL,
  period_start date NOT NULL,
  period_end date NOT NULL,
  metrics jsonb NOT NULL,
  ability_states jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(child_id, period_type, period_start, period_end)
);

CREATE TABLE growth_report (
  report_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  snapshot_id uuid NOT NULL REFERENCES growth_snapshot(snapshot_id),
  report_version int NOT NULL DEFAULT 1,
  content jsonb NOT NULL,
  evidence_refs jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(snapshot_id, report_version)
);

CREATE TABLE consent_record (
  consent_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guardian_id uuid NOT NULL REFERENCES guardian(guardian_id),
  child_id uuid NOT NULL REFERENCES child(child_id),
  consent_type varchar(32) NOT NULL,
  policy_version varchar(32) NOT NULL,
  granted boolean NOT NULL,
  granted_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);
CREATE INDEX idx_consent_child ON consent_record(child_id, consent_type, granted_at DESC);

CREATE TABLE audio_asset (
  audio_asset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  child_id uuid NOT NULL REFERENCES child(child_id),
  task_instance_id uuid REFERENCES task_instance(task_instance_id),
  storage_key varchar(512) NOT NULL,
  duration_ms int,
  consent_id uuid NOT NULL REFERENCES consent_record(consent_id),
  retention_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);


-- V1.3 mastery derivation contract (canonical engineering notes)
-- Atomic evidence: attempt_standard, attempt_transfer, retention_check, explanation.
-- correctness: scorable Attempt maps true=1.0 / false=0.0; partial credit requires a new rule_version.
-- independence from max_hint_level: 0=1.00, 1=0.75, 2=0.50, 3=0.25, 4=0.00.
-- L2->L3 C/I evaluation window: latest 8 valid scorable atomic evidences,
--   requiring >=3 distinct resource_version_id values and >=2 learning_session values.
-- stability MUST be written only by MasteryService as stability_window:
--   latest 5 eligible attempt_standard/retention_check evidence rows,
--   >=3 distinct resource versions and >=2 sessions;
--   each source_quality = correctness * independence; stability = arithmetic mean(source_quality).
-- transfer MUST be written only by MasteryService as transfer_window:
--   latest up to 4 eligible attempt_transfer evidence rows, minimum 2 rows,
--   >=2 distinct context_family values and >=2 sessions;
--   each source_quality = correctness * independence; transfer = arithmetic mean(source_quality).
-- Derived windows require source_evidence_ids and rule_version.
-- Mastery weights: correctness=.35, independence=.25, stability=.20, transfer=.20.
-- Missing required dimensions MUST NOT be renormalized.
-- L2->L3 default gate: score>=.80, C>=.80, I>=.75, S>=.75, T>=.60.
-- L3->L4 default gate: T>=.80, >=3 transfer evidence rows and >=3 context_family values,
--   plus node-specific explanation/transfer gate.
-- Single failure never directly downgrades; downgrade requires review_required + subsequent validation evidence.

-- V1.3 GRAY-01 CLOSED
-- learning_plan MUST exist before learning_session; fk_learning_session_plan MUST be present and validated by migration test.
-- learning_plan rows are lifecycle-managed (completed/cancelled/expired) rather than hard-deleted; FK uses ON DELETE RESTRICT.

-- V1.3 SSOT note: learning_plan and child-safe composite FK are part of the canonical schema.
