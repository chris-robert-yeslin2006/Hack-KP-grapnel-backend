#!/usr/bin/env python3

import uvicorn
import asyncio
from app.main import app
from app.core.config import settings

async def main():
    """Main function to run the application"""
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=settings.debug,
        workers=1 if settings.debug else 4
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())