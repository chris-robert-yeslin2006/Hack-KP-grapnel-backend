-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Hash Registry Table
CREATE TABLE IF NOT EXISTS hash_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hash_value VARCHAR(64) NOT NULL,
    hash_type VARCHAR(20) NOT NULL CHECK (hash_type IN ('SHA256', 'MD5', 'PHASH')),
    source_system VARCHAR(20) NOT NULL CHECK (source_system IN ('trace', 'grapnel', 'takedown')),
    source_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    severity_level VARCHAR(20) DEFAULT 'medium' CHECK (severity_level IN ('low', 'medium', 'high', 'critical')),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Notification Queue Table
CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    match_id UUID NOT NULL,
    target_system VARCHAR(20) NOT NULL CHECK (target_system IN ('trace', 'grapnel', 'takedown')),
    notification_type VARCHAR(50) NOT NULL CHECK (notification_type IN ('hash_match', 'alert', 'update')),
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'acknowledged')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE NULL,
    retry_count INTEGER DEFAULT 0
);

-- Hash Matches Table
CREATE TABLE IF NOT EXISTS hash_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    primary_hash_id UUID NOT NULL,
    matched_hash_id UUID NOT NULL,
    match_type VARCHAR(20) NOT NULL CHECK (match_type IN ('exact', 'similar', 'variant')),
    confidence_score DECIMAL(3,2) DEFAULT 1.00,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    systems_notified JSONB DEFAULT '[]',
    FOREIGN KEY (primary_hash_id) REFERENCES hash_registry(id),
    FOREIGN KEY (matched_hash_id) REFERENCES hash_registry(id)
);

-- Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(50) NOT NULL,
    system_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Webhook Subscriptions Table
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    system_id VARCHAR(20) UNIQUE NOT NULL,
    webhook_url VARCHAR(500) NOT NULL,
    notification_types JSONB DEFAULT '["hash_match"]',
    filters JSONB DEFAULT '{}',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_hash_registry_hash_value ON hash_registry(hash_value);
CREATE INDEX IF NOT EXISTS idx_hash_registry_source_system ON hash_registry(source_system);
CREATE INDEX IF NOT EXISTS idx_hash_registry_created_at ON hash_registry(created_at);
CREATE INDEX IF NOT EXISTS idx_hash_registry_severity ON hash_registry(severity_level);

CREATE INDEX IF NOT EXISTS idx_notification_queue_status ON notification_queue(status);
CREATE INDEX IF NOT EXISTS idx_notification_queue_target_system ON notification_queue(target_system);
CREATE INDEX IF NOT EXISTS idx_notification_queue_created_at ON notification_queue(created_at);

CREATE INDEX IF NOT EXISTS idx_hash_matches_detected_at ON hash_matches(detected_at);
CREATE INDEX IF NOT EXISTS idx_hash_matches_primary_hash ON hash_matches(primary_hash_id);

CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_system_id ON audit_log(system_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);

-- Create composite indexes
CREATE INDEX IF NOT EXISTS idx_hash_registry_composite ON hash_registry(hash_value, source_system);
CREATE INDEX IF NOT EXISTS idx_notification_queue_composite ON notification_queue(status, target_system);