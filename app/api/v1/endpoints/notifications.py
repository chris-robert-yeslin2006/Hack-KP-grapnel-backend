from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
from pydantic import BaseModel

from app.services.notification_service import notification_service

router = APIRouter()

class WebhookSubscriptionRequest(BaseModel):
    system_id: str
    webhook_url: str
    notification_types: List[str] = ["hash_match", "alert", "update"]
    filters: Dict[str, Any] = {}

class WebhookSubscriptionResponse(BaseModel):
    success: bool
    message: str
    subscription_id: str = ""

@router.post("/subscribe", response_model=WebhookSubscriptionResponse)
async def subscribe_webhook(request: WebhookSubscriptionRequest):
    """
    Subscribe to hash match notifications
    
    Register a webhook URL to receive notifications when hash matches are found.
    """
    
    # Validate webhook URL format
    if not request.webhook_url.startswith(('http://', 'https://')):
        raise HTTPException(
            status_code=400,
            detail="Webhook URL must start with http:// or https://"
        )
    
    # Validate system ID
    valid_systems = ["trace", "grapnel", "takedown"]
    if request.system_id not in valid_systems:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid system_id. Must be one of: {', '.join(valid_systems)}"
        )
    
    try:
        success = await notification_service.subscribe_webhook(
            request.system_id,
            request.webhook_url,
            request.notification_types,
            request.filters
        )
        
        if success:
            return WebhookSubscriptionResponse(
                success=True,
                message="Webhook subscription created successfully",
                subscription_id=request.system_id
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create webhook subscription"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating webhook subscription: {str(e)}"
        )

@router.get("/subscriptions/{system_id}")
async def get_subscription(system_id: str):
    """Get current webhook subscription for a system"""
    
    try:
        from app.core.database import db_manager
        
        result = db_manager.supabase.table('webhook_subscriptions').select('*').eq('system_id', system_id).eq('active', True).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="No active subscription found for this system"
            )
        
        subscription = result.data[0]
        return {
            "system_id": subscription["system_id"],
            "webhook_url": subscription["webhook_url"],
            "notification_types": subscription["notification_types"],
            "filters": subscription["filters"],
            "created_at": subscription["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving subscription: {str(e)}"
        )

@router.delete("/subscriptions/{system_id}")
async def unsubscribe_webhook(system_id: str):
    """Unsubscribe from webhook notifications"""
    
    try:
        from app.core.database import db_manager
        from app.core.redis import redis_manager
        
        # Deactivate subscription
        result = db_manager.supabase.table('webhook_subscriptions').update({"active": False}).eq('system_id', system_id).execute()
        
        # Remove from cache
        await redis_manager.delete(f"webhook:{system_id}")
        
        return {"success": True, "message": "Webhook subscription removed successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error removing webhook subscription: {str(e)}"
        )

@router.get("/queue/status")
async def get_notification_queue_status():
    """Get status of the notification queue"""
    
    try:
        from app.core.database import db_manager
        
        # Get queue statistics
        pending = db_manager.supabase.table('notification_queue').select('id', count="exact").eq('status', 'pending').execute()
        failed = db_manager.supabase.table('notification_queue').select('id', count="exact").eq('status', 'failed').execute()
        sent = db_manager.supabase.table('notification_queue').select('id', count="exact").eq('status', 'sent').execute()
        
        return {
            "pending": pending.count,
            "failed": failed.count,
            "sent": sent.count,
            "total": pending.count + failed.count + sent.count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving queue status: {str(e)}"
        )