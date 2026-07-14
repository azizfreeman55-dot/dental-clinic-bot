-- ============================================================
-- 010_wheel_names_fix.sql
-- Полные суммы в названиях призов ("25 000 бонусов", а не "25 бонусов")
-- ============================================================

UPDATE wheel_prizes SET name = '25 000 бонусов'  WHERE bonus_amount = 25000;
UPDATE wheel_prizes SET name = '50 000 бонусов'  WHERE bonus_amount = 50000;
UPDATE wheel_prizes SET name = '100 000 бонусов' WHERE bonus_amount = 100000;
UPDATE wheel_prizes SET name = '250 000 бонусов' WHERE bonus_amount = 250000;
UPDATE wheel_prizes SET name = '500 000 бонусов' WHERE bonus_amount = 500000;
