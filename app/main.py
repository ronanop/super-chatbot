from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uuid
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import SessionLocal
from app.services.query_enhancement import enhance_query_for_search
from app.vectorstore.pinecone_store import query_similar
from app.admin.routes import router as admin_router
from app.services.llm import generate_content, get_llm_provider_from_db, is_image_generation_request, extract_image_prompt, generate_image_openai
from app.auth.utils import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user as get_auth_user
from app.middleware.security_headers import SecurityHeadersMiddleware

app = FastAPI(title="Cache Digitech Chatbot API")

# CORS Configuration - MUST be added BEFORE other middleware and routes
# This ensures CORS headers are always included in responses
allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
environment = os.getenv("ENVIRONMENT", "development").lower()

# Default localhost origins for development
default_localhost_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

# Always add CORS middleware FIRST (before other middleware)
# In development, allow all origins for easier testing
if environment == "development" or not allowed_origins:
    # Development mode: Allow all origins (but without credentials to avoid browser restrictions)
    # Browsers don't allow allow_origins=["*"] with allow_credentials=True
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=False,  # Set to False when using wildcard
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
elif allowed_origins and allowed_origins.strip() == "*":
    # Explicit wildcard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
elif allowed_origins:
    # Use configured origins
    origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]
    # Add localhost origins if not already present
    for localhost_origin in default_localhost_origins:
        if localhost_origin not in origins:
            origins.append(localhost_origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

# Add session middleware (after CORS) with enhanced security
session_secret_key = os.getenv("SESSION_SECRET_KEY")
if not session_secret_key or session_secret_key == "your-secret-key-change-in-production":
    import secrets
    session_secret_key = secrets.token_urlsafe(32)
    print("⚠️  WARNING: Using auto-generated SESSION_SECRET_KEY. Set SESSION_SECRET_KEY environment variable for production!")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret_key,
    max_age=8 * 60 * 60,  # 8 hours session timeout
    same_site="lax",  # CSRF protection
    https_only=False,  # Set to True in production with HTTPS
    # Note: HttpOnly and Secure flags are set automatically by SessionMiddleware
    # Secure flag requires https_only=True when HTTPS is enabled
)

# Add security headers middleware (after session middleware)
app.add_middleware(SecurityHeadersMiddleware)

# Global exception handler to ensure CORS headers are always included
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler that ensures CORS headers are always included."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the error
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    logger.error(traceback.format_exc())
    
    # Create error response with CORS headers
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        status_code = exc.status_code
        detail = exc.detail
    else:
        status_code = 500
        detail = "Internal server error"
    
    response = JSONResponse(
        status_code=status_code,
        content={"detail": detail if isinstance(detail, str) else str(detail)},
    )
    
    # Add CORS headers manually
    origin = request.headers.get("origin")
    if origin or environment == "development":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# Include admin router
app.include_router(admin_router)

@app.on_event("startup")
async def startup_event():
    """Log registered routes on startup."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"CORS Configuration: ENVIRONMENT={environment}, ALLOWED_ORIGINS={allowed_origins or 'not set (using defaults)'}")
    admin_routes = [r.path for r in app.routes if hasattr(r, 'path') and r.path.startswith('/admin')]
    logger.info(f"Registered {len(admin_routes)} admin routes")
    if '/admin/logs' in admin_routes:
        logger.info("✓ /admin/logs route is registered")
    else:
        logger.error("✗ /admin/logs route is NOT registered!")
        logger.error(f"Available admin routes: {admin_routes}")



class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None
    image_url: str | None = None  # URL to uploaded image for vision analysis
    document_ids: list[int] | None = None  # IDs of documents to include in context


class ChatResponse(BaseModel):
    reply: str
    session_id: int
    prompt_for_info: bool = False
    image_url: str | None = None  # URL of generated image if image generation was requested


class UserInfoRequest(BaseModel):
    session_id: int
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class UserInfoResponse(BaseModel):
    status: str
    user_id: int


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None


class RegisterResponse(BaseModel):
    status: str
    message: str
    token: str | None = None
    email: str | None = None
    user_id: int | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    status: str
    message: str
    token: str | None = None
    email: str | None = None
    user_id: int | None = None


class ProfileResponse(BaseModel):
    id: int
    email: str | None
    name: str | None
    phone: str | None


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/auth/register", response_model=RegisterResponse)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing_user:
        return RegisterResponse(
            status="error",
            message="Email already registered. Please login instead.",
        )
    
    # Create new user
    password_hash = hash_password(payload.password)
    user = models.User(
        email=payload.email.lower(),
        password_hash=password_hash,
        name=payload.name.strip() if payload.name else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create access token
    token = create_access_token(user.id, user.email)
    
    return RegisterResponse(
        status="success",
        message="Registration successful!",
        token=token,
        email=user.email,
        user_id=user.id,
    )


@app.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    """Login user and return JWT token with rate limiting protection."""
    from app.auth.rate_limit import (
        get_client_ip,
        check_rate_limit,
        record_failed_login_attempt,
        record_successful_login
    )
    
    # Get client IP for rate limiting
    ip_address = get_client_ip(request)
    
    # Check rate limiting
    rate_ok, rate_error = check_rate_limit(ip_address)
    if not rate_ok:
        return LoginResponse(
            status="error",
            message=rate_error or "Too many requests. Please try again later.",
        )
    
    # Find user by email
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    
    # Always use same error message to prevent user enumeration
    generic_error = LoginResponse(
        status="error",
        message="Invalid email or password.",
    )
    
    if not user:
        # Record failed attempt even if user doesn't exist (prevents timing attacks)
        record_failed_login_attempt(ip_address)
        return generic_error
    
    # Check password
    if not user.password_hash or not verify_password(payload.password, user.password_hash):
        # Record failed attempt
        is_locked, lockout_until = record_failed_login_attempt(ip_address)
        if is_locked:
            remaining_minutes = int((lockout_until - time.time()) / 60) + 1
            return LoginResponse(
                status="error",
                message=f"Too many failed attempts. IP locked for {remaining_minutes} minutes.",
            )
        return generic_error
    
    # Successful login - clear failed attempts
    record_successful_login(ip_address)
    
    # Create access token
    token = create_access_token(user.id, user.email)
    
    return LoginResponse(
        status="success",
        message="Login successful!",
        token=token,
        email=user.email,
        user_id=user.id,
    )


def _get_or_create_session(db: Session, session_id: int | None, user_id: int | None = None) -> models.ChatSession:
    """Get existing session or create a new one. Associate with user if user_id provided."""
    if session_id:
        existing = db.get(models.ChatSession, session_id)
        if existing:
            # Ensure session is associated with the user
            if user_id and not existing.user_id:
                existing.user_id = user_id
                db.add(existing)
                db.commit()
            return existing

    # Create new session
    session = models.ChatSession()
    if user_id:
        session.user_id = user_id
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _get_conversation_history(db: Session, session_id: int, limit: int = 20) -> list[dict]:
    """Get conversation history for a session, excluding the current message."""
    messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.timestamp.asc())
        .limit(limit)
        .all()
    )
    
    history = []
    for msg in messages:
        # Skip the last message (current one being processed)
        if msg == messages[-1]:
            continue
            
        role = "user" if msg.is_user_message else "assistant"
        content = msg.content or ""
        
        # Include image info in user messages if present
        if msg.is_user_message and msg.image_url:
            content = f"{content} [Image attached: {msg.image_url}]"
        
        history.append({
            "role": role,
            "content": content
        })
    
    return history


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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_auth_user),  # Protected endpoint
) -> ChatResponse:
    """Chat endpoint - handles user messages and generates AI responses."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Chat request received from user {current_user.id}: message length={len(payload.message) if payload.message else 0}")
        
        # Create or get session, associate with authenticated user
        session = _get_or_create_session(db, payload.session_id, user_id=current_user.id)

        user_message = models.Message(
            session_id=session.id,
            content=payload.message,
            is_user_message=True,
            image_url=payload.image_url,  # Store image URL if provided
        )
        db.add(user_message)
        db.commit()

        # Get conversation history (excluding the current message we just added)
        conversation_history = _get_conversation_history(db, session.id, limit=20)

        # Skip knowledge base search if image is provided (vision analysis doesn't need KB context)
        # Get document context if document IDs provided
        document_context = ""
        if payload.document_ids:
            documents = (
                db.query(models.ChatDocument)
                .filter(
                    models.ChatDocument.id.in_(payload.document_ids),
                    models.ChatDocument.session_id == session.id
                )
                .all()
            )
            document_texts = []
            for doc in documents:
                if doc.extracted_text:
                    document_texts.append(f"=== Document: {doc.filename} ===\n{doc.extracted_text}")
            if document_texts:
                document_context = "\n\n".join(document_texts)
        
        if payload.image_url:
            context = ""
            _sources = []
        else:
            context, _sources = _build_context(payload.message)
            
        # Combine document context with knowledge base context
        if document_context:
            if context:
                context = f"{document_context}\n\n--- Knowledge Base Context ---\n{context}"
            else:
                context = document_context
        
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

        # Check if user is asking for image generation (DALL-E)
        image_url = None
        
        if payload.image_url:
            # Image input - use GPT-4 Vision
            # Normalize image URL - if it's a full URL, use it; if relative, make sure it's correct
            image_url_to_use = payload.image_url
            if image_url_to_use.startswith("/uploads/"):
                # It's already a relative path, keep it
                pass
            elif "/uploads/chat_images/" in image_url_to_use:
                # Extract relative path from full URL
                parts = image_url_to_use.split("/uploads/chat_images/")
                if len(parts) > 1:
                    image_url_to_use = f"/uploads/chat_images/{parts[-1]}"
            
            logger.info(f"=== IMAGE ANALYSIS REQUEST ===")
            logger.info(f"Original image_url: {payload.image_url}")
            logger.info(f"Normalized image_url: {image_url_to_use}")
            logger.info(f"User message: {payload.message}")
            logger.info(f"Session ID: {session.id}")
            
            # Build a better prompt for image analysis that explicitly tells the model to analyze the image
            user_question = payload.message.strip() if payload.message else "What do you see in this image?"
            
            image_prompt = (
                f"Analyze the image that the user has shared with you. "
                f"Look at the image carefully and describe what you see. "
                f"Answer the user's question: {user_question}\n\n"
                f"Be detailed and specific about what you observe in the image."
            )
            
            try:
                logger.info(f"Calling generate_content with image_url: {image_url_to_use}")
                result = generate_content(
                    image_prompt, 
                    db=db, 
                    image_url=image_url_to_use,  # Use normalized URL
                    conversation_history=conversation_history  # Include conversation history
                )
                reply_text = result.text
                logger.info(f"Image analysis successful. Response length: {len(reply_text)} chars")
                logger.info(f"Response preview: {reply_text[:200]}...")
            except Exception as exc:
                logger.error(f"=== IMAGE ANALYSIS ERROR ===")
                logger.error(f"Error type: {type(exc).__name__}")
                logger.error(f"Error message: {str(exc)}")
                logger.error(f"Full traceback:", exc_info=True)
                raise HTTPException(status_code=502, detail=f"Image analysis failed: {str(exc)}") from exc
        elif is_image_generation_request(payload.message):
            # Image generation request (DALL-E)
            try:
                image_prompt = extract_image_prompt(payload.message)
                image_url = generate_image_openai(image_prompt)
                reply_text = "Here you go!"
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(f"Image generation failed: {exc}")
                # Fall through to normal text generation
                try:
                    result = generate_content(
                        prompt, 
                        db=db, 
                        image_url=None,
                        conversation_history=conversation_history  # Include conversation history
                    )
                    reply_text = result.text + f"\n\n*Note: I couldn't generate an image at this time.*"
                except Exception as text_exc:
                    raise HTTPException(status_code=502, detail=f"OpenAI API error: {text_exc}") from text_exc
        else:
            # Normal text generation
            try:
                result = generate_content(
                    prompt, 
                    db=db, 
                    image_url=None,
                    conversation_history=conversation_history  # Include conversation history
                )
                reply_text = result.text
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc}") from exc

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

        return ChatResponse(reply=reply_text, session_id=session.id, prompt_for_info=prompt_for_info, image_url=image_url)
    except HTTPException:
        # Re-raise HTTPExceptions (they already have proper status codes and CORS headers via middleware)
        raise
    except Exception as e:
        # Log the error and re-raise as HTTPException with CORS headers
        logger.error(f"Error in chat endpoint: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@app.post("/chat/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    """Upload an image for vision analysis. Returns the image URL."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}")
    
    # Validate file size (max 20MB)
    file_content = await file.read()
    if len(file_content) > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 20MB.")
    
    # Create uploads directory
    uploads_dir = Path("uploads/chat_images")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower() or ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = uploads_dir / unique_filename
    
    # Save file
    file_path.write_bytes(file_content)
    
    # Return URL (relative path - frontend will construct full URL)
    image_url = f"/uploads/chat_images/{unique_filename}"
    
    return {"image_url": image_url, "filename": unique_filename}


@app.get("/uploads/chat_images/{filename}")
async def serve_chat_image(filename: str):
    """Serve uploaded chat images."""
    file_path = Path("uploads/chat_images") / filename
    
    # Security check
    try:
        file_path.resolve().relative_to(Path("uploads/chat_images").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="Image not found")


@app.post("/chat/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    session_id: int | None = None,
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a document (PDF or TXT) for chat context. Returns document ID and extracted text preview."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = Path(file.filename).suffix.lower()
    allowed_extensions = [".pdf", ".txt"]
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Validate file size (max 50MB for documents)
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB.")
    
    # Create or get session
    session = _get_or_create_session(db, session_id, user_id=current_user.id)
    
    # Create uploads directory
    uploads_dir = Path("uploads/chat_documents")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = uploads_dir / unique_filename
    
    # Save file
    file_path.write_bytes(file_content)
    
    # Extract text from document
    extracted_text = None
    try:
        if file_ext == ".pdf":
            extracted_text = _extract_text_from_pdf(file_path)
        elif file_ext == ".txt":
            extracted_text = _extract_text_from_txt(file_path)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to extract text from document: {e}", exc_info=True)
        # Continue even if extraction fails - user can still reference the document
    
    # Store document in database
    document = models.ChatDocument(
        session_id=session.id,
        filename=file.filename,
        file_path=str(file_path),
        file_type=file_ext[1:],  # Remove the dot
        file_size=file_size,
        extracted_text=extracted_text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Return document info
    return {
        "document_id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "text_preview": extracted_text[:500] + "..." if extracted_text and len(extracted_text) > 500 else extracted_text,
        "session_id": session.id,
    }


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n\n".join(text_parts)
    except Exception as e:
        # Fallback to PyPDF2 if pdfplumber fails
        try:
            import PyPDF2
            text_parts = []
            with open(pdf_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as fallback_error:
            raise Exception(f"Failed to extract text from PDF: {e}, fallback also failed: {fallback_error}")


def _extract_text_from_txt(txt_path: Path) -> str:
    """Extract text from a TXT file."""
    try:
        # Try UTF-8 first
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback to latin-1 if UTF-8 fails
        try:
            with open(txt_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to extract text from TXT file: {e}")


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


@app.get("/user/profile", response_model=ProfileResponse)
async def get_user_profile(
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Get current user's profile."""
    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
    )


@app.put("/user/profile", response_model=ProfileResponse)
async def update_user_profile(
    payload: ProfileUpdateRequest,
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    """Update current user's profile."""
    if payload.name is not None:
        current_user.name = payload.name.strip() if payload.name else None
    if payload.phone is not None:
        current_user.phone = payload.phone.strip() if payload.phone else None
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    return ProfileResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        phone=current_user.phone,
    )


@app.post("/user/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> dict:
    """Change user's password."""
    # Verify current password
    if not current_user.password_hash or not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    
    # Update password
    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
    
    return {"status": "success", "message": "Password changed successfully."}


@app.post("/chat/new")
async def create_new_chat(
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a new chat session for the authenticated user."""
    session = models.ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return {"session_id": session.id}


@app.get("/chat/sessions")
async def get_chat_sessions(
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get all chat sessions for the authenticated user."""
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .order_by(models.ChatSession.started_at.desc())
        .all()
    )
    
    formatted_sessions = []
    for session in sessions:
        # Get the first user message as preview
        first_message = (
            db.query(models.Message)
            .filter(
                models.Message.session_id == session.id,
                models.Message.is_user_message.is_(True)
            )
            .order_by(models.Message.timestamp.asc())
            .first()
        )
        
        preview = first_message.content[:50] + "..." if first_message and first_message.content else "New Chat"
        
        formatted_sessions.append({
            "id": session.id,
            "preview": preview,
            "started_at": session.started_at.isoformat() if session.started_at else None,
        })
    
    return {"sessions": formatted_sessions}


@app.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get all messages for a specific chat session."""
    session = db.get(models.ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    # Verify session belongs to current user
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.timestamp.asc())
        .all()
    )
    
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "id": msg.id,
            "content": msg.content,
            "is_user_message": msg.is_user_message,
            "image_url": msg.image_url,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
        })
    
    return {"messages": formatted_messages}


@app.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    current_user: models.User = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a chat session."""
    session = db.get(models.ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    
    # Verify session belongs to current user
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    db.delete(session)
    db.commit()
    
    return {"status": "success", "message": "Chat session deleted successfully."}


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
