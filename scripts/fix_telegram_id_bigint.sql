-- Migration: Fix telegram_id overflow (INTEGER to BIGINT)
-- Date: 2025-11-27
-- Issue: Telegram user IDs can exceed int32 max value (2,147,483,647)

BEGIN;

-- Step 1: Alter the telegram_id column type from INTEGER to BIGINT
ALTER TABLE users 
ALTER COLUMN telegram_id TYPE BIGINT;

-- Step 2: Also update chat_rooms table if it has telegram_chat_id
ALTER TABLE chat_rooms 
ALTER COLUMN telegram_chat_id TYPE BIGINT;

COMMIT;
