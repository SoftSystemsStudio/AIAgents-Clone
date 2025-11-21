-- Multi-tenant schema migration
-- Adds customer tables and updates existing tables for multi-tenancy

-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, basic, pro, enterprise
    status VARCHAR(50) NOT NULL DEFAULT 'active',   -- active, suspended, cancelled
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    
    -- Billing
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_status VARCHAR(50),  -- active, past_due, cancelled, trialing
    trial_ends_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Indexes
    CONSTRAINT email_lowercase CHECK (email = LOWER(email))
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_stripe_id ON customers(stripe_customer_id);
CREATE INDEX idx_customers_status ON customers(status);

-- Create OAuth tokens table (encrypted per customer)
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL DEFAULT 'gmail',
    
    -- Encrypted token data (use encryption at rest)
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    token_expires_at TIMESTAMP,
    
    -- Gmail-specific
    gmail_email VARCHAR(255),
    scopes TEXT[],
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    
    UNIQUE(customer_id, provider)
);

CREATE INDEX idx_oauth_tokens_customer ON oauth_tokens(customer_id);

-- Create usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Usage period
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Metrics
    emails_processed INT DEFAULT 0,
    cleanups_executed INT DEFAULT 0,
    api_calls INT DEFAULT 0,
    storage_freed_mb NUMERIC DEFAULT 0,
    
    -- Quota enforcement
    quota_limit INT NOT NULL,
    quota_used INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(customer_id, period_start)
);

CREATE INDEX idx_usage_tracking_customer ON usage_tracking(customer_id);
CREATE INDEX idx_usage_tracking_period ON usage_tracking(period_start, period_end);

-- Update cleanup_runs table to add customer_id
ALTER TABLE cleanup_runs 
ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_cleanup_runs_customer ON cleanup_runs(customer_id);
CREATE INDEX IF NOT EXISTS idx_cleanup_runs_customer_date ON cleanup_runs(customer_id, started_at DESC);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Action details
    action VARCHAR(100) NOT NULL,  -- login, cleanup_execute, policy_create, etc.
    resource_type VARCHAR(50),     -- cleanup_run, policy, oauth_token
    resource_id VARCHAR(255),
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_customer ON audit_logs(customer_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- Create plan quotas reference table
CREATE TABLE IF NOT EXISTS plan_quotas (
    plan_tier VARCHAR(50) PRIMARY KEY,
    emails_per_month INT NOT NULL,
    cleanups_per_day INT NOT NULL,
    api_calls_per_hour INT NOT NULL,
    features JSONB DEFAULT '{}',
    price_monthly_cents INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default plans
INSERT INTO plan_quotas (plan_tier, emails_per_month, cleanups_per_day, api_calls_per_hour, price_monthly_cents, features) VALUES
    ('free', 500, 1, 10, 0, '{"scheduled_cleanups": false, "api_access": false, "priority_support": false}'),
    ('basic', 5000, 10, 100, 900, '{"scheduled_cleanups": true, "api_access": false, "priority_support": false}'),
    ('pro', 50000, 100, 1000, 2900, '{"scheduled_cleanups": true, "api_access": true, "priority_support": false}'),
    ('enterprise', 500000, 1000, 10000, 9900, '{"scheduled_cleanups": true, "api_access": true, "priority_support": true, "custom_policies": true}')
ON CONFLICT (plan_tier) DO NOTHING;

-- Enable row-level security on sensitive tables
ALTER TABLE oauth_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE cleanup_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;

-- Create policies for row-level security (customers can only see their own data)
CREATE POLICY customer_oauth_isolation ON oauth_tokens
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id')::UUID);

CREATE POLICY customer_cleanup_runs_isolation ON cleanup_runs
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id')::UUID);

CREATE POLICY customer_usage_isolation ON usage_tracking
    FOR ALL
    USING (customer_id = current_setting('app.current_customer_id')::UUID);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_tokens_updated_at BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_usage_tracking_updated_at BEFORE UPDATE ON usage_tracking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE customers IS 'Customer accounts with plan tiers and billing info';
COMMENT ON TABLE oauth_tokens IS 'Encrypted OAuth tokens per customer (Gmail, etc.)';
COMMENT ON TABLE usage_tracking IS 'Usage metrics and quota tracking per customer per month';
COMMENT ON TABLE audit_logs IS 'Audit trail of all customer actions for security and debugging';
COMMENT ON TABLE plan_quotas IS 'Plan tier definitions with quotas and pricing';
