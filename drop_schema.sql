-- ============================================
-- 데이터베이스 스키마 삭제 SQL
-- PostgreSQL용
-- 주의: 모든 데이터가 삭제됩니다!
-- ============================================

BEGIN;

-- 외래키 제약조건 때문에 역순으로 삭제
DROP TABLE IF EXISTS usage_logs CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS chat_rooms CASCADE;
DROP TABLE IF EXISTS personas CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 트리거 함수 삭제
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

COMMIT;

-- ============================================
-- 스키마 삭제 완료
-- ============================================

