import uuid
import json
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.database import db_manager
from app.core.redis import redis_manager
from app.core.config import settings

class NotificationService:
    def __init__(self):
        self.db = db_manager
        self.redis = redis_manager
        self.webhook_endpoints = {
            "trace": None,  # Will be set via subscription
            "grapnel": None,
            "takedown": None
        }
    
    async def subscribe_webhook(self, system_id: str, webhook_url: str, notification_types: List[str], filters: Dict[str, Any] = None) -> bool:
        """Subscribe a system to webhook notifications"""
        try:
            subscription_data = {
                "id": str(uuid.uuid4()),
                "system_id": system_id,
                "webhook_url": webhook_url,
                "notification_types": notification_types,
                "filters": filters or {},
                "active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store in database
            result = self.db.supabase.table('webhook_subscriptions').upsert(subscription_data, on_conflict="system_id").execute()
            
            if result.data:
                # Cache the webhook URL for quick access
                await self.redis.set(f"webhook:{system_id}", webhook_url, expire=3600)  # Cache for 1 hour
                return True
            
            return False
            
        except Exception as e:
            print(f"Error subscribing webhook: {e}")
            return False
    
    async def send_hash_match_notification(self, match_data: Dict[str, Any]):
        """Send hash match notification to relevant systems"""
        try:
            # Create notification record
            notification_id = str(uuid.uuid4())
            
            # Determine which systems to notify
            systems_to_notify = await self._determine_notification_targets(match_data)
            
            for system_id in systems_to_notify:
                await self._queue_notification(notification_id, system_id, "hash_match", match_data)
            
            # Process notifications asynchronously
            await self._process_notification_queue()
            
        except Exception as e:
            print(f"Error sending hash match notification: {e}")
    
    async def _determine_notification_targets(self, match_data: Dict[str, Any]) -> List[str]:
        """Determine which systems should receive the notification"""
        targets = []
        
        new_source = match_data.get("new_source_system")
        existing_source = match_data.get("existing_source_system")
        
        # Notify the system that originally reported the hash
        if existing_source and existing_source not in targets:
            targets.append(existing_source)
        
        # Notify other relevant systems based on business rules
        severity = match_data.get("severity", "medium")
        if severity in ["high", "critical"]:
            # High severity matches notify all systems
            all_systems = ["trace", "grapnel", "takedown"]
            for system in all_systems:
                if system != new_source and system not in targets:
                    targets.append(system)
        
        return targets
    
    async def _queue_notification(self, notification_id: str, target_system: str, notification_type: str, payload: Dict[str, Any]):
        """Queue a notification for delivery"""
        notification_data = {
            "id": str(uuid.uuid4()),
            "match_id": notification_id,
            "target_system": target_system,
            "notification_type": notification_type,
            "payload": payload,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        # Store in database
        self.db.supabase.table('notification_queue').insert(notification_data).execute()
        
        # Also add to Redis queue for immediate processing
        await self.redis.set(
            f"notification_queue:{notification_data['id']}", 
            notification_data, 
            expire=3600  # Expire after 1 hour
        )
    
    async def _process_notification_queue(self):
        """Process pending notifications"""
        try:
            # Get pending notifications
            result = self.db.supabase.table('notification_queue').select('*').eq('status', 'pending').limit(10).execute()
            
            for notification in result.data:
                success = await self._send_webhook_notification(notification)
                
                # Update notification status
                new_status = "sent" if success else "failed"
                retry_count = notification.get("retry_count", 0)
                
                if not success and retry_count < settings.max_retry_attempts:
                    new_status = "pending"
                    retry_count += 1
                
                update_data = {
                    "status": new_status,
                    "retry_count": retry_count,
                    "sent_at": datetime.utcnow().isoformat() if success else None
                }
                
                self.db.supabase.table('notification_queue').update(update_data).eq('id', notification['id']).execute()
                
        except Exception as e:
            print(f"Error processing notification queue: {e}")
    
    async def _send_webhook_notification(self, notification: Dict[str, Any]) -> bool:
        """Send individual webhook notification"""
        try:
            target_system = notification["target_system"]
            
            # Get webhook URL from cache or database
            webhook_url = await self.redis.get(f"webhook:{target_system}")
            
            if not webhook_url:
                # Fetch from database
                result = self.db.supabase.table('webhook_subscriptions').select('webhook_url').eq('system_id', target_system).eq('active', True).single().execute()
                
                if not result.data:
                    return False
                
                webhook_url = result.data['webhook_url']
                # Cache it
                await self.redis.set(f"webhook:{target_system}", webhook_url, expire=3600)
            
            # Prepare webhook payload
            webhook_payload = {
                "event": notification["notification_type"],
                "timestamp": datetime.utcnow().isoformat(),
                "data": notification["payload"],
                "notification_id": notification["id"]
            }
            
            # Send HTTP request
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook_url,
                    json=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Grapnel-Signature": self._generate_signature(webhook_payload)
                    }
                )
                
                return response.status_code == 200
                
        except Exception as e:
            print(f"Error sending webhook notification: {e}")
            return False
    
    def _generate_signature(self, payload: Dict[str, Any]) -> str:
        """Generate HMAC signature for webhook security"""
        import hmac
        import hashlib
        
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            settings.webhook_secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"

notification_service = NotificationService()