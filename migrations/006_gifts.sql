-- ============================================================
-- 006_gifts.sql
-- Каталог подарков за бонусы + погашения
-- ============================================================

CREATE TYPE redemption_status AS ENUM ('pending', 'used', 'expired');

CREATE TABLE gifts_catalog (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    cost_bonuses    INTEGER NOT NULL CHECK (cost_bonuses > 0),
    category        VARCHAR(100),
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    image_url       TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE gift_redemptions (
    id              SERIAL PRIMARY KEY,
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    gift_id         INTEGER NOT NULL REFERENCES gifts_catalog(id),
    cost_bonuses    INTEGER NOT NULL,  -- фиксируем цену на момент погашения (каталог может измениться позже)
    status          redemption_status NOT NULL DEFAULT 'pending',
    redeemed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at         TIMESTAMPTZ
);

CREATE INDEX idx_gift_redemptions_patient ON gift_redemptions(patient_id);
CREATE INDEX idx_gift_redemptions_status ON gift_redemptions(status);

-- ---------- Стартовый каталог, на основе реального прайса клиники ----------

INSERT INTO gifts_catalog (name, description, cost_bonuses, category, sort_order) VALUES
    ('Профессиональная чистка зубов', 'Бесплатная чистка в подарок', 300000, 'Услуги', 1),
    ('Отбеливание голливудское (1 зуб)', 'Отбеливание одного зуба бесплатно', 25000, 'Услуги', 2),
    ('Скидка 20% на любую услугу', 'Разовый сертификат на скидку 20%, показать администратору', 100000, 'Скидки', 3),
    ('Скидка 10% на любую услугу', 'Разовый сертификат на скидку 10%, показать администратору', 50000, 'Скидки', 4);
