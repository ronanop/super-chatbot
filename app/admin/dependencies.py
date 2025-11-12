from __future__ import annotations

import os
import secrets

from fastapi import Depends, HTTPException, Request, status
from starlette.responses import RedirectResponse


def require_admin(request: Request) -> str:
    """Check if user is authenticated via session."""
    username = os.getenv("ADMIN_USERNAME", "admin")
    
    # Check session
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
    
    return request.session.get("admin_username", username)


def get_admin_username(request: Request) -> str | None:
    """Get admin username from session if authenticated, None otherwise."""
    if request.session.get("admin_authenticated"):
        return request.session.get("admin_username", "admin")
    return None
