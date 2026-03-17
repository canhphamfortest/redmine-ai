-- Migration script: Add prompt_token column to openai_usage_log table
-- Date: 2026-02-24
-- Description: Adds a new column to track calculated prompt tokens (max(0, total_tokens - output_token))

-- Add the new column (nullable to allow existing records)
ALTER TABLE openai_usage_log 
ADD COLUMN IF NOT EXISTS prompt_token INTEGER DEFAULT 0;

-- Update existing records: Calculate prompt_token = max(0, total_tokens - output_token)
UPDATE openai_usage_log 
SET prompt_token = GREATEST(0, total_tokens - output_token)
WHERE prompt_token IS NULL OR prompt_token = 0;

-- Add comment to document the column
COMMENT ON COLUMN openai_usage_log.prompt_token IS 'Calculated prompt tokens: max(0, total_tokens - output_token). Used for analytics and comparison with API-provided input_token.';

-- Verify the migration
SELECT 
    'Migration completed. Sample data:' as status,
    COUNT(*) as total_records,
    COUNT(CASE WHEN prompt_token IS NOT NULL THEN 1 END) as records_with_prompt_token,
    COUNT(CASE WHEN prompt_token = 0 THEN 1 END) as records_with_zero_prompt_token
FROM openai_usage_log;

-- Show sample records to verify
SELECT 
    id,
    provider,
    model,
    input_token,
    output_token,
    total_tokens,
    prompt_token,
    created_at
FROM openai_usage_log
ORDER BY created_at DESC
LIMIT 5;
