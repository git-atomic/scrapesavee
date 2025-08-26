"""
RabbitMQ message producer for job queuing
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

import aio_pika
from aio_pika import ExchangeType, Message

from ..config import settings
from ..logging_config import setup_logging

logger = setup_logging(__name__)


class JobProducer:
    """Produces jobs to RabbitMQ queues"""
    
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.exchange: Optional[aio_pika.Exchange] = None
        
    async def connect(self):
        """Connect to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(settings.amqp_url)
            self.channel = await self.connection.channel()
            
            # Set QoS
            await self.channel.set_qos(prefetch_count=10)
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                'scrape.direct',
                ExchangeType.DIRECT,
                durable=True
            )
            
            # Declare queues
            await self._declare_queues()
            
            logger.info("Connected to RabbitMQ")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
            
    async def _declare_queues(self):
        """Declare all required queues"""
        queues = [
            ('sweep.tail', 'sweep.tail'),
            ('sweep.backfill', 'sweep.backfill'), 
            ('item.jobs', 'item.jobs'),
            ('item.dlq', 'item.dlq')
        ]
        
        for queue_name, routing_key in queues:
            # Declare DLQ first
            dlq_name = f"{queue_name}.dlq"
            dlq = await self.channel.declare_queue(
                dlq_name,
                durable=True,
                arguments={
                    'x-message-ttl': 86400000,  # 24 hours
                }
            )
            
            # Declare main queue with DLQ
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'scrape.direct',
                    'x-dead-letter-routing-key': f"{routing_key}.dlq",
                    'x-message-ttl': 3600000,  # 1 hour
                }
            )
            
            # Bind queues
            await queue.bind(self.exchange, routing_key)
            await dlq.bind(self.exchange, f"{routing_key}.dlq")
            
        logger.info("Declared all queues")
        
    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Closed RabbitMQ connection")
            
    async def queue_sweep_job(self, source_id: str, sweep_type: str = 'tail', priority: int = 0) -> str:
        """Queue a sweep job"""
        job_id = str(uuid4())
        
        job_data = {
            'job_id': job_id,
            'source_id': source_id,
            'sweep_type': sweep_type,
            'priority': priority,
            'created_at': datetime.utcnow().isoformat(),
            'retry_count': 0,
            'max_retries': 3
        }
        
        routing_key = f'sweep.{sweep_type}'
        
        message = Message(
            json.dumps(job_data).encode(),
            message_id=job_id,
            priority=priority,
            headers={
                'job_type': 'sweep',
                'source_id': source_id,
                'sweep_type': sweep_type
            }
        )
        
        await self.exchange.publish(message, routing_key=routing_key)
        
        logger.info(f"Queued sweep job {job_id} for source {source_id} ({sweep_type})")
        return job_id
        
    async def queue_item_job(self, item_url: str, source_id: str, priority: int = 0) -> str:
        """Queue an item processing job"""
        job_id = str(uuid4())
        
        job_data = {
            'job_id': job_id,
            'item_url': item_url,
            'source_id': source_id,
            'priority': priority,
            'created_at': datetime.utcnow().isoformat(),
            'retry_count': 0,
            'max_retries': 5
        }
        
        message = Message(
            json.dumps(job_data).encode(),
            message_id=job_id,
            priority=priority,
            headers={
                'job_type': 'item',
                'source_id': source_id,
                'item_url': item_url
            }
        )
        
        await self.exchange.publish(message, routing_key='item.jobs')
        
        logger.debug(f"Queued item job {job_id} for {item_url}")
        return job_id
        
    async def queue_batch_items(self, items: list, source_id: str) -> list:
        """Queue multiple item jobs efficiently"""
        job_ids = []
        
        for item_url in items:
            job_id = await self.queue_item_job(item_url, source_id)
            job_ids.append(job_id)
            
        logger.info(f"Queued {len(job_ids)} item jobs for source {source_id}")
        return job_ids


# Global producer instance
_producer: Optional[JobProducer] = None


async def get_producer() -> JobProducer:
    """Get or create the global producer instance"""
    global _producer
    
    if _producer is None:
        _producer = JobProducer()
        await _producer.connect()
        
    return _producer


async def close_producer():
    """Close the global producer"""
    global _producer
    
    if _producer:
        await _producer.close()
        _producer = None

