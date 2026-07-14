-- ============================================================
-- seed_test_data.sql
-- Тестовые данные для проверки цепочки записи.
-- Применять ПОСЛЕ 001_init.sql. Можно удалить/не использовать в проде.
-- ============================================================

INSERT INTO services (name, description, price, duration_min, category) VALUES
    ('Профессиональная чистка зубов', 'Ультразвуковая чистка + полировка', 350000, 45, 'Гигиена'),
    ('Отбеливание зубов', 'Кабинетное отбеливание', 900000, 60, 'Эстетика'),
    ('Бесплатный осмотр', 'Первичная консультация', 0, 30, 'Диагностика'),
    ('Лечение кариеса', 'Пломбирование одного зуба', 450000, 60, 'Лечение');

INSERT INTO doctors (full_name, specialization, description, active) VALUES
    ('Азимова Малика Рустамовна', 'Стоматолог-терапевт', 'Стаж 8 лет', TRUE),
    ('Каримов Бехзод Анварович', 'Стоматолог-гигиенист', 'Стаж 5 лет', TRUE);

-- Связываем врачей с услугами: терапевт лечит + осматривает, гигиенист — чистка/отбеливание
INSERT INTO doctor_services (doctor_id, service_id)
SELECT d.id, s.id FROM doctors d, services s
WHERE d.full_name = 'Азимова Малика Рустамовна'
  AND s.name IN ('Бесплатный осмотр', 'Лечение кариеса');

INSERT INTO doctor_services (doctor_id, service_id)
SELECT d.id, s.id FROM doctors d, services s
WHERE d.full_name = 'Каримов Бехзод Анварович'
  AND s.name IN ('Профессиональная чистка зубов', 'Отбеливание зубов');

-- Расписание: терапевт Пн-Пт 9:00-15:00, гигиенист Пн-Сб 10:00-18:00
INSERT INTO doctor_schedule_templates (doctor_id, weekday, start_time, end_time, slot_duration_min)
SELECT d.id, weekday, '09:00', '15:00', 30
FROM doctors d, generate_series(0, 4) AS weekday  -- 0=Пн ... 4=Пт
WHERE d.full_name = 'Азимова Малика Рустамовна';

INSERT INTO doctor_schedule_templates (doctor_id, weekday, start_time, end_time, slot_duration_min)
SELECT d.id, weekday, '10:00', '18:00', 30
FROM doctors d, generate_series(0, 5) AS weekday  -- 0=Пн ... 5=Сб
WHERE d.full_name = 'Каримов Бехзод Анварович';

-- Себя добавляем админом через переменную окружения ADMIN_TELEGRAM_ID на Render —
-- см. database/queries/admin.py: ensure_admin(), вызывается при каждом старте бота.
-- Ничего вручную редактировать здесь не нужно.
