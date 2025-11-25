"""
Rate limiting for user authentication endpoints.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Optional
from fastapi import Request, HTTPException, status


# Rate limiting configuration for user login
MAX_LOGIN_ATTEMPTS = 5  # Maximum failed attempts before lockout
LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutes lockout
RATE_LIMIT_WINDOW_SECONDS = 60  # Time window for rate limiting
MAX_REQUESTS_PER_WINDOW = 10  # Max requests per window per IP


# In-memory rate limiting (for IP-based protection)
_ip_attempts: dict[str, list[float]] = defaultdict(list)
_ip_lockouts: dict[str, float] = {}
_ip_request_counts: dict[str, list[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    Validates X-Forwarded-For header against trusted proxies to prevent IP spoofing.
    """
    import os
    
    # Get trusted proxy IPs from environment (comma-separated)
    trusted_proxies = os.getenv("TRUSTED_PROXIES", "").split(",")
    trusted_proxies = [p.strip() for p in trusted_proxies if p.strip()]
    
    # Get direct client IP first
    direct_ip = None
    if hasattr(request.client, "host"):
        direct_ip = request.client.host
    
    # Check X-Forwarded-For header (only trust if from trusted proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and direct_ip in trusted_proxies:
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP (only trust if from trusted proxy)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip and direct_ip in trusted_proxies:
        return real_ip.strip()
    
    # Fallback to direct client IP
    if direct_ip:
        return direct_ip
    
    return "unknown"


def check_rate_limit(ip_address: str) -> tuple[bool, Optional[str]]:
    """Check if IP has exceeded rate limit for requests."""
    current_time = time.time()
    
    # Check if IP is locked out
    if ip_address in _ip_lockouts:
        lockout_until = _ip_lockouts[ip_address]
        if current_time < lockout_until:
            remaining_seconds = int(lockout_until - current_time)
            remaining_minutes = (remaining_seconds // 60) + 1
            return False, f"Too many failed attempts. IP locked for {remaining_minutes} minutes."
        else:
            # Lockout expired
            del _ip_lockouts[ip_address]
    
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


def record_failed_login_attempt(ip_address: str) -> tuple[bool, Optional[float]]:
    """Record a failed login attempt and check if IP should be locked out."""
    current_time = time.time()
    
    # Record attempt
    _ip_attempts[ip_address].append(current_time)
    
    # Clean old attempts
    cutoff_time = current_time - LOCKOUT_DURATION_SECONDS
    _ip_attempts[ip_address] = [
        t for t in _ip_attempts[ip_address] if t > cutoff_time
    ]
    
    # Check if we should lock out this IP
    if len(_ip_attempts[ip_address]) >= MAX_LOGIN_ATTEMPTS:
        lockout_until = current_time + LOCKOUT_DURATION_SECONDS
        _ip_lockouts[ip_address] = lockout_until
        return True, lockout_until
    
    return False, None


def record_successful_login(ip_address: str):
    """Clear failed attempts for this IP on successful login."""
    if ip_address in _ip_attempts:
        del _ip_attempts[ip_address]
    if ip_address in _ip_lockouts:
        del _ip_lockouts[ip_address]

