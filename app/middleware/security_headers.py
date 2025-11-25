"""
Maximum security headers middleware with nonce-based CSP.
"""
from __future__ import annotations

import secrets
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add maximum security headers to all responses with nonce-based CSP."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate nonce for this request (unique per request)
        nonce = secrets.token_urlsafe(16)
        
        # Store nonce in request state for template access
        request.state.csp_nonce = nonce
        
        response = await call_next(request)
        
        # Get nonce from request state (may have been regenerated)
        nonce = getattr(request.state, 'csp_nonce', secrets.token_urlsafe(16))
        
        # Security headers - Maximum protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        
        # Check if HTTPS is enabled
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https" or
            os.getenv("ENVIRONMENT", "").lower() == "production"
        )
        
        # Content Security Policy - Maximum security with nonces
        # No unsafe-inline or unsafe-eval - uses nonces instead
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://fonts.googleapis.com",
            f"style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.openai.com https://api.pinecone.io",
            "frame-src 'none'",
            "frame-ancestors 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests" if is_https else "",
            "block-all-mixed-content" if is_https else "",
        ]
        
        # Remove empty directives
        csp_directives = [d for d in csp_directives if d]
        csp = "; ".join(csp_directives)
        
        response.headers["Content-Security-Policy"] = csp
        
        # Report-Only CSP for monitoring (optional, can be removed in production)
        # Uncomment to enable CSP violation reporting:
        # response.headers["Content-Security-Policy-Report-Only"] = csp + " report-uri /csp-report"
        
        # Strict Transport Security (HSTS) - Only if HTTPS
        if is_https:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; "
                "includeSubDomains; "
                "preload"
            )
        
        # Permissions Policy - Restrict all unnecessary features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "bluetooth=(), "
            "clipboard-read=(), "
            "clipboard-write=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), "
            "fullscreen=(self), "
            "gamepad=(), "
            "keyboard-map=(), "
            "midi=(), "
            "notifications=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(), "
            "screen-wake-lock=(), "
            "speaker=(), "
            "sync-xhr=(), "
            "unoptimized-images=(), "
            "unsized-media=(), "
            "usb-device=(), "
            "vertical-scroll=(), "
            "wake-lock=(), "
            "xr-spatial-tracking=()"
        )
        
        # Additional security headers
        response.headers["X-DNS-Prefetch-Control"] = "off"
        response.headers["X-Download-Options"] = "noopen"
        response.headers["X-Powered-By"] = ""  # Remove server signature
        
        return response

