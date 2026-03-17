-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Source table
CREATE TABLE IF NOT EXISTS source (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT NOT NULL,
    external_id TEXT,
    external_url TEXT,
    project_key TEXT,
    project_id INTEGER,
    language TEXT DEFAULT 'en',
    sha1_content TEXT,
    -- Sync tracking fields (merged from issue_sync_log)
    sync_status TEXT DEFAULT 'success', -- 'pending', 'success', 'failed', 'outdated'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_type, external_id)
);

-- Source detail tables
CREATE TABLE IF NOT EXISTS source_redmine_issue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES source(id) ON DELETE CASCADE,
    tracker_id INTEGER,
    tracker_name TEXT,
    status_id INTEGER,
    status_name TEXT,
    status_is_closed BOOLEAN,
    priority_id INTEGER,
    priority_name TEXT,
    category_id INTEGER,
    category_name TEXT,
    author_id INTEGER,
    author_name TEXT,
    assigned_to_id INTEGER,
    assigned_to_name TEXT,
    fixed_version_id INTEGER,
    fixed_version_name TEXT,
    parent_issue_id INTEGER,
    estimated_hours FLOAT,
    done_ratio INTEGER,
    start_date DATE,
    due_date DATE,
    closed_on TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS source_redmine_wiki (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES source(id) ON DELETE CASCADE,
    wiki_version INTEGER,
    parent_page_title TEXT,
    author_id INTEGER,
    author_name TEXT,
    comments TEXT,
    redmine_project_id INTEGER,
    redmine_project_name TEXT
);

CREATE TABLE IF NOT EXISTS source_git_file (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES source(id) ON DELETE CASCADE,
    repository_name TEXT,
    repository_url TEXT,
    branch TEXT,
    commit_hash TEXT,
    commit_short_hash TEXT,
    commit_author_name TEXT,
    commit_author_email TEXT,
    commit_date TIMESTAMPTZ,
    commit_message TEXT,
    file_extension TEXT,
    file_type TEXT,
    file_size_bytes BIGINT,
    line_count INTEGER
);

CREATE TABLE IF NOT EXISTS source_document (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES source(id) ON DELETE CASCADE,
    filename TEXT,
    mime_type TEXT,
    file_size_bytes BIGINT,
    page_count INTEGER,
    author TEXT,
    created_date TIMESTAMPTZ,
    modified_date TIMESTAMPTZ,
    source_location TEXT
);

-- Chunk table
CREATE TABLE IF NOT EXISTS chunk (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES source(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    chunk_type TEXT DEFAULT 'text',
    text_content TEXT NOT NULL,
    token_count INTEGER,
    status TEXT DEFAULT 'pending',
    
    -- Context metadata
    heading_title TEXT,
    heading_level INTEGER,
    author_id INTEGER,
    author_name TEXT,
    created_on TIMESTAMPTZ,
    
    -- Journal/comment specific
    journal_id INTEGER,
    is_private BOOLEAN DEFAULT FALSE,
    
    -- Code specific
    code_language TEXT,
    function_name TEXT,
    class_name TEXT,
    line_start INTEGER,
    line_end INTEGER,
    
    -- Document specific
    page_number INTEGER,
    
    -- Wiki specific
    wiki_version INTEGER,
    section_index INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Embedding table
CREATE TABLE IF NOT EXISTS embedding (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID REFERENCES chunk(id) ON DELETE CASCADE,
    embedding VECTOR(1024),
    model_name TEXT DEFAULT 'mixedbread-ai/mxbai-embed-large-v1',
    quality_score FLOAT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chunk_id)
);

-- Search log
CREATE TABLE IF NOT EXISTS search_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT,
    query TEXT NOT NULL,
    filters JSONB,
    top_chunk_ids UUID[],
    response_time_ms INTEGER,
    usage_log_id UUID REFERENCES openai_usage_log(id) ON DELETE SET NULL,
    generation_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job scheduling tables
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name TEXT NOT NULL,
    job_type TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    items_processed INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    execution_log JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM Usage Log (supports multiple providers: openai, google, anthropic, groq)
-- Note: Table name kept as 'openai_usage_log' for backward compatibility
CREATE TABLE IF NOT EXISTS openai_usage_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider TEXT NOT NULL DEFAULT 'openai',  -- openai, google, anthropic, groq
    model TEXT NOT NULL,
    input_token INTEGER NOT NULL DEFAULT 0,
    output_token INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd FLOAT NOT NULL DEFAULT 0.0,
    user_query TEXT,
    cached BOOLEAN DEFAULT FALSE,
    response_time_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM Usage Log Detail - Store prompt and response details
-- Note: Table name kept as 'openai_usage_log_detail' for backward compatibility
CREATE TABLE IF NOT EXISTS openai_usage_log_detail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usage_log_id UUID NOT NULL REFERENCES openai_usage_log(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM Config - Store model pricing configuration (supports multiple providers)
-- Note: Table name kept as 'openai_config' for backward compatibility
CREATE TABLE IF NOT EXISTS openai_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider TEXT NOT NULL DEFAULT 'openai',  -- openai, google, anthropic, groq
    model_name TEXT NOT NULL UNIQUE,
    input_price_per_1m FLOAT NOT NULL,
    output_price_per_1m FLOAT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    description TEXT,
    api_key TEXT,      -- Optional: per-model API key override (encrypted in production)
    base_url TEXT,     -- Optional: custom endpoint URL (for Azure, self-hosted, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- account table for user authentication
CREATE TABLE IF NOT EXISTS account (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    hashed_password TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);


-- Create indexes
CREATE INDEX IF NOT EXISTS idx_source_type ON source(source_type);
CREATE INDEX IF NOT EXISTS idx_source_project ON source(project_key);
CREATE INDEX IF NOT EXISTS idx_source_project_id ON source(project_id);
CREATE INDEX IF NOT EXISTS idx_chunk_source ON chunk(source_id);
CREATE INDEX IF NOT EXISTS idx_embedding_chunk ON embedding(chunk_id);

-- Full-text search index for hybrid search (keyword matching)
-- This enables fast keyword search without additional AI cost
-- Using 'simple' config for better Vietnamese and mixed language support
CREATE INDEX IF NOT EXISTS idx_chunk_text_fts ON chunk 
    USING gin(to_tsvector('simple', coalesce(text_content, '')));

-- Vector similarity search index (IVFFlat for better performance on large datasets)
CREATE INDEX IF NOT EXISTS idx_embedding_vector ON embedding 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Job indexes
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_active ON scheduled_jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_job_executions_job_id ON job_executions(job_id);
CREATE INDEX IF NOT EXISTS idx_job_executions_started ON job_executions(started_at DESC);

-- Search log indexes
CREATE INDEX IF NOT EXISTS idx_search_log_created ON search_log(created_at DESC);

-- LLM Usage indexes
CREATE INDEX IF NOT EXISTS idx_openai_usage_created ON openai_usage_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_openai_usage_model ON openai_usage_log(model);
CREATE INDEX IF NOT EXISTS idx_openai_usage_provider ON openai_usage_log(provider);

-- OpenAI Usage Log Detail indexes
CREATE INDEX IF NOT EXISTS idx_openai_usage_log_detail_usage_log_id ON openai_usage_log_detail(usage_log_id);
CREATE INDEX IF NOT EXISTS idx_openai_usage_log_detail_created ON openai_usage_log_detail(created_at DESC);

-- LLM Config indexes
CREATE INDEX IF NOT EXISTS idx_openai_config_model ON openai_config(model_name);
CREATE INDEX IF NOT EXISTS idx_openai_config_active ON openai_config(is_active);
CREATE INDEX IF NOT EXISTS idx_openai_config_default ON openai_config(is_default);
CREATE INDEX IF NOT EXISTS idx_openai_config_provider ON openai_config(provider);

-- account indexes
CREATE INDEX IF NOT EXISTS idx_account_username ON account(username);
CREATE INDEX IF NOT EXISTS idx_account_email ON account(email);
CREATE INDEX IF NOT EXISTS idx_account_active ON account(is_active);

-- Source sync indexes
CREATE INDEX IF NOT EXISTS idx_source_sync_status ON source(sync_status);
CREATE INDEX IF NOT EXISTS idx_source_last_sync ON source(last_sync_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_type_sync_status ON source(source_type, sync_status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers
CREATE TRIGGER update_source_updated_at BEFORE UPDATE ON source
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chunk_updated_at BEFORE UPDATE ON chunk
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_embedding_updated_at BEFORE UPDATE ON embedding
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_openai_config_updated_at BEFORE UPDATE ON openai_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_account_updated_at BEFORE UPDATE ON account
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default LLM config values based on current pricing
-- Note: Prices stored as per-token (per 1M tokens divided by 1M)
-- Format: input_price_per_1m = price_per_1M_tokens / 1000000
-- Set gpt-4o-mini as default model
--
-- IMPORTANT: API keys and base_url are NOT set here (they are NULL by default)
-- To set API keys from environment variables, run:
--   python scripts/update_llm_api_keys.py
-- Or set them manually via the UI (Streamlit) or API

-- OpenAI Models
INSERT INTO openai_config (id, provider, model_name, input_price_per_1m, output_price_per_1m, is_default, description) VALUES
    (uuid_generate_v4(), 'openai', 'gpt-4o-mini', 0.00000015, 0.0000006, TRUE, 'GPT-4o Mini model'),
    (uuid_generate_v4(), 'openai', 'gpt-4o', 0.0000025, 0.00001, FALSE, 'GPT-4o model'),
    (uuid_generate_v4(), 'openai', 'gpt-4o-2024-08-06', 0.0000025, 0.00001, FALSE, 'GPT-4o snapshot from 2024-08-06'),
    (uuid_generate_v4(), 'openai', 'gpt-4-turbo', 0.00001, 0.00003, FALSE, 'GPT-4 Turbo model'),
    (uuid_generate_v4(), 'openai', 'gpt-4-turbo-preview', 0.00001, 0.00003, FALSE, 'GPT-4 Turbo Preview'),
    (uuid_generate_v4(), 'openai', 'gpt-4', 0.00003, 0.00006, FALSE, 'GPT-4 model'),
    (uuid_generate_v4(), 'openai', 'gpt-4-32k', 0.00006, 0.00012, FALSE, 'GPT-4 32k model'),
    (uuid_generate_v4(), 'openai', 'gpt-3.5-turbo', 0.0000005, 0.0000015, FALSE, 'GPT-3.5 Turbo (legacy)'),
    (uuid_generate_v4(), 'openai', 'gpt-5-nano', 0.00000005, 0.0000004, FALSE, 'GPT-5 Nano model'),
    (uuid_generate_v4(), 'openai', 'gpt-5', 0.000002, 0.000008, FALSE, 'GPT-5 model'),
    (uuid_generate_v4(), 'openai', 'o1-preview', 0.000015, 0.00006, FALSE, 'o1 Preview reasoning model'),
    (uuid_generate_v4(), 'openai', 'o1-mini', 0.000003, 0.000012, FALSE, 'o1 Mini reasoning model')
ON CONFLICT (model_name) DO NOTHING;

-- Google Gemini Models (using new SDK google-genai)
-- Note: SDK mới sử dụng REST API thay vì gRPC, model names phải đúng với API v1beta
-- Pricing updated from: https://ai.google.dev/gemini-api/docs/pricing
-- See: https://ai.google.dev/gemini-api/docs/quickstart
INSERT INTO openai_config (id, provider, model_name, input_price_per_1m, output_price_per_1m, is_default, description) VALUES
    -- Gemini 3 series (Preview)
    (uuid_generate_v4(), 'google', 'gemini-3-pro-preview', 0.000002, 0.000012, FALSE, 'Gemini 3 Pro Preview - Most powerful model (<= 200k tokens pricing)'),
    (uuid_generate_v4(), 'google', 'gemini-3-flash-preview', 0.0000005, 0.000003, FALSE, 'Gemini 3 Flash Preview - Fast and intelligent (text/image/video pricing)'),
    -- Gemini 2.5 series
    (uuid_generate_v4(), 'google', 'gemini-2.5-flash', 0.000000075, 0.0000003, TRUE, 'Gemini 2.5 Flash - Latest, fast and efficient (recommended)'),
    -- Gemini 2.0 series
    (uuid_generate_v4(), 'google', 'gemini-2.0-flash', 0.000000075, 0.0000003, FALSE, 'Gemini 2.0 Flash - Fast and efficient'),
    -- Gemini 1.5 series
    (uuid_generate_v4(), 'google', 'gemini-1.5-pro', 0.0000035, 0.0000105, FALSE, 'Gemini 1.5 Pro - Best for complex tasks'),
    (uuid_generate_v4(), 'google', 'gemini-1.5-flash', 0.000000075, 0.0000003, FALSE, 'Gemini 1.5 Flash - Fast and efficient'),
    -- Gemini 1.0 series (legacy)
    (uuid_generate_v4(), 'google', 'gemini-1.0-pro', 0.0000005, 0.0000015, FALSE, 'Gemini 1.0 Pro - Legacy model'),
    (uuid_generate_v4(), 'google', 'gemini-pro', 0.0000005, 0.0000015, FALSE, 'Gemini Pro (alias for gemini-1.0-pro)')
ON CONFLICT (model_name) DO UPDATE SET 
    is_default = CASE WHEN EXCLUDED.is_default = TRUE THEN TRUE ELSE openai_config.is_default END,
    description = EXCLUDED.description;

-- Anthropic Claude Models
INSERT INTO openai_config (id, provider, model_name, input_price_per_1m, output_price_per_1m, is_default, description) VALUES
    (uuid_generate_v4(), 'anthropic', 'claude-3-opus-20240229', 0.000015, 0.000075, FALSE, 'Claude 3 Opus - Most powerful'),
    (uuid_generate_v4(), 'anthropic', 'claude-3-sonnet-20240229', 0.000003, 0.000015, FALSE, 'Claude 3 Sonnet - Balanced'),
    (uuid_generate_v4(), 'anthropic', 'claude-3-haiku-20240307', 0.00000025, 0.00000125, FALSE, 'Claude 3 Haiku - Fast and cheap'),
    (uuid_generate_v4(), 'anthropic', 'claude-3-5-sonnet-20241022', 0.000003, 0.000015, FALSE, 'Claude 3.5 Sonnet - Latest'),
    (uuid_generate_v4(), 'anthropic', 'claude-3-5-haiku-20241022', 0.000001, 0.000005, FALSE, 'Claude 3.5 Haiku - Latest fast')
ON CONFLICT (model_name) DO NOTHING;

-- Groq Models (fast inference)
INSERT INTO openai_config (id, provider, model_name, input_price_per_1m, output_price_per_1m, is_default, description) VALUES
    (uuid_generate_v4(), 'groq', 'llama-3.3-70b-versatile', 0.00000059, 0.00000079, FALSE, 'Llama 3.3 70B on Groq'),
    (uuid_generate_v4(), 'groq', 'llama-3.1-8b-instant', 0.00000005, 0.00000008, FALSE, 'Llama 3.1 8B on Groq - Very fast'),
    (uuid_generate_v4(), 'groq', 'llama-3.2-90b-vision-preview', 0.0000009, 0.0000009, FALSE, 'Llama 3.2 90B Vision on Groq'),
    (uuid_generate_v4(), 'groq', 'mixtral-8x7b-32768', 0.00000024, 0.00000024, FALSE, 'Mixtral 8x7B on Groq'),
    (uuid_generate_v4(), 'groq', 'gemma2-9b-it', 0.0000002, 0.0000002, FALSE, 'Gemma 2 9B on Groq')
ON CONFLICT (model_name) DO NOTHING;

INSERT INTO "openai_config" ("id", "provider", "model_name", "input_price_per_1m", "output_price_per_1m", "is_active", "is_default", "description", "api_key", "base_url", "created_at", "updated_at") 
VALUES ('528c7382-c5c3-4385-85f9-9038d95e9d32', 'free', 'free-ai', '0', '0', 't', 'f', NULL, NULL, NULL, '2026-01-19 01:37:16.809478+00', '2026-01-19 01:38:07.726689+00');
