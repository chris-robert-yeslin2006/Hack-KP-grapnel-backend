from supabase import create_client, Client
from typing import Optional
import asyncio

from app.core.config import settings

# Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_key)

class DatabaseManager:
    def __init__(self):
        self.supabase = supabase
    
    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            result = self.supabase.table('hash_registry').select("count", count='exact').limit(1).execute()
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False
    
    def get_client(self) -> Client:
        """Get Supabase client"""
        return self.supabase

# Create the database manager instance
db_manager = DatabaseManager()