import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.database import db_manager

class AuditService:
    def __init__(self):
        self.db = db_manager
    
    async def log_action(
        self,
        action: str,
        system_id: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log an action for audit purposes"""
        
        try:
            audit_record = {
                "id": str(uuid.uuid4()),
                "action": action,
                "system_id": system_id,
                "user_id": user_id,
                "resource_id": resource_id,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Insert into audit log table
            self.db.supabase.table('audit_log').insert(audit_record).execute()
            
        except Exception as e:
            # Don't fail the main operation if audit logging fails
            print(f"Audit logging failed: {e}")
    
    async def get_audit_logs(
        self,
        system_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Retrieve audit logs with optional filters"""
        
        try:
            query = self.db.supabase.table('audit_log').select('*')
            
            if system_id:
                query = query.eq('system_id', system_id)
            
            if action:
                query = query.eq('action', action)
            
            result = query.order('timestamp', desc=True).limit(limit).execute()
            
            return result.data
            
        except Exception as e:
            print(f"Error retrieving audit logs: {e}")
            return []

audit_service = AuditService()