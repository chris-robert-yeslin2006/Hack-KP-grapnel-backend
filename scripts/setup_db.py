#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def setup_database():
    """Setup database tables and initial data"""
    print("Setting up database...")
    
    try:
        # Import after adding to path
        from app.core.database import supabase
        
        # Read and execute the SQL migration file
        sql_file = project_root / "migrations" / "init.sql"
        
        if not sql_file.exists():
            print(f"SQL file not found: {sql_file}")
            print("Creating migrations directory and init.sql file...")
            
            # Create migrations directory if it doesn't exist
            migrations_dir = project_root / "migrations"
            migrations_dir.mkdir(exist_ok=True)
            
            # Create the SQL file with our schema
            create_init_sql(sql_file)
            
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        print("\n" + "="*60)
        print("📋 MANUAL SETUP REQUIRED")
        print("="*60)
        print("Please follow these steps:")
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to the SQL Editor")
        print("3. Copy and paste the following SQL commands:")
        print("="*60)
        print(sql_content)
        print("="*60)
        print("4. Click 'Run' to execute the SQL")
        print("5. Come back here and press Enter to test the connection")
        input("\nPress Enter after you've run the SQL in Supabase...")
        
        # Test connection
        print("Testing database connection...")
        result = supabase.table('hash_registry').select("count", count='exact').execute()
        print(f"✅ Database connection successful!")
        print(f"Current hash_registry count: {result.count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure your .env file has correct Supabase credentials")
        print("2. Verify your Supabase project is active")
        print("3. Check that you've run the SQL commands in Supabase SQL Editor")
        return False

def create_init_sql(sql_file):
    """Create the init.sql file with our database schema"""
    sql_content = """-- Enable UUID extension
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
    systems_notified JSONB DEFAULT '[]'
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
CREATE INDEX IF NOT EXISTS idx_notification_queue_composite ON notification_queue(status, target_system);"""
    
    with open(sql_file, 'w') as f:
        f.write(sql_content)
    
    print(f"✅ Created SQL migration file: {sql_file}")

if __name__ == "__main__":
    success = setup_database()
    if success:
        print("🎉 Database setup completed!")
    else:
        print("💥 Database setup failed!")
        sys.exit(1)