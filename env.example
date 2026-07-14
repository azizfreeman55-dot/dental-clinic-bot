-- ============================================================
-- 001_init.sql
-- Ядро: пациенты, врачи, расписание/слоты, записи, бонусы, уровни
-- Геймификация (колесо, миссии, рефералка, подарки) — отдельными миграциями позже
-- ============================================================

-- ---------- ENUM-типы ----------

CREATE TYPE appointment_status AS ENUM (
    'pending',              -- пациент забронировал слот, ждёт подтверждения админа
    'confirmed',            -- админ подтвердил
    'completed',            -- визит состоялся, бонусы начислены
    'cancelled_by_patient',
    'cancelled_by_admin',
    'no_show'               -- пациент не пришёл
);

CREATE TYPE bonus_tx_type AS ENUM (
    'earn_visit',
    'spend_gift',
    'referral',
    'birthday',
    'manual_admin',
    'refund'
);

CREATE TYPE admin_role AS ENUM ('owner', 'manager');


-- ---------- Уровни лояльности ----------

CREATE TABLE loyalty_levels (
    id                          SERIAL PRIMARY KEY,
    name                        VARCHAR(50) NOT NULL,           -- Bronze, Silver, Gold, Platinum
    min_lifetime_bonus_earned   INTEGER NOT NULL DEFAULT 0,     -- порог входа на уровень
    bonus_percent               NUMERIC(5,2) NOT NULL,          -- % начисления бонусов от чека
    benefits                    JSONB NOT NULL DEFAULT '[]',    -- ["Бесплатная консультация 1 раз в год", ...]
    sort_order                  INTEGER NOT NULL,
    UNIQUE (sort_order)
);

-- ---------- Пациенты ----------

CREATE TABLE patients (
    id                      SERIAL PRIMARY KEY,
    telegram_id             BIGINT NOT NULL UNIQUE,
    phone                   VARCHAR(20),
    full_name               VARCHAR(255) NOT NULL,
    birth_date              DATE,
    language                VARCHAR(5) NOT NULL DEFAULT 'ru',   -- ru / uz

    referrer_id             INTEGER REFERENCES patients(id) ON DELETE SET NULL,

    level_id                INTEGER NOT NULL REFERENCES loyalty_levels(id) DEFAULT 1,
    bonus_balance            INTEGER NOT NULL DEFAULT 0,         -- текущий баланс (можно тратить)
    lifetime_bonus_earned    INTEGER NOT NULL DEFAULT 0,         -- накоплено за всё время (для уровня, не убывает)
    total_visits             INTEGER NOT NULL DEFAULT 0,

    is_blocked                BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_patients_telegram_id ON patients(telegram_id);
CREATE INDEX idx_patients_referrer_id ON patients(referrer_id);

-- ---------- Врачи и услуги ----------

CREATE TABLE doctors (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR(255) NOT NULL,
    specialization  VARCHAR(255) NOT NULL,
    photo_url       TEXT,
    description     TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE services (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    price           NUMERIC(12,2) NOT NULL,
    duration_min    INTEGER NOT NULL,
    category        VARCHAR(100),
    active          BOOLEAN NOT NULL DEFAULT TRUE
);

-- Какой врач какие услуги оказывает (M2M)
CREATE TABLE doctor_services (
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    service_id  INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    PRIMARY KEY (doctor_id, service_id)
);

-- ---------- Шаблон расписания (по дням недели) ----------

CREATE TABLE doctor_schedule_templates (
    id              SERIAL PRIMARY KEY,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    weekday         SMALLINT NOT NULL CHECK (weekday BETWEEN 0 AND 6),  -- 0=понедельник
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    slot_duration_min INTEGER NOT NULL DEFAULT 30,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (end_time > start_time)
);

-- ---------- Сгенерированные слоты (реальный календарь) ----------

CREATE TABLE doctor_slots (
    id              SERIAL PRIMARY KEY,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    is_booked       BOOLEAN NOT NULL DEFAULT FALSE,
    appointment_id  INTEGER,  -- FK добавим ниже, после создания appointments (циклическая ссылка)

    -- защита от гонки: один и тот же слот у врача не может быть создан дважды
    UNIQUE (doctor_id, date, start_time)
);

CREATE INDEX idx_doctor_slots_lookup ON doctor_slots(doctor_id, date, is_booked);

-- ---------- Записи ----------

CREATE TABLE appointments (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(id),
    service_id      INTEGER NOT NULL REFERENCES services(id),
    slot_id         INTEGER NOT NULL REFERENCES doctor_slots(id),

    status          appointment_status NOT NULL DEFAULT 'pending',

    reminder_24h_sent  BOOLEAN NOT NULL DEFAULT FALSE,
    reminder_2h_sent   BOOLEAN NOT NULL DEFAULT FALSE,

    admin_comment   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE doctor_slots
    ADD CONSTRAINT fk_doctor_slots_appointment
    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE SET NULL;

CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_status ON appointments(status);

-- ---------- История лечения (заполняется после completed) ----------

CREATE TABLE treatment_history (
    id              SERIAL PRIMARY KEY,
    appointment_id  INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id       INTEGER NOT NULL REFERENCES doctors(id),
    notes           TEXT,
    amount_paid     NUMERIC(12,2) NOT NULL,
    bonuses_earned  INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_treatment_history_patient ON treatment_history(patient_id);

-- ---------- Бонусные транзакции ----------

CREATE TABLE bonus_transactions (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    amount          INTEGER NOT NULL,           -- может быть отрицательным (списание)
    type            bonus_tx_type NOT NULL,
    description     TEXT,
    related_id      INTEGER,                    -- id appointment / redemption и т.п., без жёсткого FK (полиморфно)
    created_by_admin_id INTEGER,                 -- если начислено вручную
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_bonus_tx_patient ON bonus_transactions(patient_id, created_at DESC);

-- ---------- Админы ----------

CREATE TABLE admins (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT NOT NULL UNIQUE,
    full_name       VARCHAR(255),
    role            admin_role NOT NULL DEFAULT 'manager',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- Триггер: автоматическое начисление/списание баланса
-- при вставке в bonus_transactions + пересчёт уровня.
-- Так баланс никогда не рассинхронизируется с историей транзакций —
-- вся бизнес-логика начисления идёт ЧЕРЕЗ bonus_transactions, не через прямой UPDATE patients.
-- ============================================================

CREATE OR REPLACE FUNCTION apply_bonus_transaction() RETURNS TRIGGER AS $$
DECLARE
    new_level_id INTEGER;
BEGIN
    UPDATE patients
    SET
        bonus_balance = bonus_balance + NEW.amount,
        lifetime_bonus_earned = lifetime_bonus_earned +
            (CASE WHEN NEW.amount > 0 THEN NEW.amount ELSE 0 END)
    WHERE id = NEW.patient_id;

    -- пересчёт уровня по накопленной сумме (только на рост, не понижаем)
    SELECT id INTO new_level_id
    FROM loyalty_levels
    WHERE min_lifetime_bonus_earned <= (
        SELECT lifetime_bonus_earned FROM patients WHERE id = NEW.patient_id
    )
    ORDER BY min_lifetime_bonus_earned DESC
    LIMIT 1;

    UPDATE patients
    SET level_id = new_level_id
    WHERE id = NEW.patient_id AND level_id != new_level_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_apply_bonus_transaction
    AFTER INSERT ON bonus_transactions
    FOR EACH ROW
    EXECUTE FUNCTION apply_bonus_transaction();

-- ---------- Стартовые данные уровней ----------

INSERT INTO loyalty_levels (name, min_lifetime_bonus_earned, bonus_percent, benefits, sort_order) VALUES
    ('Bronze',   0,       5.00, '["Бонусы с каждой оплаты 5%"]', 1),
    ('Silver',   500000,  6.00, '["Бонусы с каждой оплаты 6%", "Приоритетная запись"]', 2),
    ('Gold',     2000000, 7.00, '["Бонусы с каждой оплаты 7%", "Бесплатная консультация 1 раз в год", "Приоритетная запись"]', 3),
    ('Platinum', 7000000, 10.00,'["Бонусы с каждой оплаты 10%", "Бесплатная консультация 1 раз в год", "Приоритетная запись", "Персональный менеджер"]', 4);
