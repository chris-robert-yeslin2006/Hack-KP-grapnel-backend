import asyncio
import time
from datetime import datetime

from app.services.notification_service import notification_service
from app.core.config import settings

class NotificationWorker:
    def __init__(self):
        self.running = False
        
    async def start(self):
        """Start the notification worker"""
        self.running = True
        print("🚀 Notification worker started")
        
        while self.running:
            try:
                await notification_service._process_notification_queue()
                await asyncio.sleep(5)  # Process every 5 seconds
                
            except KeyboardInterrupt:
                print("⏹️  Shutting down notification worker...")
                self.running = False
                break
            except Exception as e:
                print(f"❌ Notification worker error: {e}")
                await asyncio.sleep(10)  # Wait longer if there's an error
    
    def stop(self):
        """Stop the notification worker"""
        self.running = False

async def main():
    """Main worker function"""
    worker = NotificationWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print("👋 Notification worker stopped")
    finally:
        worker.stop()

if __name__ == "__main__":
    asyncio.run(main())