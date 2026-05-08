"""
Security utilities for PopCorn API
Includes admin authentication, rate limiting, and security logging
"""
import logging
import time
from functools import wraps
from typing import Callable
from fastapi import HTTPException, Request
from app.config import ADMIN_ID

logger = logging.getLogger(__name__)

# ── Security Event Logging ────────────────────────────────────────────────────

class SecurityLogger:
    """Centralized security event logging"""
    
    @staticmethod
    def log_unauthorized_access(endpoint: str, ip: str, user_agent: str | None = None):
        """Log unauthorized access attempts"""
        logger.warning(
            f"🚨 UNAUTHORIZED ACCESS ATTEMPT | "
            f"Endpoint: {endpoint} | IP: {ip} | User-Agent: {user_agent or 'Unknown'}"
        )
    
    @staticmethod
    def log_rate_limit_exceeded(endpoint: str, ip: str):
        """Log rate limit violations"""
        logger.warning(
            f"⚠️ RATE LIMIT EXCEEDED | "
            f"Endpoint: {endpoint} | IP: {ip}"
        )
    
    @staticmethod
    def log_admin_action(action: str, admin_id: int, ip: str):
        """Log admin actions for audit trail"""
        logger.info(
            f"🔐 ADMIN ACTION | "
            f"Action: {action} | Admin ID: {admin_id} | IP: {ip}"
        )
    
    @staticmethod
    def log_suspicious_activity(reason: str, ip: str, details: dict | None = None):
        """Log suspicious activities"""
        details_str = f" | Details: {details}" if details else ""
        logger.warning(
            f"🔍 SUSPICIOUS ACTIVITY | "
            f"Reason: {reason} | IP: {ip}{details_str}"
        )


security_logger = SecurityLogger()


# ── Admin Authentication ──────────────────────────────────────────────────────

def require_admin(func: Callable):
    """
    Decorator to protect endpoints requiring admin authentication.
    Checks for admin_id in request body or query parameters.
    """
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Try to get admin_id from different sources
        admin_id = None
        
        # 1. Check query parameters
        if "admin_id" in request.query_params:
            try:
                admin_id = int(request.query_params["admin_id"])
            except (ValueError, TypeError):
                pass
        
        # 2. Check request body (for POST requests)
        if admin_id is None and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                if "admin_id" in body:
                    admin_id = int(body.get("admin_id"))
            except Exception:
                pass
        
        # 3. Check headers (X-Admin-ID)
        if admin_id is None and "X-Admin-ID" in request.headers:
            try:
                admin_id = int(request.headers["X-Admin-ID"])
            except (ValueError, TypeError):
                pass
        
        # Verify admin_id
        if admin_id != ADMIN_ID:
            security_logger.log_unauthorized_access(
                endpoint=request.url.path,
                ip=client_ip,
                user_agent=request.headers.get("user-agent", "Unknown")
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Admin authentication required"
            )
        
        # Log successful admin action (admin_id is guaranteed to be int here)
        security_logger.log_admin_action(
            action=f"{request.method} {request.url.path}",
            admin_id=admin_id,  # type: ignore
            ip=client_ip
        )
        
        return await func(request, *args, **kwargs)
    
    return wrapper


# ── Rate Limiting (Simple In-Memory Implementation) ───────────────────────────

class SimpleRateLimiter:
    """
    Simple in-memory rate limiter.
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(self):
        self._requests = {}  # {ip: [(timestamp, endpoint), ...]}
        self._cleanup_interval = 300  # Clean old entries every 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove entries older than 1 hour"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff = now - 3600  # 1 hour ago
        for ip in list(self._requests.keys()):
            self._requests[ip] = [
                (ts, ep) for ts, ep in self._requests[ip]
                if ts > cutoff
            ]
            if not self._requests[ip]:
                del self._requests[ip]
        
        self._last_cleanup = now
    
    def check_rate_limit(
        self,
        ip: str,
        endpoint: str,
        max_requests: int = 60,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Args:
            ip: Client IP address
            endpoint: API endpoint path
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            (is_allowed, requests_in_window)
        """
        self._cleanup_old_entries()
        
        now = time.time()
        cutoff = now - window_seconds
        
        # Get requests for this IP
        if ip not in self._requests:
            self._requests[ip] = []
        
        # Filter to requests in current window for this endpoint
        recent = [
            (ts, ep) for ts, ep in self._requests[ip]
            if ts > cutoff and ep == endpoint
        ]
        
        # Check limit
        is_allowed = len(recent) < max_requests
        
        if is_allowed:
            # Add this request
            self._requests[ip].append((now, endpoint))
        
        return is_allowed, len(recent)


rate_limiter = SimpleRateLimiter()


def rate_limit(max_requests: int = 60, window_seconds: int = 60):
    """
    Decorator to apply rate limiting to endpoints.
    
    Args:
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            client_ip = request.client.host if request.client else "unknown"
            endpoint = request.url.path
            
            is_allowed, count = rate_limiter.check_rate_limit(
                ip=client_ip,
                endpoint=endpoint,
                max_requests=max_requests,
                window_seconds=window_seconds
            )
            
            if not is_allowed:
                security_logger.log_rate_limit_exceeded(
                    endpoint=endpoint,
                    ip=client_ip
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s."
                )
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


# ── Request Validation ────────────────────────────────────────────────────────

def detect_suspicious_patterns(request: Request) -> list[str]:
    """
    Detect suspicious patterns in requests.
    Returns list of detected issues.
    """
    issues = []
    
    # Check for SQL injection patterns
    sql_patterns = ["'", "\"", "--", "/*", "*/", "union", "select", "drop", "insert"]
    for param_name, param_value in request.query_params.items():
        param_lower = str(param_value).lower()
        for pattern in sql_patterns:
            if pattern in param_lower:
                issues.append(f"Potential SQL injection in {param_name}")
                break
    
    # Check for path traversal
    if ".." in str(request.url.path):
        issues.append("Path traversal attempt detected")
    
    # Check for excessively long parameters
    for param_name, param_value in request.query_params.items():
        if len(str(param_value)) > 1000:
            issues.append(f"Excessively long parameter: {param_name}")
    
    return issues


async def validate_request_security(request: Request):
    """
    Validate request for security issues.
    Logs suspicious activity but doesn't block (for now).
    """
    issues = detect_suspicious_patterns(request)
    
    if issues:
        client_ip = request.client.host if request.client else "unknown"
        security_logger.log_suspicious_activity(
            reason="Suspicious request patterns detected",
            ip=client_ip,
            details={
                "endpoint": request.url.path,
                "issues": issues,
                "user_agent": request.headers.get("user-agent")
            }
        )

# Made with Bob
