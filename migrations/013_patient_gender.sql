-- ============================================================
-- 013_patient_gender.sql
-- Добавляем пол пациента для регистрации в Mini App
-- ============================================================

ALTER TABLE patients ADD COLUMN gender VARCHAR(10) CHECK (gender IN ('male', 'female'));
