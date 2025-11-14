from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.services.gemini import get_generation_model
from app.services.query_enhancement import enhance_query_for_search
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

# CORS Configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
environment = os.getenv("ENVIRONMENT", "production").lower()

if allowed_origins and allowed_origins.strip() == "*":
    # Allow all origins (not recommended for production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif allowed_origins:
    # Use configured origins
    origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
elif environment == "development":
    # Development defaults
    origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
# Production: No CORS middleware if no origins specified (most secure)


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


def _build_context(query: str) -> tuple[str, list[str]]:
    """
    Build context from knowledge base for the given query.
    Uses query enhancement to improve retrieval for short/specific queries.
    Returns tuple of (context_text, sources_list).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Enhance query with multiple variations for better retrieval
    # Use LLM expansion only for very short queries (adds latency)
    use_llm_expansion = len(query.split()) <= 3
    query_variations = enhance_query_for_search(query, use_llm=use_llm_expansion)
    
    logger.debug(f"Query: '{query}' -> {len(query_variations)} variations: {query_variations[:3]}")
    
    # Collect matches from all query variations
    all_matches = []
    seen_match_ids = set()
    
    # Try original query first with higher top_k and lower threshold
    original_matches = query_similar(query, top_k=15, min_score=0.15)  # Very low threshold for better recall
    logger.debug(f"Original query found {len(original_matches)} matches")
    
    for match in original_matches:
        match_id = getattr(match, "id", None)
        score = getattr(match, "score", 0.0)
        if match_id and match_id not in seen_match_ids:
            seen_match_ids.add(match_id)
            all_matches.append((match, score, "original"))
    
    # Try enhanced query variations (limit to avoid too many API calls)
    max_variations = 5 if use_llm_expansion else 7  # Fewer if using LLM (already slower)
    for variation in query_variations[1:max_variations]:
        if len(all_matches) >= 25:  # Limit total matches
            break
        variation_matches = query_similar(variation, top_k=8, min_score=0.15)
        for match in variation_matches:
            match_id = getattr(match, "id", None)
            score = getattr(match, "score", 0.0)
            if match_id and match_id not in seen_match_ids:
                seen_match_ids.add(match_id)
                all_matches.append((match, score, variation[:30]))  # Store which variation found it
    
    if not all_matches:
        logger.debug(f"No matches found for query: '{query}'")
        return "", []

    # Sort by score (highest first) - use the score we stored
    sorted_matches = sorted(all_matches, key=lambda x: x[1], reverse=True)
    logger.debug(f"Total unique matches: {len(sorted_matches)}, top score: {sorted_matches[0][1] if sorted_matches else 0:.3f}")

    snippets: list[str] = []
    sources: list[str] = []
    seen_texts = set()  # Avoid duplicate content
    total_length = 0
    
    for match_tuple in sorted_matches:
        match = match_tuple[0]
        metadata = getattr(match, "metadata", {}) or {}
        text = metadata.get("text")
        if not text or not text.strip():
            continue
        
        # Skip duplicates using a more robust check
        text_preview = text.strip()[:150]  # Use first 150 chars for duplicate detection
        if text_preview in seen_texts:
            continue
        seen_texts.add(text_preview)
        
        # Check length limit before adding
        # Don't include "Source:" prefix - let the model use information naturally
        snippet_text = text.strip()
        if total_length + len(snippet_text) > 6000:  # Increased limit for better context
            break
        
        snippets.append(snippet_text)
        sources.append(metadata.get("source", "Knowledge Base"))
        total_length += len(snippet_text)

    combined = "\n\n".join(snippets)
    logger.debug(f"Built context: {len(snippets)} snippets, {total_length} chars")
    return combined, sources


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> ChatResponse:
    session = _get_or_create_session(db, payload.session_id)

    user_message = models.Message(
        session_id=session.id,
        content=payload.message,
        is_user_message=True,
    )
    db.add(user_message)
    db.commit()

    context, _sources = _build_context(payload.message)
    
    # Language instruction - English only
    language_instruction = "Respond in English."
    
    # Get custom instructions from database
    app_settings = db.query(models.AppSettings).first()
    custom_instructions = app_settings.custom_instructions if app_settings else None
    
    # Use custom instructions if available, otherwise use defaults
    if custom_instructions and custom_instructions.strip():
        base_instructions = custom_instructions.strip()
    else:
        base_instructions = (
            "You are Cache Digitech's virtual assistant. Provide helpful, accurate, and natural answers in Cache Digitech's professional tone. "
            "Use the context provided below as your primary source of information. "
            "Answer questions naturally and conversationally - as if you're a knowledgeable team member speaking directly to the user. "
            "DO NOT mention 'knowledge base', 'according to our knowledge base', 'based on the information', or similar phrases. "
            "Simply answer the question naturally using the information provided. "
            "If the context doesn't fully answer the question, provide a helpful response based on what you know, but don't explicitly state where the information comes from. "
            "Be conversational, friendly, and human-like - write as if you're having a natural conversation. "
            "Stay concise and to the point, highlight next steps when relevant, and offer to connect with a human when appropriate."
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
        "FORMATTING GUIDELINES (CRITICAL - Always follow these):\n"
        "- ALWAYS use **bold** (double asterisks) for important keywords, especially in long answers.\n"
        "- Bold ALL service names, product names, key terms, important concepts, and section headers.\n"
        "- Bold important phrases like: **Service Name**, **Key Feature**, **Important Term**.\n"
        "- For lists of services or features, bold each item name: **Service 1**, **Service 2**, etc.\n"
        "- When describing multiple items, bold the name/title of each item consistently.\n"
        "- Include full URLs (https://...) when referencing websites - these will be automatically converted to clickable links.\n"
        "- Use clear structure with line breaks between sections.\n"
        "- For long answers, ensure EVERY important keyword, service name, or key term is bolded.\n"
        "\n"
        "Examples:\n"
        "- Good: We offer **Infrastructure Audit**, **Security Assessment**, and **Compliance Review** services.\n"
        "- Good: **Managed Infrastructure Services**: We provide 24/7 monitoring...\n"
        "- Good: Our **Cybersecurity Services** include **Firewall Management** and **Consulting Services**.\n"
        "- Bad: We offer Infrastructure Audit, Security Assessment services. (missing bold)\n"
    )

    if context:
        # Check if this is likely a long answer (service lists, detailed descriptions, etc.)
        is_long_answer_query = any(keyword in payload.message.lower() for keyword in [
            "services", "service", "offer", "provide", "what do you", "what can you",
            "capabilities", "features", "products", "solutions", "tell me about"
        ])
        
        formatting_emphasis = ""
        if is_long_answer_query:
            formatting_emphasis = (
                "\n\nIMPORTANT FORMATTING REMINDER:\n"
                "- This appears to be a question about services/offerings - ensure ALL service names, "
                "key terms, and important keywords are BOLDED using **double asterisks**.\n"
                "- Be consistent - if you mention a service name once, bold it every time.\n"
                "- For lists, bold each item name/title.\n"
            )
        
        prompt = (
            f"{instructions}\n\n"
            f"CONTEXT INFORMATION:\n{context}\n\n"
            f"USER QUESTION: {payload.message}\n\n"
            f"{formatting_emphasis}"
            f"INSTRUCTIONS:\n"
            f"- Answer the question naturally using the context information above\n"
            f"- Write as if you're a knowledgeable team member having a conversation\n"
            f"- DO NOT say 'based on the knowledge base', 'according to our knowledge base', or similar phrases\n"
            f"- DO NOT mention 'context', 'information provided', or 'sources'\n"
            f"- Simply answer directly and naturally - integrate the information seamlessly into your response\n"
            f"- If the context directly answers the question, use that information naturally\n"
            f"- If the context is partially relevant, combine it with your knowledge seamlessly\n"
            f"- Be conversational, friendly, and human-like\n"
            f"- ALWAYS bold important keywords, service names, and key terms - especially in long answers\n"
            f"- Always be accurate and professional"
        )
    else:
        # No context found - still allow the chatbot to respond naturally
        prompt = (
            f"{instructions}\n\n"
            f"USER QUESTION: {payload.message}\n\n"
            f"Provide a helpful, natural, and professional answer. "
            f"If you're unsure about Cache Digitech-specific information, suggest the user contact them directly. "
            f"Answer conversationally as if you're a team member."
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

    # Auto-training: Learn from this conversation (in background)
    # Only train if we have context (successful knowledge base response) and auto-training is enabled
    auto_training_enabled = os.getenv("ENABLE_AUTO_TRAINING", "true").lower() == "true"
    if context and auto_training_enabled:
        try:
            from app.services.auto_training import process_conversation_for_training
            
            # Add background task for auto-training
            # Pass session_id and message content (not db session - will create new one in task)
            background_tasks.add_task(
                process_conversation_for_training,
                session.id,
                payload.message,
                reply_text
            )
        except Exception as e:
            # Log but don't fail the request if training fails
            import logging
            logging.getLogger(__name__).warning(f"Auto-training setup failed: {e}")

    user_message_count = (
        db.query(models.Message)
        .filter(models.Message.session_id == session.id, models.Message.is_user_message.is_(True))
        .count()
    )
    prompt_for_info = user_message_count >= 2

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
                elif file_full_path.suffix == '.html':
                    content_type = 'text/html'
                else:
                    content_type = 'application/octet-stream'
            
            # Read file content
            with open(file_full_path, 'rb') as f:
                content = f.read()
            
            # Create response with aggressive no-cache headers
            from starlette.responses import Response
            response = Response(
                content=content,
                media_type=content_type,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Content-Type-Options": "nosniff",
                }
            )
            return response
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")


@app.get("/embed", response_class=HTMLResponse)
async def embed_widget(request: Request, db: Session = Depends(get_db)):
    """Serve the embeddable chatbot widget page."""
    # Get the API base URL - prefer configured URL, fallback to request URL
    api_base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # Check if there's a configured API URL in database
    try:
        app_settings = db.query(models.AppSettings).first()
        if app_settings and app_settings.api_base_url and app_settings.api_base_url.strip():
            api_base_url = app_settings.api_base_url.strip()
            print(f"Using configured API URL for embed: {api_base_url}")
        else:
            print(f"Using request-based API URL for embed: {api_base_url}")
    except Exception as e:
        # If database query fails, use request URL as fallback
        print(f"Warning: Could not query AppSettings, using request URL: {e}")
        api_base_url = f"{request.url.scheme}://{request.url.netloc}"
    
    # Add cache-busting version - use current timestamp + random to ensure uniqueness
    import time
    import random
    cache_version = f"{int(time.time())}-{random.randint(1000, 9999)}"
    
    # Escape values for safe HTML/JS embedding
    safe_api_url = api_base_url.replace('"', '\\"').replace("'", "\\'")
    safe_cache_version = cache_version.replace('"', '\\"').replace("'", "\\'")
    request_url = f"{request.url.scheme}://{request.url.netloc}"
    safe_request_url = request_url.replace('"', '\\"').replace("'", "\\'")
    
    embed_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Chatbot Widget</title>
    <link rel="stylesheet" crossorigin href="/static/widget/assets/index.css?v={safe_cache_version}">
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
        window.WIDGET_API_BASE_URL = "{safe_api_url}";
        // Force reload settings on every load
        window.WIDGET_FORCE_RELOAD = true;
        // Widget version for cache verification
        window.WIDGET_VERSION = "{safe_cache_version}";
        console.log("🚀 Chatbot Widget Embed Initialized:");
        console.log("  Version:", window.WIDGET_VERSION);
        console.log("  API Base URL:", window.WIDGET_API_BASE_URL);
        console.log("  Request URL:", "{safe_request_url}");
    </script>
    <script type="module" crossorigin src="/static/widget/assets/index.js?v={safe_cache_version}"></script>
</body>
</html>"""
    
    response = HTMLResponse(content=embed_html)
    # Allow embedding in iframes from any origin
    response.headers["Content-Security-Policy"] = "frame-ancestors *;"
    # Prevent caching of the embed page itself
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Widget-Version"] = cache_version
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Check database connection
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "service": "Cache Digitech Chatbot API",
        "version": "1.0.0"
    }
