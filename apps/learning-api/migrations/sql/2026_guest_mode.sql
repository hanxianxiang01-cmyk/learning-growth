-- 游客模式 P1/P2 增量 DDL（V1.4 纯游客模式设计方案）
--
-- 定位：**增量脚本，不修改 baselines/learning-core-v1.3.1/01_schema_postgresql_v1.3.1.sql**。
-- 前置：基线 18 张表已建好（child / guardian 已存在且被 9 张表外键引用）。
-- 可重复执行（全部 IF NOT EXISTS）。
--
-- 关系：一个游客 = 一行 guardian + 一行 child + 一行 guest_identity。
-- guest_identity.child_id 即方案里的 guest_id；不引入第二个身份标识。
--
-- 与基线表的关系只有两条外键（都指向 child），不新增任何基线表列。

BEGIN;

CREATE TABLE IF NOT EXISTS guest_identity (
  child_id         uuid PRIMARY KEY REFERENCES child(child_id) ON DELETE CASCADE,
  created_at       timestamptz NOT NULL DEFAULT now(),
  last_activity_at timestamptz NOT NULL DEFAULT now(),
  expires_at       timestamptz NOT NULL,
  status           varchar(16) NOT NULL DEFAULT 'active',
  CONSTRAINT guest_identity_status_check
    CHECK (status IN ('active','expired','purged')),
  CONSTRAINT guest_identity_expires_after_create
    CHECK (expires_at >= created_at)
);
CREATE INDEX IF NOT EXISTS idx_guest_identity_expires
  ON guest_identity(expires_at) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS guest_session (
  session_token_hash varchar(64) PRIMARY KEY,
  child_id           uuid NOT NULL REFERENCES guest_identity(child_id) ON DELETE CASCADE,
  created_at         timestamptz NOT NULL DEFAULT now(),
  last_seen_at       timestamptz NOT NULL DEFAULT now(),
  expires_at         timestamptz NOT NULL,
  revoked_at         timestamptz
);
CREATE INDEX IF NOT EXISTS idx_guest_session_child ON guest_session(child_id);

CREATE TABLE IF NOT EXISTS guest_daily_quota (
  child_id         uuid NOT NULL REFERENCES guest_identity(child_id) ON DELETE CASCADE,
  task_instance_id uuid NOT NULL,
  quota_date       date NOT NULL,
  counted_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (child_id, task_instance_id)
);
CREATE INDEX IF NOT EXISTS idx_guest_quota_day ON guest_daily_quota(child_id, quota_date);

CREATE TABLE IF NOT EXISTS guest_cleanup_run (
  run_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  scanned     int NOT NULL DEFAULT 0,
  purged      int NOT NULL DEFAULT 0,
  failed      int NOT NULL DEFAULT 0,
  status      varchar(16) NOT NULL DEFAULT 'running',
  detail      jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT guest_cleanup_run_status_check
    CHECK (status IN ('running','succeeded','partial','failed'))
);
CREATE INDEX IF NOT EXISTS idx_guest_cleanup_run_started ON guest_cleanup_run(started_at DESC);

COMMIT;