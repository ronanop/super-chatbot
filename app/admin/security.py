"""
Security utilities for admin panel protection against brute force attacks and unauthorized access.
"""
from __future__ import annotations

import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from app.db import models


# Rate limiting configuration
MAX_LOGIN_ATTEMPTS = 5  # Maximum failed attempts before lockout
LOCKOUT_DURATION_MINUTES = 15  # Lockout duration in minutes
RATE_LIMIT_WINDOW_SECONDS = 60  # Time window for rate limiting
MAX_REQUESTS_PER_WINDOW = 10  # Max requests per window


# In-memory rate limiting (for IP-based protection)
_ip_attempts: dict[str, list[float]] = defaultdict(list)
_ip_lockouts: dict[str, datetime] = {}
_ip_request_counts: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request) -> str:
    """
    Extract client IP address from request.
    Validates X-Forwarded-For header against trusted proxies to prevent IP spoofing.
    """
    import os
    
    # Get trusted proxy IPs from environment (comma-separated)
    # In production, set TRUSTED_PROXIES to your load balancer/proxy IPs
    trusted_proxies = os.getenv("TRUSTED_PROXIES", "").split(",")
    trusted_proxies = [p.strip() for p in trusted_proxies if p.strip()]
    
    # Get direct client IP first
    direct_ip = None
    if hasattr(request.client, "host"):
        direct_ip = request.client.host
    
    # Check X-Forwarded-For header (only trust if from trusted proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and direct_ip in trusted_proxies:
        # Only trust X-Forwarded-For if request came from trusted proxy
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP (only trust if from trusted proxy)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and direct_ip in trusted_proxies:
        return real_ip.strip()
    
    # Fallback to direct client IP (most secure if no trusted proxy)
    if direct_ip:
        return direct_ip
    
    return "unknown"


def is_ip_locked_out(ip_address: str) -> tuple[bool, Optional[datetime]]:
    """Check if IP is currently locked out."""
    if ip_address in _ip_lockouts:
        lockout_time = _ip_lockouts[ip_address]
        if datetime.now() < lockout_time:
            return True, lockout_time
        else:
            # Lockout expired, remove it
            del _ip_lockouts[ip_address]
    
    return False, None


def record_failed_login_attempt(db: Session, ip_address: str, username: str, reason: str = "invalid_credentials"):
    """Record a failed login attempt in database and memory."""
    # Record in database
    attempt = models.AdminLoginAttempt(
        ip_address=ip_address,
        username=username,
        success=False,
        reason=reason,
        attempted_at=datetime.now()
    )
    db.add(attempt)
    db.commit()
    
    # Record in memory for rate limiting
    current_time = time.time()
    _ip_attempts[ip_address].append(current_time)
    
    # Clean old attempts (older than lockout duration)
    cutoff_time = current_time - (LOCKOUT_DURATION_MINUTES * 60)
    _ip_attempts[ip_address] = [
        t for t in _ip_attempts[ip_address] if t > cutoff_time
    ]
    
    # Check if we should lock out this IP
    if len(_ip_attempts[ip_address]) >= MAX_LOGIN_ATTEMPTS:
        lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        _ip_lockouts[ip_address] = lockout_until
        return True, lockout_until
    
    return False, None


def record_successful_login(db: Session, ip_address: str, username: str):
    """Record a successful login attempt."""
    attempt = models.AdminLoginAttempt(
        ip_address=ip_address,
        username=username,
        success=True,
        reason="success",
        attempted_at=datetime.now()
    )
    db.add(attempt)
    db.commit()
    
    # Clear failed attempts for this IP on successful login
    if ip_address in _ip_attempts:
        del _ip_attempts[ip_address]
    if ip_address in _ip_lockouts:
        del _ip_lockouts[ip_address]


def check_rate_limit(ip_address: str) -> tuple[bool, Optional[str]]:
    """Check if IP has exceeded rate limit for requests."""
    current_time = time.time()
    
    # Clean old requests
    cutoff_time = current_time - RATE_LIMIT_WINDOW_SECONDS
    _ip_request_counts[ip_address] = [
        t for t in _ip_request_counts[ip_address] if t > cutoff_time
    ]
    
    # Check rate limit
    if len(_ip_request_counts[ip_address]) >= MAX_REQUESTS_PER_WINDOW:
        return False, f"Too many requests. Please wait {RATE_LIMIT_WINDOW_SECONDS} seconds."
    
    # Record this request
    _ip_request_counts[ip_address].append(current_time)
    return True, None


def get_recent_failed_attempts(db: Session, ip_address: str, minutes: int = 15) -> int:
    """Get count of recent failed login attempts for an IP."""
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    count = db.query(models.AdminLoginAttempt).filter(
        models.AdminLoginAttempt.ip_address == ip_address,
        models.AdminLoginAttempt.success == False,
        models.AdminLoginAttempt.attempted_at >= cutoff_time
    ).count()
    return count


def generate_csrf_token() -> str:
    """Generate a CSRF token."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(session_token: Optional[str], form_token: Optional[str]) -> bool:
    """Verify CSRF token."""
    if not session_token or not form_token:
        return False
    return secrets.compare_digest(session_token, form_token)


def hash_ip_for_logging(ip_address: str) -> str:
    """Hash IP address for logging (privacy-friendly)."""
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

