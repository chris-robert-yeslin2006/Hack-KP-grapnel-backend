#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    
    try:
        print("✓ Testing config...")
        from app.core.config import settings
        print(f"  Environment: {settings.environment}")
        
        print("✓ Testing database...")
        from app.core.database import db_manager, supabase
        print("  Database manager created")
        
        print("✓ Testing redis...")
        from app.core.redis import redis_manager
        print("  Redis manager created")
        
        print("✓ Testing schemas...")
        from app.schemas.hash_schemas import HashLookupRequest
        print("  Schemas imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Other error: {e}")
        return False

def test_config():
    """Test configuration"""
    print("\nTesting configuration...")
    
    try:
        from app.core.config import settings
        
        required_settings = [
            'supabase_url', 'supabase_key', 'redis_url', 'secret_key'
        ]
        
        for setting in required_settings:
            value = getattr(settings, setting, None)
            if not value or "your-" in str(value).lower():
                print(f"⚠️  {setting} needs to be configured in .env")
            else:
                print(f"✓ {setting} is configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

async def test_connections():
    """Test database and Redis connections"""
    print("\nTesting connections...")
    
    try:
        from app.core.database import db_manager
        
        # Test database (Supabase only)
        print("Testing Supabase connection...")
        db_healthy = await db_manager.health_check()
        if db_healthy:
            print("✅ Supabase connection successful")
        else:
            print("❌ Supabase connection failed - check your credentials")
        
        # Test Redis (basic test)
        print("Testing Redis connection...")
        from app.core.redis import redis_manager
        
        await redis_manager.connect()
        await redis_manager.set("test_key", "test_value", expire=10)
        test_value = await redis_manager.get("test_key")
        await redis_manager.delete("test_key")
        
        if test_value == "test_value":
            print("✅ Redis connection successful")
        else:
            print("❌ Redis connection failed")
        
        await redis_manager.disconnect()
        
    except Exception as e:
        print(f"⚠️  Connection test failed: {e}")
        print("Make sure Redis is running: brew services start redis")

if __name__ == "__main__":
    print("🧪 Running setup tests...\n")
    
    # Test imports
    imports_ok = test_imports()
    
    # Test config
    config_ok = test_config()
    
    # Test connections (async)
    import asyncio
    try:
        asyncio.run(test_connections())
    except Exception as e:
        print(f"Connection tests failed: {e}")
    
    print("\n" + "="*50)
    if imports_ok and config_ok:
        print("✅ Basic setup looks good!")
        print("\nNext steps:")
        print("1. Ensure Redis is running: brew services start redis")
        print("2. Run database setup: python scripts/setup_db.py")
        print("3. Start the application: python run.py")
        print("4. Test the API: curl http://localhost:8000/api/v1/health")
    else:
        print("❌ Setup has issues that need to be fixed")
        sys.exit(1)