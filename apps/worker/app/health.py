"""
Comprehensive health check system for ScrapeSavee Worker
Monitors database, queue, storage, and service health
"""
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Import directly from database.py to avoid circular imports
import sys
import os
sys.path.append(os.path.dirname(__file__))
from .config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

health_router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model"""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    checks: Dict[str, Any]
    version: str
    uptime_seconds: float


class ComponentHealth(BaseModel):
    """Individual component health"""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: float
    message: str
    details: Dict[str, Any] = {}


# Track service start time for uptime calculation
SERVICE_START_TIME = time.time()


async def check_database_health() -> ComponentHealth:
    """Check database connectivity and performance"""
    start_time = time.perf_counter()
    
    try:
        async with get_async_session() as session:
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            
            # Test table existence
            result = await session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            )
            table_count = result.scalar()
            
            # Test recent activity
            result = await session.execute(
                text("SELECT COUNT(*) FROM items WHERE created_at > NOW() - INTERVAL '1 hour'")
            )
            recent_items = result.scalar()
            
            response_time = (time.perf_counter() - start_time) * 1000
            
            return ComponentHealth(
                name="database",
                status="healthy",
                response_time_ms=round(response_time, 2),
                message="Database is healthy",
                details={
                    "tables_count": table_count,
                    "recent_items_1h": recent_items,
                    "pool_type": engine.pool.__class__.__name__,
                    "pool_size": getattr(engine.pool, '_pool_size', 'N/A'),
                    "checked_out_connections": getattr(engine.pool, 'checkedout', lambda: 'N/A')(),
                }
            )
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"Database health check failed: {e}")
        
        return ComponentHealth(
            name="database",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            message=f"Database connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def check_queue_health() -> ComponentHealth:
    """Check RabbitMQ queue connectivity and status"""
    start_time = time.perf_counter()
    
    try:
        from aio_pika import connect_robust
        
        # Test connection
        connection = await connect_robust(settings.AMQP_URL)
        channel = await connection.channel()
        
        # Check queue status
        queue_names = ["item.jobs", "sweep.tail", "sweep.backfill", "item.dlq"]
        queue_info = {}
        
        for queue_name in queue_names:
            try:
                queue = await channel.get_queue(queue_name, ensure=False)
                # Use channel.queue_declare to get queue info
                declare_result = await channel.queue_declare(queue_name, passive=True)
                queue_info[queue_name] = {
                    "message_count": declare_result.method.message_count,
                    "consumer_count": declare_result.method.consumer_count,
                }
            except Exception as e:
                logger.debug(f"Could not get info for queue {queue_name}: {e}")
                queue_info[queue_name] = {
                    "message_count": 0,
                    "consumer_count": 0,
                    "status": "unknown"
                }
        
        await connection.close()
        response_time = (time.perf_counter() - start_time) * 1000
        
        # Determine status based on queue health
        total_messages = sum(
            info.get("message_count", 0) 
            for info in queue_info.values() 
            if isinstance(info, dict) and "message_count" in info
        )
        
        status = "healthy"
        if total_messages > 1000:
            status = "degraded"
        
        return ComponentHealth(
            name="queue",
            status=status,
            response_time_ms=round(response_time, 2),
            message="Queue is healthy",
            details={
                "queues": queue_info,
                "total_pending_messages": total_messages,
            }
        )
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"Queue health check failed: {e}")
        
        return ComponentHealth(
            name="queue",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            message=f"Queue connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def check_storage_health() -> ComponentHealth:
    """Check R2 storage connectivity and status"""
    start_time = time.perf_counter()
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Create S3 client for R2
        s3_client = boto3.client(
            's3',
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION,
        )
        
        # Test bucket access
        response = s3_client.head_bucket(Bucket=settings.R2_BUCKET_NAME)
        
        # Get bucket info
        objects = s3_client.list_objects_v2(
            Bucket=settings.R2_BUCKET_NAME,
            MaxKeys=1
        )
        
        response_time = (time.perf_counter() - start_time) * 1000
        
        return ComponentHealth(
            name="storage",
            status="healthy",
            response_time_ms=round(response_time, 2),
            message="Storage is healthy",
            details={
                "bucket": settings.R2_BUCKET_NAME,
                "accessible": True,
                "object_count_sample": objects.get("KeyCount", 0),
            }
        )
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"Storage health check failed: {e}")
        
        return ComponentHealth(
            name="storage",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            message=f"Storage connection failed: {str(e)}",
            details={"error": str(e)}
        )


async def check_worker_health() -> ComponentHealth:
    """Check worker service health and performance"""
    start_time = time.perf_counter()
    
    try:
        import psutil
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check if any critical thresholds are exceeded
        status = "healthy"
        issues = []
        
        if cpu_percent > 80:
            status = "degraded"
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        if memory.percent > 85:
            status = "degraded"
            issues.append(f"High memory usage: {memory.percent}%")
        
        if disk.percent > 90:
            status = "degraded"
            issues.append(f"High disk usage: {disk.percent}%")
        
        response_time = (time.perf_counter() - start_time) * 1000
        
        return ComponentHealth(
            name="worker",
            status=status,
            response_time_ms=round(response_time, 2),
            message="Worker is healthy" if not issues else f"Worker issues: {'; '.join(issues)}",
            details={
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory.percent, 2),
                "memory_available_gb": round(memory.available / 1024**3, 2),
                "disk_percent": round(disk.percent, 2),
                "disk_free_gb": round(disk.free / 1024**3, 2),
                "uptime_seconds": round(time.time() - SERVICE_START_TIME, 2),
            }
        )
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        logger.error(f"Worker health check failed: {e}")
        
        return ComponentHealth(
            name="worker",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            message=f"Worker health check failed: {str(e)}",
            details={"error": str(e)}
        )


@health_router.get("/", response_model=HealthStatus)
async def get_health_status():
    """Get comprehensive health status of all components"""
    start_time = time.perf_counter()
    
    try:
        # Run all health checks concurrently
        checks = await asyncio.gather(
            check_database_health(),
            check_queue_health(),
            check_storage_health(),
            check_worker_health(),
            return_exceptions=True
        )
        
        # Process results
        health_checks = {}
        overall_status = "healthy"
        
        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check failed: {check}")
                health_checks["unknown"] = {
                    "status": "unhealthy",
                    "message": str(check)
                }
                overall_status = "unhealthy"
            else:
                health_checks[check.name] = {
                    "status": check.status,
                    "response_time_ms": check.response_time_ms,
                    "message": check.message,
                    "details": check.details
                }
                
                # Update overall status
                if check.status == "unhealthy":
                    overall_status = "unhealthy"
                elif check.status == "degraded" and overall_status == "healthy":
                    overall_status = "degraded"
        
        response_time = (time.perf_counter() - start_time) * 1000
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            checks=health_checks,
            version=settings.VERSION,
            uptime_seconds=round(time.time() - SERVICE_START_TIME, 2)
        )
    except Exception as e:
        logger.error(f"Health status check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@health_router.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Check if essential services are ready
        db_check = await check_database_health()
        queue_check = await check_queue_health()
        
        if db_check.status == "unhealthy" or queue_check.status == "unhealthy":
            raise HTTPException(
                status_code=503, 
                detail="Service not ready - essential components unhealthy"
            )
        
        return {"status": "ready", "timestamp": datetime.utcnow()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@health_router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness probe"""
    try:
        # Simple check that the service is alive
        return {
            "status": "alive",
            "timestamp": datetime.utcnow(),
            "uptime_seconds": round(time.time() - SERVICE_START_TIME, 2)
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=500, detail="Service not alive")


@health_router.get("/metrics")
async def get_metrics():
    """Get basic metrics for monitoring"""
    try:
        async with get_async_session() as session:
            # Get basic stats
            total_items = await session.scalar(
                text("SELECT COUNT(*) FROM items")
            )
            
            items_last_hour = await session.scalar(
                text("SELECT COUNT(*) FROM items WHERE created_at > NOW() - INTERVAL '1 hour'")
            )
            
            active_runs = await session.scalar(
                text("SELECT COUNT(*) FROM runs WHERE status = 'running'")
            )
            
            failed_runs_last_hour = await session.scalar(
                text("SELECT COUNT(*) FROM runs WHERE status = 'failed' AND started_at > NOW() - INTERVAL '1 hour'")
            )
        
        import psutil
        
        return {
            "items_total": total_items,
            "items_last_hour": items_last_hour,
            "runs_active": active_runs,
            "runs_failed_last_hour": failed_runs_last_hour,
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "uptime_seconds": round(time.time() - SERVICE_START_TIME, 2),
            "timestamp": datetime.utcnow(),
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")
