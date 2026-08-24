-- PostgreSQL initialization script for Code Alpha
-- Creates required schemas, tables, and extensions

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS uuid-ossp;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS code_alpha;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS metrics;

-- Audit schema tables
CREATE TABLE IF NOT EXISTS audit.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    target VARCHAR(500),
    status VARCHAR(20) NOT NULL,
    reason TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255),
    previous_hash VARCHAR(64),
    entry_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT audit_log_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_audit_task_id ON audit.audit_log(task_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit.audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action_type ON audit.audit_log(action_type);

-- Metrics schema tables
CREATE TABLE IF NOT EXISTS metrics.task_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL UNIQUE,
    files_touched INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    shell_commands INTEGER DEFAULT 0,
    blocked_actions INTEGER DEFAULT 0,
    total_actions INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'ok',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT task_metrics_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_metrics_task_id ON metrics.task_metrics(task_id);
CREATE INDEX IF NOT EXISTS idx_metrics_status ON metrics.task_metrics(status);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics.task_metrics(created_at);

-- Core schema tables
CREATE TABLE IF NOT EXISTS code_alpha.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL UNIQUE,
    name TEXT,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    prompt TEXT,
    result TEXT,
    error_message TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tasks_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON code_alpha.tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON code_alpha.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON code_alpha.tasks(created_at);

-- Approval requests table
CREATE TABLE IF NOT EXISTS code_alpha.approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id UUID NOT NULL UNIQUE,
    task_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(100),
    target VARCHAR(500),
    risk_level VARCHAR(20),
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT approval_requests_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_approval_request_id ON code_alpha.approval_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_approval_task_id ON code_alpha.approval_requests(task_id);
CREATE INDEX IF NOT EXISTS idx_approval_status ON code_alpha.approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_expires_at ON code_alpha.approval_requests(expires_at);

-- Safety events table
CREATE TABLE IF NOT EXISTS code_alpha.safety_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20),
    message TEXT,
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT safety_events_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_safety_events_task_id ON code_alpha.safety_events(task_id);
CREATE INDEX IF NOT EXISTS idx_safety_events_severity ON code_alpha.safety_events(severity);
CREATE INDEX IF NOT EXISTS idx_safety_events_timestamp ON code_alpha.safety_events(timestamp);

-- Policy violations table
CREATE TABLE IF NOT EXISTS code_alpha.policy_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL,
    policy_name VARCHAR(100),
    violation_type VARCHAR(50),
    target VARCHAR(500),
    reason TEXT,
    action_taken VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT policy_violations_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_violations_task_id ON code_alpha.policy_violations(task_id);
CREATE INDEX IF NOT EXISTS idx_violations_action_taken ON code_alpha.policy_violations(action_taken);
CREATE INDEX IF NOT EXISTS idx_violations_timestamp ON code_alpha.policy_violations(timestamp);

-- Permissions for application user
GRANT CONNECT ON DATABASE codealpha_dev TO codealpha;
GRANT USAGE ON SCHEMA code_alpha, audit, metrics TO codealpha;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA code_alpha TO codealpha;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit TO codealpha;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA metrics TO codealpha;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA code_alpha TO codealpha;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO codealpha;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA metrics TO codealpha;

-- Create views for common queries
CREATE OR REPLACE VIEW code_alpha.recent_tasks AS
SELECT id, task_id, name, status, created_at, completed_at
FROM code_alpha.tasks
ORDER BY created_at DESC
LIMIT 100;

CREATE OR REPLACE VIEW code_alpha.pending_approvals AS
SELECT id, request_id, task_id, action_type, risk_level, status, expires_at
FROM code_alpha.approval_requests
WHERE status = 'pending'
ORDER BY requested_at ASC;

CREATE OR REPLACE VIEW metrics.task_summary AS
SELECT 
    tm.task_id,
    tm.files_touched,
    tm.lines_added,
    tm.lines_removed,
    tm.api_calls,
    tm.shell_commands,
    tm.blocked_actions,
    tm.total_actions,
    tm.status,
    (SELECT COUNT(*) FROM audit.audit_log WHERE task_id = tm.task_id) as audit_entries,
    (SELECT COUNT(*) FROM code_alpha.safety_events WHERE task_id = tm.task_id) as safety_events
FROM metrics.task_metrics tm;

-- Vacuum and analyze
ANALYZE;

-- Done
\echo 'Code Alpha database schema initialized successfully!'
