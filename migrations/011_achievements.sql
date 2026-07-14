-- ============================================================
-- 011_achievements.sql
-- Достижения: постоянные бейджи за визиты, уровень, рефералов
-- ============================================================

CREATE TABLE achievements (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    icon            VARCHAR(10) NOT NULL DEFAULT '🏆',
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE patient_achievements (
    patient_id      INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    achievement_id  INTEGER NOT NULL REFERENCES achievements(id),
    earned_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (patient_id, achievement_id)
);

INSERT INTO achievements (code, name, description, icon, sort_order) VALUES
    ('first_visit',    'Первый визит',        'Посетили клинику в первый раз',                 '🦷', 1),
    ('friend_bringer',  'Привёл друга',         'Пригласили друга, и он посетил клинику',       '👥', 2),
    ('loyal_client',    'Постоянный клиент',    'Завершили 5 визитов в клинике',                '⭐', 3),
    ('best_client',      'Лучший клиент',        'Завершили 10 визитов в клинике',               '💎', 4),
    ('gold_level',       'VIP пациент',          'Достигли уровня Gold',                          '🥇', 5),
    ('platinum_level',   'Платиновый клиент',    'Достигли максимального уровня Platinum',       '👑', 6);
