-- ============================================================
-- 008_wheel_amounts.sql
-- Уменьшаем суммы призов колеса фортуны вдвое
-- ============================================================

UPDATE wheel_prizes SET name = '25 бонусов',  bonus_amount = 25000,  color = '#FF6B6B' WHERE bonus_amount = 50000;
UPDATE wheel_prizes SET name = '50 бонусов',  bonus_amount = 50000,  color = '#FFA94D' WHERE bonus_amount = 100000;
UPDATE wheel_prizes SET name = '100 бонусов', bonus_amount = 100000, color = '#FFD93D' WHERE bonus_amount = 200000;
UPDATE wheel_prizes SET name = '250 бонусов', bonus_amount = 250000, color = '#6BCB77' WHERE bonus_amount = 500000;
UPDATE wheel_prizes SET name = '500 бонусов', bonus_amount = 500000, color = '#9B5DE5' WHERE bonus_amount = 1000000;
UPDATE wheel_prizes SET color = '#374151' WHERE bonus_amount = 0;
