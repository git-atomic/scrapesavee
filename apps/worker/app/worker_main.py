"""
Main worker application that starts both API and queue consumers
"""
import asyncio
import signal
import sys
from typing import List

import uvicorn
from fastapi import FastAPI

from .main import app
from .queue.consumers import get_consumer_manager
from .logging_config import setup_logging

logger = setup_logging(__name__)


class WorkerApplication:
    """Main worker application manager"""
    
    def __init__(self):
        self.tasks: List[asyncio.Task] = []
        self.shutdown_event = asyncio.Event()
        
    async def start_api_server(self):
        """Start the FastAPI server"""
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8001,
            log_level="info",
            access_log=False  # We handle logging in middleware
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    async def start_queue_consumers(self):
        """Start queue consumers"""
        try:
            manager = await get_consumer_manager()
            await manager.start_all()
        except Exception as e:
            logger.error(f"Failed to start queue consumers: {e}")
            raise
            
    async def start(self):
        """Start all services"""
        logger.info("🚀 Starting ScrapeSavee Worker Application")
        
        try:
            # Start API server and queue consumers concurrently
            api_task = asyncio.create_task(self.start_api_server(), name="api-server")
            consumer_task = asyncio.create_task(self.start_queue_consumers(), name="queue-consumers")
            
            self.tasks = [api_task, consumer_task]
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting worker application: {e}")
            raise
        finally:
            await self.stop()
            
    async def stop(self):
        """Stop all services"""
        logger.info("🛑 Stopping ScrapeSavee Worker Application")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        logger.info("✅ Worker application stopped")
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()


async def main():
    """Main entry point"""
    worker = WorkerApplication()
    
    # Setup signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, worker.signal_handler)
        
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        sys.exit(1)