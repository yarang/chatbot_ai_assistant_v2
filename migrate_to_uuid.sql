-- ============================================
-- String 타입 ID를 UUID 타입으로 마이그레이션
-- PostgreSQL용
-- 주의: 기존 데이터가 있는 경우에만 실행하세요!
-- ============================================

BEGIN;

-- ============================================
-- 1. users 테이블 마이그레이션
-- ============================================
-- 기존 id 컬럼이 VARCHAR인 경우에만 실행
DO $$
BEGIN
    -- id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'id' 
        AND data_type = 'character varying'
    ) THEN
        -- 임시 컬럼 생성
        ALTER TABLE users ADD COLUMN IF NOT EXISTS id_new UUID;
        
        -- 기존 데이터 변환 (유효한 UUID 문자열만 변환)
        UPDATE users 
        SET id_new = id::UUID 
        WHERE id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        
        -- 기존 컬럼 삭제 및 새 컬럼으로 교체
        ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey CASCADE;
        ALTER TABLE users DROP COLUMN IF EXISTS id;
        ALTER TABLE users RENAME COLUMN id_new TO id;
        ALTER TABLE users ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE users ADD PRIMARY KEY (id);
    END IF;
END $$;

-- ============================================
-- 2. personas 테이블 마이그레이션
-- ============================================
DO $$
BEGIN
    -- id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'personas' 
        AND column_name = 'id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE personas ADD COLUMN IF NOT EXISTS id_new UUID;
        UPDATE personas SET id_new = id::UUID 
        WHERE id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE personas DROP CONSTRAINT IF EXISTS personas_pkey CASCADE;
        ALTER TABLE personas DROP COLUMN IF EXISTS id;
        ALTER TABLE personas RENAME COLUMN id_new TO id;
        ALTER TABLE personas ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE personas ADD PRIMARY KEY (id);
    END IF;
    
    -- user_id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'personas' 
        AND column_name = 'user_id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE personas DROP CONSTRAINT IF EXISTS fk_personas_user_id;
        ALTER TABLE personas ADD COLUMN IF NOT EXISTS user_id_new UUID;
        UPDATE personas SET user_id_new = user_id::UUID 
        WHERE user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE personas DROP COLUMN IF EXISTS user_id;
        ALTER TABLE personas RENAME COLUMN user_id_new TO user_id;
        ALTER TABLE personas ALTER COLUMN user_id SET NOT NULL;
        ALTER TABLE personas ADD CONSTRAINT fk_personas_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS idx_personas_user_id ON personas(user_id);
    END IF;
END $$;

-- ============================================
-- 3. chat_rooms 테이블 마이그레이션
-- ============================================
DO $$
BEGIN
    -- id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'chat_rooms' 
        AND column_name = 'id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat_rooms ADD COLUMN IF NOT EXISTS id_new UUID;
        UPDATE chat_rooms SET id_new = id::UUID 
        WHERE id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE chat_rooms DROP CONSTRAINT IF EXISTS chat_rooms_pkey CASCADE;
        ALTER TABLE chat_rooms DROP COLUMN IF EXISTS id;
        ALTER TABLE chat_rooms RENAME COLUMN id_new TO id;
        ALTER TABLE chat_rooms ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE chat_rooms ADD PRIMARY KEY (id);
    END IF;
    
    -- persona_id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'chat_rooms' 
        AND column_name = 'persona_id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE chat_rooms DROP CONSTRAINT IF EXISTS fk_chat_rooms_persona_id;
        ALTER TABLE chat_rooms ADD COLUMN IF NOT EXISTS persona_id_new UUID;
        UPDATE chat_rooms SET persona_id_new = persona_id::UUID 
        WHERE persona_id IS NOT NULL 
        AND persona_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE chat_rooms DROP COLUMN IF EXISTS persona_id;
        ALTER TABLE chat_rooms RENAME COLUMN persona_id_new TO persona_id;
        ALTER TABLE chat_rooms ADD CONSTRAINT fk_chat_rooms_persona_id 
            FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================
-- 4. conversations 테이블 마이그레이션
-- ============================================
DO $$
BEGIN
    -- id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'conversations' 
        AND column_name = 'id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS id_new UUID;
        UPDATE conversations SET id_new = id::UUID 
        WHERE id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_pkey CASCADE;
        ALTER TABLE conversations DROP COLUMN IF EXISTS id;
        ALTER TABLE conversations RENAME COLUMN id_new TO id;
        ALTER TABLE conversations ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE conversations ADD PRIMARY KEY (id);
    END IF;
    
    -- user_id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'conversations' 
        AND column_name = 'user_id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE conversations DROP CONSTRAINT IF EXISTS fk_conversations_user_id;
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id_new UUID;
        UPDATE conversations SET user_id_new = user_id::UUID 
        WHERE user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE conversations DROP COLUMN IF EXISTS user_id;
        ALTER TABLE conversations RENAME COLUMN user_id_new TO user_id;
        ALTER TABLE conversations ALTER COLUMN user_id SET NOT NULL;
        ALTER TABLE conversations ADD CONSTRAINT fk_conversations_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
    END IF;
    
    -- chat_room_id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'conversations' 
        AND column_name = 'chat_room_id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE conversations DROP CONSTRAINT IF EXISTS fk_conversations_chat_room_id;
        ALTER TABLE conversations ADD COLUMN IF NOT EXISTS chat_room_id_new UUID;
        UPDATE conversations SET chat_room_id_new = chat_room_id::UUID 
        WHERE chat_room_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE conversations DROP COLUMN IF EXISTS chat_room_id;
        ALTER TABLE conversations RENAME COLUMN chat_room_id_new TO chat_room_id;
        ALTER TABLE conversations ALTER COLUMN chat_room_id SET NOT NULL;
        ALTER TABLE conversations ADD CONSTRAINT fk_conversations_chat_room_id 
            FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS idx_conversations_chat_room_id ON conversations(chat_room_id);
    END IF;
END $$;

-- ============================================
-- 5. usage_logs 테이블 마이그레이션
-- ============================================
DO $$
BEGIN
    -- id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'usage_logs' 
        AND column_name = 'id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS id_new UUID;
        UPDATE usage_logs SET id_new = id::UUID 
        WHERE id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS usage_logs_pkey CASCADE;
        ALTER TABLE usage_logs DROP COLUMN IF EXISTS id;
        ALTER TABLE usage_logs RENAME COLUMN id_new TO id;
        ALTER TABLE usage_logs ALTER COLUMN id SET DEFAULT gen_random_uuid();
        ALTER TABLE usage_logs ADD PRIMARY KEY (id);
    END IF;
    
    -- user_id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'usage_logs' 
        AND column_name = 'user_id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS fk_usage_logs_user_id;
        ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS user_id_new UUID;
        UPDATE usage_logs SET user_id_new = user_id::UUID 
        WHERE user_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE usage_logs DROP COLUMN IF EXISTS user_id;
        ALTER TABLE usage_logs RENAME COLUMN user_id_new TO user_id;
        ALTER TABLE usage_logs ALTER COLUMN user_id SET NOT NULL;
        ALTER TABLE usage_logs ADD CONSTRAINT fk_usage_logs_user_id 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
    END IF;
    
    -- chat_room_id 컬럼이 VARCHAR인지 확인
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'usage_logs' 
        AND column_name = 'chat_room_id' 
        AND data_type = 'character varying'
    ) THEN
        ALTER TABLE usage_logs DROP CONSTRAINT IF EXISTS fk_usage_logs_chat_room_id;
        ALTER TABLE usage_logs ADD COLUMN IF NOT EXISTS chat_room_id_new UUID;
        UPDATE usage_logs SET chat_room_id_new = chat_room_id::UUID 
        WHERE chat_room_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
        ALTER TABLE usage_logs DROP COLUMN IF EXISTS chat_room_id;
        ALTER TABLE usage_logs RENAME COLUMN chat_room_id_new TO chat_room_id;
        ALTER TABLE usage_logs ALTER COLUMN chat_room_id SET NOT NULL;
        ALTER TABLE usage_logs ADD CONSTRAINT fk_usage_logs_chat_room_id 
            FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS idx_usage_logs_chat_room_id ON usage_logs(chat_room_id);
    END IF;
END $$;

COMMIT;

-- ============================================
-- 마이그레이션 완료
-- ============================================

