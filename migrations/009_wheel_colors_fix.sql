-- ============================================================
-- 009_wheel_colors_fix.sql
-- Жёстко фиксируем цвет по актуальной (уже применённой) сумме приза —
-- независимо от того, что произошло в 008, здесь пары гарантированно верные.
-- ============================================================

UPDATE wheel_prizes SET color = '#374151' WHERE bonus_amount = 0;
UPDATE wheel_prizes SET color = '#FF6B6B' WHERE bonus_amount = 25000;
UPDATE wheel_prizes SET color = '#FFA94D' WHERE bonus_amount = 50000;
UPDATE wheel_prizes SET color = '#FFD93D' WHERE bonus_amount = 100000;
UPDATE wheel_prizes SET color = '#6BCB77' WHERE bonus_amount = 250000;
UPDATE wheel_prizes SET color = '#9B5DE5' WHERE bonus_amount = 500000;
