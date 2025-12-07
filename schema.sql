-- ============================================
-- 데이터베이스 스키마 생성 SQL
-- PostgreSQL용
-- ============================================

BEGIN;

-- ============================================
-- 1. users 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR NOT NULL UNIQUE,
    telegram_id INTEGER UNIQUE,
    username VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- users 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- ============================================
-- 2. personas 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    description VARCHAR,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_personas_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

-- personas 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_personas_user_id ON personas(user_id);

-- updated_at 자동 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- personas 테이블 updated_at 트리거
DROP TRIGGER IF EXISTS update_personas_updated_at ON personas;
CREATE TRIGGER update_personas_updated_at
    BEFORE UPDATE ON personas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 3. chat_rooms 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS chat_rooms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_chat_id INTEGER NOT NULL UNIQUE,
    name VARCHAR,
    type VARCHAR NOT NULL,
    username VARCHAR,
    persona_id UUID,
    summary VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chat_rooms_persona_id 
        FOREIGN KEY (persona_id) 
        REFERENCES personas(id) 
        ON DELETE SET NULL
);

-- chat_rooms 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_chat_rooms_telegram_chat_id ON chat_rooms(telegram_chat_id);

-- chat_rooms 테이블 updated_at 트리거
DROP TRIGGER IF EXISTS update_chat_rooms_updated_at ON chat_rooms;
CREATE TRIGGER update_chat_rooms_updated_at
    BEFORE UPDATE ON chat_rooms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 4. conversations 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    chat_room_id UUID NOT NULL,
    role VARCHAR NOT NULL,
    message VARCHAR NOT NULL,
    model VARCHAR,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_conversations_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_conversations_chat_room_id 
        FOREIGN KEY (chat_room_id) 
        REFERENCES chat_rooms(id) 
        ON DELETE CASCADE
);

-- conversations 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_chat_room_id ON conversations(chat_room_id);
CREATE INDEX IF NOT EXISTS idx_conversations_model ON conversations(model);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);

-- ============================================
-- 5. usage_logs 테이블 (DEPRECATED)
-- ============================================
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    chat_room_id UUID NOT NULL,
    model VARCHAR NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usage_logs_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_usage_logs_chat_room_id 
        FOREIGN KEY (chat_room_id) 
        REFERENCES chat_rooms(id) 
        ON DELETE CASCADE
);

-- usage_logs 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_chat_room_id ON usage_logs(chat_room_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);

-- ============================================
-- 6. persona_evaluations 테이블
-- ============================================
CREATE TABLE IF NOT EXISTS persona_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona_id UUID NOT NULL,
    user_id UUID NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 5),
    comment VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_persona_evaluations_persona_id 
        FOREIGN KEY (persona_id) 
        REFERENCES personas(id) 
        ON DELETE CASCADE,
    CONSTRAINT fk_persona_evaluations_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    CONSTRAINT uq_persona_user_evaluation UNIQUE (persona_id, user_id)
);

-- persona_evaluations 테이블 인덱스
CREATE INDEX IF NOT EXISTS idx_persona_evaluations_persona_id ON persona_evaluations(persona_id);
CREATE INDEX IF NOT EXISTS idx_persona_evaluations_user_id ON persona_evaluations(user_id);

COMMIT;

-- ============================================
-- 스키마 생성 완료
-- ============================================

