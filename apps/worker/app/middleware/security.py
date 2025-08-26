"""
Security middleware for FastAPI application
"""
import time
from typing import Dict, Optional
from collections import defaultdict, deque

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings
from ..logging_config import setup_logging

logger = setup_logging(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY" 
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Custom rate limiting middleware"""
    
    def __init__(self, app, calls: int = 60, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, deque] = defaultdict(deque)
        
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
            
        client_ip = get_remote_address(request)
        now = time.time()
        
        # Clean old requests
        client_requests = self.clients[client_ip]
        while client_requests and client_requests[0] <= now - self.period:
            client_requests.popleft()
            
        # Check rate limit
        if len(client_requests) >= self.calls:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.calls} per {self.period} seconds"
                }
            )
            
        # Add current request
        client_requests.append(now)
        
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for security monitoring"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = get_remote_address(request)
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Request completed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "process_time": f"{process_time:.3f}s",
                    "client_ip": client_ip,
                }
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "error": str(e),
                    "process_time": f"{process_time:.3f}s",
                    "client_ip": client_ip,
                }
            )
            raise


def setup_security_middleware(app: FastAPI):
    """Setup all security middleware"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware (only allow specific hosts in production)
    if settings.DEBUG is False:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.scrapesavee.com"]
        )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    if settings.ENABLE_RATE_LIMITING:
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.RATE_LIMIT_PER_MINUTE,
            period=60
        )
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # Rate limiter for specific endpoints
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info("Security middleware configured")
    
    return limiter


def validate_request_size(request: Request, max_size: int = 10 * 1024 * 1024):  # 10MB
    """Validate request body size"""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Request too large. Maximum size: {max_size} bytes"
        )


def sanitize_input(value: str) -> str:
    """Basic input sanitization"""
    if not value:
        return value
        
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", "&", "\"", "'", "/", "\\"]
    for char in dangerous_chars:
        value = value.replace(char, "")
        
    return value.strip()


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate uploaded filename"""
        if not filename:
            return False
            
        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return False
            
        # Check for dangerous extensions
        dangerous_extensions = [
            ".exe", ".bat", ".cmd", ".com", ".pif", ".scr", ".vbs", ".js", 
            ".jar", ".zip", ".rar", ".7z", ".php", ".asp", ".aspx", ".jsp"
        ]
        
        filename_lower = filename.lower()
        for ext in dangerous_extensions:
            if filename_lower.endswith(ext):
                return False
                
        return True
        
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL for safety"""
        if not url:
            return False
            
        # Must be HTTP/HTTPS
        if not url.startswith(("http://", "https://")):
            return False
            
        # Block internal/private IPs
        dangerous_hosts = [
            "localhost", "127.0.0.1", "0.0.0.0", "::1",
            "169.254.", "10.", "172.16.", "192.168."
        ]
        
        for host in dangerous_hosts:
            if host in url:
                return False
                
        return True
        
    @staticmethod
    def validate_json_size(data: dict, max_keys: int = 100, max_depth: int = 5) -> bool:
        """Validate JSON data size and structure"""
        def count_keys_and_depth(obj, current_depth=0):
            if current_depth > max_depth:
                return float('inf'), current_depth
                
            if isinstance(obj, dict):
                total_keys = len(obj)
                max_subdepth = current_depth
                
                for value in obj.values():
                    subkeys, subdepth = count_keys_and_depth(value, current_depth + 1)
                    total_keys += subkeys
                    max_subdepth = max(max_subdepth, subdepth)
                    
                return total_keys, max_subdepth
                
            elif isinstance(obj, list):
                total_keys = 0
                max_subdepth = current_depth
                
                for item in obj:
                    subkeys, subdepth = count_keys_and_depth(item, current_depth + 1)
                    total_keys += subkeys
                    max_subdepth = max(max_subdepth, subdepth)
                    
                return total_keys, max_subdepth
                
            return 0, current_depth
            
        total_keys, depth = count_keys_and_depth(data)
        return total_keys <= max_keys and depth <= max_depth

