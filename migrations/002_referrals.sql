-- ============================================================
-- 002_referrals.sql
-- Реферальная программа: бонус и другу, и пригласившему при первом визите друга
-- ============================================================

CREATE TYPE referral_status AS ENUM ('pending', 'rewarded');

CREATE TABLE referrals (
    id              SERIAL PRIMARY KEY,
    referrer_id     INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    referred_id     INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    referrer_bonus  INTEGER NOT NULL DEFAULT 150000,  -- сколько получит пригласивший
    referred_bonus  INTEGER NOT NULL DEFAULT 100000,  -- сколько получит приглашённый
    status          referral_status NOT NULL DEFAULT 'pending',
    rewarded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (referred_id)  -- у одного приглашённого может быть только один реферер
);

CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX idx_referrals_status ON referrals(status);
