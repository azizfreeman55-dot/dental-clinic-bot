-- ============================================================
-- 007_wheel.sql
-- Колесо фортуны: призы в виде бонусов, вращение даётся за завершённый визит
-- ============================================================

ALTER TYPE bonus_tx_type ADD VALUE IF NOT EXISTS 'wheel';

CREATE TABLE wheel_prizes (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    bonus_amount    INTEGER NOT NULL DEFAULT 0 CHECK (bonus_amount >= 0),
    weight          INTEGER NOT NULL CHECK (weight > 0),  -- относительная вероятность выпадения
    color           VARCHAR(20) NOT NULL DEFAULT '#2f6fed',
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE patient_wheel_credits (
    patient_id      INTEGER PRIMARY KEY REFERENCES patients(id) ON DELETE CASCADE,
    spins_available INTEGER NOT NULL DEFAULT 0 CHECK (spins_available >= 0)
);

CREATE TABLE wheel_spins (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    prize_id        INTEGER NOT NULL REFERENCES wheel_prizes(id),
    bonus_amount    INTEGER NOT NULL,
    spun_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_wheel_spins_patient ON wheel_spins(patient_id);

-- ---------- Призы (6 секторов) ----------

INSERT INTO wheel_prizes (name, bonus_amount, weight, color) VALUES
    ('Не повезло',        0,       20, '#4a5568'),
    ('50 бонусов',        50000,   25, '#2f6fed'),
    ('100 бонусов',       100000,  20, '#8ce35a'),
    ('200 бонусов',       200000,  15, '#f6ad55'),
    ('500 бонусов',       500000,  12, '#e5484d'),
    ('1000 бонусов',      1000000, 8,  '#a78bfa');
