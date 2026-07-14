-- ============================================================
-- 012_missions.sql
-- Миссии: разовые или ежемесячные цели с наградой в бонусах
-- ============================================================

ALTER TYPE bonus_tx_type ADD VALUE IF NOT EXISTS 'mission';

CREATE TABLE missions (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    metric          VARCHAR(20) NOT NULL CHECK (metric IN ('referrals', 'visits')),
    target_count    INTEGER NOT NULL CHECK (target_count > 0),
    reward_bonus    INTEGER NOT NULL CHECK (reward_bonus > 0),
    period          VARCHAR(20) NOT NULL DEFAULT 'monthly' CHECK (period IN ('monthly', 'once')),
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE patient_missions (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    mission_id      INTEGER NOT NULL REFERENCES missions(id),
    period_key      VARCHAR(20) NOT NULL,  -- '2026-07' для monthly, 'once' для разовых
    completed       BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    UNIQUE (patient_id, mission_id, period_key)
);

CREATE INDEX idx_patient_missions_patient ON patient_missions(patient_id);

INSERT INTO missions (code, name, description, metric, target_count, reward_bonus, period, sort_order) VALUES
    ('refer_2_friends',  'Приведи 2 друзей',   'Пригласите 2 друзей за месяц, и оба должны посетить клинику',  'referrals', 2, 500000, 'monthly', 1),
    ('three_visits',     '3 визита за месяц',   'Посетите клинику 3 раза в течение месяца',                     'visits',    3, 200000, 'monthly', 2);
