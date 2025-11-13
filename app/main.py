from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.services.gemini import get_generation_model
from app.vectorstore.pinecone_store import query_similar
from app.admin.routes import router as admin_router

app = FastAPI(title="Cache Digitech Chatbot API")

# Add session middleware (must be before other middleware)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production"))

# Include admin router
app.include_router(admin_router)

@app.on_event("startup")
async def startup_event():
    """Log registered routes on startup."""
    import logging
    logger = logging.getLogger(__name__)
    admin_routes = [r.path for r in app.routes if hasattr(r, 'path') and r.path.startswith('/admin')]
    logger.info(f"Registered {len(admin_routes)} admin routes")
    if '/admin/logs' in admin_routes:
        logger.info("✓ /admin/logs route is registered")
    else:
        logger.error("✗ /admin/logs route is NOT registered!")
        logger.error(f"Available admin routes: {admin_routes}")

allowed_origins = os.getenv("ALLOWED_ORIGINS")
if allowed_origins and allowed_origins.strip() == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = ([origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
               if allowed_origins
               else [
                   "http://localhost:5173",
                   "http://localhost:5174",
                   "http://localhost:5175",
                   "http://127.0.0.1:5173",
                   "http://127.0.0.1:5174",
                   "http://127.0.0.1:5175",
               ])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: int
    prompt_for_info: bool = False


class UserInfoRequest(BaseModel):
    session_id: int
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class UserInfoResponse(BaseModel):
    status: str
    user_id: int


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_or_create_session(db: Session, session_id: int | None) -> models.ChatSession:
    if session_id:
        existing = db.get(models.ChatSession, session_id)
        if existing:
            return existing

    session = models.ChatSession()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _detect_language(text: str) -> str:
    """Detect language of the input text. Returns 'hindi', 'hinglish', or 'english'."""
    if not text or not text.strip():
        return "english"
    
    text_lower = text.lower()
    
    # Common Hinglish patterns (Hindi words written in English)
    hinglish_keywords = [
        'hai', 'hain', 'ho', 'hoga', 'hogi', 'honge', 'ka', 'ki', 'ke', 'ko', 'se', 'mein', 'par',
        'aur', 'ya', 'lekin', 'magar', 'kyunki', 'jab', 'tab', 'toh', 'bhi', 'hi', 'sirf', 'bas',
        'kya', 'kyun', 'kaise', 'kab', 'kahan', 'kisne', 'kisko', 'kiski', 'kiska',
        'main', 'tum', 'aap', 'woh', 'yeh', 'usne', 'maine', 'tumne', 'aapne',
        'acha', 'theek', 'sahi', 'galat', 'badhiya', 'mast', 'bohot', 'bahut',
        'chahiye', 'chahiye', 'karna', 'karna', 'hona', 'jana', 'aana', 'lena', 'dena'
    ]
    
    # Check for Devanagari script (Hindi) characters
    devanagari_chars = sum(1 for char in text if '\u0900' <= char <= '\u097F')
    # Check for English/Latin characters
    latin_chars = sum(1 for char in text if char.isalpha() and ord(char) < 128)
    
    # Count Hinglish keywords
    hinglish_count = sum(1 for keyword in hinglish_keywords if keyword in text_lower)
    
    total_chars = len([c for c in text if c.isalpha()])
    
    if total_chars == 0:
        return "english"
    
    devanagari_ratio = devanagari_chars / total_chars if total_chars > 0 else 0
    latin_ratio = latin_chars / total_chars if total_chars > 0 else 0
    
    # If Devanagari script is present
    if devanagari_chars > 0:
        # If significant Devanagari characters present
        if devanagari_ratio > 0.3:
            # Check if it's mixed (Hinglish)
            if latin_ratio > 0.15 or hinglish_count > 2:
                return "hinglish"
            else:
                return "hindi"
        elif devanagari_ratio > 0.1:
            # Some Devanagari but mostly other - likely Hinglish
            return "hinglish"
    
    # Check for Hinglish keywords (Hindi words in English script)
    if hinglish_count >= 3 or (hinglish_count >= 2 and latin_ratio > 0.5):
        return "hinglish"
    
    # Default to English
    return "english"


def _build_context(query: str) -> tuple[str, list[str]]:
    matches = query_similar(query, top_k=5)
    if not matches:
        return "", []

    snippets: list[str] = []
    sources: list[str] = []
    for match in matches:
        metadata = getattr(match, "metadata", {}) or {}
        text = metadata.get("text")
        if not text:
            continue
        source = metadata.get("source", "Knowledge Base")
        snippets.append(f"Source: {source}\n{text}")
        sources.append(source)

    combined = "\n\n".join(snippets)
    return combined, sources


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    session = _get_or_create_session(db, payload.session_id)

    user_message = models.Message(
        session_id=session.id,
        content=payload.message,
        is_user_message=True,
    )
    db.add(user_message)
    db.commit()

    context, _sources = _build_context(payload.message)
    
    # Detect user's language
    detected_language = _detect_language(payload.message)
    
    # Build language-specific instructions
    language_instruction = ""
    if detected_language == "hindi":
        language_instruction = "IMPORTANT: The user is communicating in Hindi. You MUST respond entirely in Hindi (Devanagari script). Use natural, conversational Hindi."
    elif detected_language == "hinglish":
        language_instruction = "IMPORTANT: The user is communicating in Hinglish (Hindi-English mix). You MUST respond in Hinglish - naturally mixing Hindi and English words as Indians commonly do. Use Devanagari script for Hindi words and English script for English words. This is the natural way Indians communicate."
    else:
        language_instruction = "Respond in English."
    
    # Get custom instructions from database
    app_settings = db.query(models.AppSettings).first()
    custom_instructions = app_settings.custom_instructions if app_settings else None
    
    # Use custom instructions if available, otherwise use defaults
    if custom_instructions and custom_instructions.strip():
        base_instructions = custom_instructions.strip()
    else:
        base_instructions = (
            "You are Cache Digitech's virtual assistant. Provide concise, precise answers in Cache Digitech's tone. "
            "Prioritize knowledge base context; if nothing relevant is found, draw on Gemini's general knowledge and frame the response as Cache Digitech's solution. "
            "Never offer long essays; stay to the point, highlight next steps, and offer to connect with a human when appropriate."
        )
    
    # Get current date and time
    now = datetime.now()
    current_date = now.strftime("%B %d, %Y")  # e.g., "January 15, 2024"
    current_time = now.strftime("%I:%M %p")  # e.g., "02:30 PM"
    current_datetime = now.strftime("%B %d, %Y at %I:%M %p")  # e.g., "January 15, 2024 at 02:30 PM"
    current_day = now.strftime("%A")  # e.g., "Monday"
    
    # Combine base instructions with language requirement and formatting guidelines
    instructions = (
        f"{base_instructions}\n\n"
        f"CURRENT DATE AND TIME INFORMATION:\n"
        f"- Today's date: {current_date} ({current_day})\n"
        f"- Current time: {current_time}\n"
        f"- Full date and time: {current_datetime}\n"
        f"- Use this information when answering questions about dates, times, or scheduling.\n\n"
        f"LANGUAGE REQUIREMENT: {language_instruction}\n\n"
        "Formatting guidelines:\n"
        "- Use **bold** (double asterisks) for important words, key terms, service names, and section headers.\n"
        "- Include full URLs (https://...) when referencing websites or resources - these will be automatically converted to clickable links.\n"
        "- Use clear structure with line breaks between sections.\n"
        "- Example: **Service Name**: Description text. Visit https://example.com for more details."
    )

    if context:
        prompt = (
            f"{instructions}\n\n"
            f"Context:\n{context}\n\n"
            f"User question: {payload.message}"
        )
    else:
        prompt = (
            f"{instructions}\n\n"
            f"No additional context is available. Answer the question if you can:\n"
            f"{payload.message}"
        )

    model = get_generation_model()
    try:
        result = model.generate_content(prompt)
    except Exception as exc:  # pragma: no cover - surfaces API issues
        raise HTTPException(status_code=502, detail=f"Gemini API error: {exc}") from exc

    reply_text = getattr(result, "text", None)
    if not reply_text:
        raise HTTPException(status_code=500, detail="Gemini API returned no text.")

    assistant_message = models.Message(
        session_id=session.id,
        content=reply_text,
        is_user_message=False,
    )
    db.add(assistant_message)
    db.commit()

    user_message_count = (
        db.query(models.Message)
        .filter(models.Message.session_id == session.id, models.Message.is_user_message.is_(True))
        .count()
    )
    prompt_for_info = user_message_count >= 3

    return ChatResponse(reply=reply_text, session_id=session.id, prompt_for_info=prompt_for_info)


@app.post("/user-info", response_model=UserInfoResponse)
async def submit_user_info(payload: UserInfoRequest, db: Session = Depends(get_db)) -> UserInfoResponse:
    session = db.get(models.ChatSession, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    email = payload.email.lower() if payload.email else None
    user = None
    if email:
        user = (
            db.query(models.User)
            .filter(models.User.email == email)
            .one_or_none()
        )

    if not user:
        user = models.User()
        db.add(user)

    name = payload.name.strip() if payload.name else None
    phone = payload.phone.strip() if payload.phone else None

    if name:
        user.name = name
    if email:
        user.email = email
    if phone:
        user.phone = phone

    db.flush()

    session.user_id = user.id
    db.add(session)
    db.commit()
    db.refresh(user)

    return UserInfoResponse(status="ok", user_id=user.id)


# Mount static files for widget (if dist folder exists) with no-cache headers
widget_dist_path = Path("chatbot-widget/dist")
if widget_dist_path.exists():
    from fastapi.responses import FileResponse
    import mimetypes
    
    @app.get("/static/widget/{file_path:path}")
    async def serve_widget_static(file_path: str, request: Request):
        """Serve widget static files with no-cache headers."""
        # Normalize the path to prevent directory traversal
        file_full_path = (widget_dist_path / file_path).resolve()
        
        # Ensure the file is within the dist directory
        try:
            file_full_path.relative_to(widget_dist_path.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if file_full_path.exists() and file_full_path.is_file():
            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_full_path))
            if not content_type:
                if file_full_path.suffix == '.js':
                    content_type = 'application/javascript'
                elif file_full_path.suffix == '.css':
                    content_type = 'text/css'
                else:
                    content_type = 'application/octet-stream'
            
            # Read file content
            with open(file_full_path, 'rb') as f:
                content = f.read()
            
            # Create response with no-cache headers
            from starlette.responses import Response
            response = Response(
                content=content,
                media_type=content_type,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "ETag": f'"{file_full_path.stat().st_mtime}"',  # Use file modification time as ETag
                    "Last-Modified": "",  # Clear Last-Modified to prevent caching
                }
            )
            return response
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


@app.get("/embed", response_class=HTMLResponse)
async def embed_widget(request: Request):
    """Serve the embeddable chatbot widget page."""
    # Get the API base URL from request
    api_base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # Add cache-busting version - use current timestamp + random to ensure uniqueness
    import time
    import random
    cache_version = f"{int(time.time())}-{random.randint(1000, 9999)}"
    
    embed_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Chatbot Widget</title>
    <link rel="stylesheet" crossorigin href="/static/widget/assets/index.css?v={cache_version}">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
        }}
        #root {{
            width: 100%;
            height: 100%;
        }}
    </style>
</head>
<body>
    <div id="root"></div>
    <script>
        // Set API base URL for the widget
        window.WIDGET_API_BASE_URL = "{api_base_url}";
        // Force reload settings on every load
        window.WIDGET_FORCE_RELOAD = true;
        // Widget version for cache verification
        window.WIDGET_VERSION = "{cache_version}";
        console.log("Chatbot Widget loaded - Version:", window.WIDGET_VERSION);
    </script>
    <script type="module" crossorigin src="/static/widget/assets/index.js?v={cache_version}"></script>
</body>
</html>"""
    
    response = HTMLResponse(content=embed_html)
    # Allow embedding in iframes from any origin
    response.headers["Content-Security-Policy"] = "frame-ancestors *;"
    # Prevent caching of the embed page itself
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
