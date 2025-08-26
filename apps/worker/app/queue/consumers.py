"""
RabbitMQ message consumers for processing jobs
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable

import aio_pika
from aio_pika import IncomingMessage
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..config import settings
from ..database import get_async_session
from ..models import Source, Block, Run
from ..scraper.savee import SaveeScraper
from ..scraper.core import SaveeSession
from ..storage.r2 import R2Storage
from ..logging_config import setup_logging
from sqlalchemy import select

logger = setup_logging(__name__)


class JobConsumer:
    """Base consumer for processing jobs"""
    
    def __init__(self, queue_name: str, routing_key: str, concurrency: int = 5):
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.concurrency = concurrency
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.running = False
        
    async def connect(self):
        """Connect to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(settings.amqp_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.concurrency)
            
            # Get queue
            self.queue = await self.channel.declare_queue(
                self.queue_name,
                durable=True
            )
            
            logger.info(f"Connected consumer for queue: {self.queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect consumer {self.queue_name}: {e}")
            raise
            
    async def start(self):
        """Start consuming messages"""
        if not self.connection:
            await self.connect()
            
        self.running = True
        
        # Start multiple consumers for concurrency
        tasks = []
        for i in range(self.concurrency):
            task = asyncio.create_task(self._consume_worker(f"worker-{i}"))
            tasks.append(task)
            
        logger.info(f"Started {self.concurrency} consumers for {self.queue_name}")
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in consumer {self.queue_name}: {e}")
        finally:
            self.running = False
            
    async def stop(self):
        """Stop consuming"""
        self.running = False
        if self.connection:
            await self.connection.close()
            
    async def _consume_worker(self, worker_id: str):
        """Worker that processes messages"""
        while self.running:
            try:
                async for message in self.queue:
                    if not self.running:
                        break
                        
                    try:
                        await self.process_message(message, worker_id)
                        await message.ack()
                        
                    except Exception as e:
                        logger.error(f"Error processing message in {worker_id}: {e}")
                        await self.handle_message_error(message, e)
                        
            except Exception as e:
                logger.error(f"Consumer worker {worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
                
    async def process_message(self, message: IncomingMessage, worker_id: str):
        """Override this method to process messages"""
        raise NotImplementedError
        
    async def handle_message_error(self, message: IncomingMessage, error: Exception):
        """Handle message processing errors"""
        try:
            job_data = json.loads(message.body.decode())
            retry_count = job_data.get('retry_count', 0)
            max_retries = job_data.get('max_retries', 3)
            
            if retry_count < max_retries:
                # Retry the job
                job_data['retry_count'] = retry_count + 1
                job_data['last_error'] = str(error)
                job_data['last_retry_at'] = datetime.utcnow().isoformat()
                
                # Republish with delay
                await asyncio.sleep(min(2 ** retry_count, 60))  # Exponential backoff
                await message.nack(requeue=True)
                
                logger.warning(f"Retrying job {job_data.get('job_id')} (attempt {retry_count + 1})")
                
            else:
                # Send to DLQ
                await message.nack(requeue=False)
                logger.error(f"Job {job_data.get('job_id')} failed after {max_retries} retries: {error}")
                
        except Exception as e:
            logger.error(f"Error handling message error: {e}")
            await message.nack(requeue=False)


class SweepConsumer(JobConsumer):
    """Consumer for sweep jobs (tail/backfill)"""
    
    def __init__(self, sweep_type: str):
        super().__init__(f'sweep.{sweep_type}', f'sweep.{sweep_type}', concurrency=2)
        self.sweep_type = sweep_type
        self.scraper = SaveeScraper()
        
    async def process_message(self, message: IncomingMessage, worker_id: str):
        """Process a sweep job"""
        job_data = json.loads(message.body.decode())
        job_id = job_data['job_id']
        source_id = job_data['source_id']
        
        logger.info(f"Processing sweep job {job_id} for source {source_id} ({self.sweep_type})")
        
        async with get_async_session() as session:
            # Get source
            source = await session.get(Source, source_id)
            if not source:
                raise ValueError(f"Source {source_id} not found")
                
            # Create run record
            run = Run(
                source_id=source_id,
                kind=self.sweep_type,
                status='running',
                started_at=datetime.utcnow(),
                counters={'items_discovered': 0, 'items_processed': 0}
            )
            session.add(run)
            await session.commit()
            
            try:
                # Determine max items based on sweep type
                max_items = 100 if self.sweep_type == 'backfill' else 50
                
                # Scrape the source
                items = await self.scraper.scrape_listing(source.url, max_items)
                
                run.counters['items_discovered'] = len(items)
                
                # Queue item processing jobs
                from .producer import get_producer
                producer = await get_producer()
                
                item_urls = [item.source_url for item in items]
                job_ids = await producer.queue_batch_items(item_urls, source_id)
                
                run.counters['items_queued'] = len(job_ids)
                run.status = 'completed'
                run.finished_at = datetime.utcnow()
                
                logger.info(f"Sweep job {job_id} completed: discovered {len(items)} items")
                
            except Exception as e:
                run.status = 'failed'
                run.error = str(e)
                run.finished_at = datetime.utcnow()
                raise
                
            finally:
                await session.commit()


class ItemConsumer(JobConsumer):
    """Consumer for item processing jobs"""
    
    def __init__(self):
        super().__init__('item.jobs', 'item.jobs', concurrency=10)
        self.scraper = SaveeScraper()
        self.storage = R2Storage()
        
    async def process_message(self, message: IncomingMessage, worker_id: str):
        """Process an item job"""
        job_data = json.loads(message.body.decode())
        job_id = job_data['job_id']
        item_url = job_data['item_url']
        source_id = job_data['source_id']
        
        logger.debug(f"Processing item job {job_id}: {item_url}")
        
        async with get_async_session() as session:
            # Scrape the item
            async with SaveeSession() as scrape_session:
                item = await self.scraper._scrape_item(scrape_session, item_url)
                
            if not item:
                raise ValueError(f"Failed to scrape item: {item_url}")
                
            # Check if item already exists
            existing = await session.execute(
                select(Block).where(
                    Block.source_id == source_id,
                    Block.external_id == item.external_id
                )
            )
            
            if existing.scalar_one_or_none():
                logger.debug(f"Item {item.external_id} already exists, skipping")
                return
                
            # Upload media to R2 and map to schema
            media_key = None
            video_poster_key = None

            if item.media_type == 'image':
                media_key = await self.storage.upload_image(
                    item.media_url,
                    f"blocks/{item.external_id}"
                )
            elif item.media_type == 'video':
                media_key = await self.storage.upload_video(
                    item.media_url,
                    f"blocks/{item.external_id}"
                )
                # Use thumbnail/poster if available
                if getattr(item, 'thumbnail_url', None):
                    try:
                        video_poster_key = await self.storage.upload_image(
                            item.thumbnail_url,
                            f"blocks/{item.external_id}"
                        )
                    except Exception:
                        video_poster_key = None

            # Create block record aligned with core schema
            block = Block(
                source_id=source_id,
                external_id=item.external_id,
                title_raw=item.title,
                description_raw=getattr(item, 'description', None),
                tags_raw=getattr(item, 'tags', []) or [],
                media_type=item.media_type,
                media_key=media_key or '',
                video_poster_key=video_poster_key,
                url=item.source_url,
                source_api_url=None,
                source_original_url=getattr(item, 'media_url', None),
                sidebar_info={},
                og_title=None,
                og_description=None,
                og_image_url=None,
                og_url=None,
            )
            
            session.add(block)
            await session.commit()
            
            logger.debug(f"Processed item {item.external_id}")


# Consumer manager
class ConsumerManager:
    """Manages all consumers"""
    
    def __init__(self):
        self.consumers = []
        self.running = False
        
    async def start_all(self):
        """Start all consumers"""
        # Create consumers
        self.consumers = [
            SweepConsumer('tail'),
            SweepConsumer('backfill'),
            ItemConsumer()
        ]
        
        # Start all consumers
        tasks = []
        for consumer in self.consumers:
            task = asyncio.create_task(consumer.start())
            tasks.append(task)
            
        self.running = True
        logger.info("Started all consumers")
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in consumer manager: {e}")
        finally:
            await self.stop_all()
            
    async def stop_all(self):
        """Stop all consumers"""
        self.running = False
        
        for consumer in self.consumers:
            await consumer.stop()
            
        logger.info("Stopped all consumers")


# Global manager instance
_manager: Optional[ConsumerManager] = None


async def get_consumer_manager() -> ConsumerManager:
    """Get or create the global consumer manager"""
    global _manager
    
    if _manager is None:
        _manager = ConsumerManager()
        
    return _manager
