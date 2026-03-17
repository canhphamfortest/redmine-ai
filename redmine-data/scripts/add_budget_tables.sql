-- Budget tables migration
-- This script adds budget_config and budget_alert tables for budget alert system

-- Budget Config table
CREATE TABLE IF NOT EXISTS budget_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider TEXT NOT NULL,  -- openai, google, anthropic, groq
    budget_amount_usd FLOAT NOT NULL,
    invoice_day INTEGER NOT NULL CHECK (invoice_day >= 1 AND invoice_day <= 31),
    alert_thresholds JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [50, 80, 100]
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(provider)  -- One budget config per provider
);

-- Budget Alert table
CREATE TABLE IF NOT EXISTS budget_alert (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    budget_config_id UUID NOT NULL REFERENCES budget_config(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,  -- openai, google, anthropic, groq
    billing_cycle_start TIMESTAMPTZ NOT NULL,
    billing_cycle_end TIMESTAMPTZ NOT NULL,
    threshold_percentage INTEGER NOT NULL,
    current_spending_usd FLOAT NOT NULL,
    budget_amount_usd FLOAT NOT NULL,
    alert_type TEXT NOT NULL,  -- threshold_reached, budget_exceeded
    alert_channels JSONB NOT NULL DEFAULT '[]'::jsonb,  -- ["in_app", "email"]
    sent_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_budget_config_provider ON budget_config(provider);
CREATE INDEX IF NOT EXISTS idx_budget_config_active ON budget_config(is_active);
CREATE INDEX IF NOT EXISTS idx_budget_alert_provider ON budget_alert(provider);
CREATE INDEX IF NOT EXISTS idx_budget_alert_config_id ON budget_alert(budget_config_id);
CREATE INDEX IF NOT EXISTS idx_budget_alert_cycle ON budget_alert(billing_cycle_start, billing_cycle_end);
CREATE INDEX IF NOT EXISTS idx_budget_alert_acknowledged ON budget_alert(acknowledged_at) WHERE acknowledged_at IS NULL;

-- Add comments for documentation
COMMENT ON TABLE budget_config IS 'Cấu hình budget cho từng provider (OpenAI, Google, Anthropic, Groq)';
COMMENT ON TABLE budget_alert IS 'Lịch sử cảnh báo budget khi vượt quá ngưỡng đã thiết lập';
COMMENT ON COLUMN budget_config.alert_thresholds IS 'Mảng các ngưỡng cảnh báo theo phần trăm (ví dụ: [50, 80, 100])';
COMMENT ON COLUMN budget_alert.alert_channels IS 'Mảng các kênh đã gửi alert (ví dụ: ["in_app", "email"])';
