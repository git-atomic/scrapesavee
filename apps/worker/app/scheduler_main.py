"""
Main entry point for ScrapeSavee Scheduler
Runs the scheduler service that manages periodic scraping operations
"""
import asyncio
import signal
import sys
from typing import Optional

from .scheduler import SchedulerService
from .config import settings
from .logging_config import get_logger
from .database import create_tables

logger = get_logger(__name__)


class SchedulerMain:
    """Main scheduler application"""
    
    def __init__(self):
        self.scheduler_service: Optional[SchedulerService] = None
        self.shutdown_event = asyncio.Event()
    
    async def startup(self):
        """Initialize the scheduler application"""
        logger.info("🚀 Starting ScrapeSavee Scheduler")
        
        # Initialize database
        await create_tables()
        logger.info("✅ Database initialized")
        
        # Start scheduler service
        self.scheduler_service = SchedulerService()
        await self.scheduler_service.start()
        logger.info("✅ Scheduler service started")
    
    async def shutdown(self):
        """Shutdown the scheduler application"""
        logger.info("🛑 Shutting down ScrapeSavee Scheduler")
        
        if self.scheduler_service:
            await self.scheduler_service.stop()
            logger.info("✅ Scheduler service stopped")
        
        logger.info("✅ Scheduler shutdown complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run(self):
        """Run the scheduler application"""
        try:
            await self.startup()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Scheduler application error: {e}", exc_info=True)
            sys.exit(1)
        finally:
            await self.shutdown()


async def main():
    """Main entry point"""
    scheduler = SchedulerMain()
    scheduler.setup_signal_handlers()
    await scheduler.run()


if __name__ == "__main__":
    asyncio.run(main())
