from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from starlette.responses import RedirectResponse


# Session timeout (8 hours of inactivity)
SESSION_TIMEOUT_HOURS = 8


def require_admin(request: Request) -> str:
    """Check if user is authenticated via session with enhanced security checks."""
    username = os.getenv("ADMIN_USERNAME", "admin")
    
    # Check session exists
    if not request.session.get("admin_authenticated"):
        # If this is an API request (JSON), return 401
        if request.headers.get("accept", "").startswith("application/json"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )
        # Otherwise raise exception with redirect header
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"},
        )
    
    # Check session timeout
    login_time_str = request.session.get("login_time")
    if login_time_str:
        try:
            login_time = datetime.fromisoformat(login_time_str)
            if datetime.now() - login_time > timedelta(hours=SESSION_TIMEOUT_HOURS):
                # Session expired
                request.session.clear()
                if request.headers.get("accept", "").startswith("application/json"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired. Please login again.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={"Location": "/admin/login"},
                )
        except (ValueError, TypeError):
            # Invalid login_time, clear session
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/admin/login"},
            )
    
    # Update last activity time (optional - for tracking)
    request.session["last_activity"] = datetime.now().isoformat()
    
    return request.session.get("admin_username", username)


def get_admin_username(request: Request) -> str | None:
    """Get admin username from session if authenticated, None otherwise."""
    if request.session.get("admin_authenticated"):
        return request.session.get("admin_username", "admin")
    return None
