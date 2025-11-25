from __future__ import annotations

import logging
import os
import re
import shutil
import sys
import textwrap
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Generator, List
from string import Template
import uuid

# Configure logging to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from app.admin.dependencies import require_admin, get_admin_username
from app.admin.log_handler import get_admin_log_handler, setup_admin_logging
from app.admin.input_validation import (
    ValidationError,
    validate_folder_name,
    validate_display_name,
    validate_filename,
    validate_file_upload,
    validate_path,
    validate_url,
    validate_hex_color,
    validate_id,
    validate_confirm_text,
    validate_query_param,
    validate_string_length,
    sanitize_string,
    check_dangerous_content,
    validate_file_path_safe,
    MAX_FILE_SIZE,
    ALLOWED_PDF_EXTENSIONS,
    ALLOWED_PDF_MIMES,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIMES,
)
from app.db import models
from app.db.session import SessionLocal
from app.ingestion import progress as ingestion_progress
from app.ingestion.custom_crawler_adapter import discover_links, scrape_page
from app.ingestion.pdf_loader import ingest_pdf
from app.ingestion.text_loader import ingest_text_file
from app.ingestion.types import DocumentChunk
from app.vectorstore.pinecone_store import delete_all, delete_by_path, upsert_chunks

# Setup admin logging
setup_admin_logging()
logger.info("Admin panel logging initialized")

router = APIRouter(prefix="/admin", tags=["Admin"], include_in_schema=False)
templates = Jinja2Templates(directory=str(os.path.join(os.path.dirname(__file__), "templates")))

KB_ROOT = Path("knowledge_base")
KB_ROOT.mkdir(exist_ok=True)
SCRAPED_ROOT = Path("scraped")
SCRAPED_ROOT.mkdir(exist_ok=True)
FOLDER_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


def sanitize_folder(value: str) -> str:
    """Sanitize folder name using maximum security validation."""
    try:
        return validate_folder_name(value)
    except ValidationError as e:
        logger.warning(f"Invalid folder name '{value}': {e}")
        return "general"


def slugify_value(value: str) -> str:
    cleaned = FOLDER_PATTERN.sub("-", value.strip()).strip("-").lower()
    return cleaned or "document"


def build_filename(display_name: str, suffix: str, folder_path: Path, *, current_path: Path | None = None) -> str:
    base = slugify_value(Path(display_name).stem)
    candidate = f"{base}{suffix}"
    counter = 1
    while (folder_path / candidate).exists() and (current_path is None or (folder_path / candidate) != current_path):
        candidate = f"{base}-{counter}{suffix}"
        counter += 1
    return candidate


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _process_pdf_ingestion(path_str: str, job_id: str, display_name: str) -> None:
    pdf_path = Path(path_str)
    ingestion_progress.update_job(job_id, message="Extracting PDF text")

    try:
        document = ingest_pdf(pdf_path)
    except Exception as exc:
        ingestion_progress.fail_job(job_id, message=f"Failed: {exc}")
        raise

    total_chunks = len(document.chunks)
    ingestion_progress.update_job(
        job_id,
        total_chunks=total_chunks,
        processed_chunks=0,
        message=f"Generating embeddings 0/{total_chunks} chunks",
    )

    def _on_embedding(processed: int, total: int) -> None:
        ingestion_progress.update_job(
            job_id,
            total_chunks=total,
            processed_chunks=processed,
            message=f"Generating embeddings {processed}/{total} chunks",
        )

    def _on_upload(processed: int, total: int) -> None:
        ingestion_progress.update_job(
            job_id,
            processed_chunks=processed,
            total_chunks=total,
            message=f"Uploading embeddings {processed}/{total} chunks",
        )

    try:
        upsert_chunks(
            document.chunks,
            embedding_callback=_on_embedding,
            progress_callback=_on_upload,
        )
    except Exception as exc:
        ingestion_progress.fail_job(job_id, message=f"Failed: {exc}")
        raise

    ingestion_progress.complete_job(
        job_id,
        message=f"Finished ingesting '{display_name}' ({total_chunks} chunks)",
    )


def _process_crawl_job(db_job_id: int, urls: list[str], tracker_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(models.CrawlJob, db_job_id)
        if not job:
            ingestion_progress.fail_job(tracker_id, message="Crawl job not found.")
            return

        ingestion_progress.update_job(tracker_id, message="Discovering links…")
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.message = "Starting crawl"
        db.add(job)
        db.commit()

        discovered_count = 0

        def _record_discovery(url: str, depth: int) -> None:
            nonlocal discovered_count
            discovered_count += 1

            existing = (
                db.query(models.CrawledUrl)
                .filter(models.CrawledUrl.job_id == job.id, models.CrawledUrl.url == url)
                .one_or_none()
            )
            if not existing:
                entry = models.CrawledUrl(
                    job_id=job.id,
                    url=url,
                    depth=depth,
                    status="pending",
                )
                db.add(entry)
                db.commit()

            job.total_discovered = discovered_count
            job.message = f"Discovered {discovered_count} URL(s)"
            db.add(job)
            db.commit()

            ingestion_progress.update_job(
                tracker_id,
                processed_chunks=discovered_count,
                total_chunks=None,
                message=f"Discovered {discovered_count} URL(s). Latest: {url}",
            )

        discover_links(urls, on_discovered=_record_discovery)

        if discovered_count == 0:
            ingestion_progress.complete_job(tracker_id, message="No URLs discovered.")
            job.status = "completed"
            job.message = "No URLs discovered."
            job.completed_at = datetime.utcnow()
            db.add(job)
            db.commit()
            return

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.message = f"Discovered {discovered_count} URL(s)"
        db.add(job)
        db.commit()

        ingestion_progress.complete_job(
            tracker_id,
            message=f"Crawl completed · {discovered_count} URL(s) found.",
        )
    finally:
        db.close()


def _process_scrape_job(db_job_id: int, tracker_id: str) -> None:
    logger.info(f"Starting scrape job {db_job_id} (tracker: {tracker_id})")
    db = SessionLocal()
    try:
        job = db.get(models.CrawlJob, db_job_id)
        if not job:
            logger.error(f"Scrape job {db_job_id} not found in database")
            ingestion_progress.fail_job(tracker_id, message="Crawl job not found.")
            return

        pending_urls = (
            db.query(models.CrawledUrl)
            .filter(
                models.CrawledUrl.job_id == job.id,
                models.CrawledUrl.status.in_(["pending", "failed"]),
            )
            .order_by(models.CrawledUrl.depth.asc(), models.CrawledUrl.id.asc())
            .all()
        )

        total_urls = len(pending_urls)
        logger.info(f"Scrape job {db_job_id}: Found {total_urls} URLs to scrape")
        
        if total_urls == 0:
            # Check if there are any URLs at all
            all_urls = db.query(models.CrawledUrl).filter(models.CrawledUrl.job_id == job.id).all()
            logger.warning(f"Scrape job {db_job_id}: No pending URLs found. Total URLs in job: {len(all_urls)}")
            for url_obj in all_urls[:5]:  # Log first 5 URLs
                logger.info(f"  URL status: {url_obj.url} -> {url_obj.status}")
            
            ingestion_progress.complete_job(
                tracker_id, message="No URLs available to scrape."
            )
            job.status = "scraped"
            job.message = "No URLs available to scrape."
            job.completed_at = datetime.utcnow()
            db.add(job)
            db.commit()
            return

        job.status = "scraping"
        job.message = "Scraping URLs"
        db.add(job)
        db.commit()

        ingestion_progress.update_job(
            tracker_id,
            total_chunks=total_urls,
            processed_chunks=0,
            message=f"Scraping 0/{total_urls} URLs",
        )

        aggregated_lines: list[str] = []
        ingestion_chunks: list[DocumentChunk] = []
        processed = 0
        success_count = 0

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        primary_host = urllib.parse.urlparse(job.root_url).netloc or job.root_url
        base_slug = slugify_value(primary_host)
        raw_filename = f"{base_slug}-{timestamp}.txt"
        raw_path = SCRAPED_ROOT / raw_filename

        folder_path = KB_ROOT / job.folder
        folder_path.mkdir(parents=True, exist_ok=True)
        kb_filename = build_filename(f"{base_slug}-{timestamp}", ".txt", folder_path)
        kb_path = folder_path / kb_filename

        for crawled in pending_urls:
            ingestion_progress.update_job(
                tracker_id,
                total_chunks=total_urls,
                processed_chunks=processed,
                message=f"Scraping {processed}/{total_urls} URLs · {crawled.url[:50]}...",
            )

            try:
                # Skip image URLs
                from app.ingestion.crawler import is_image_url
                if is_image_url(crawled.url):
                    crawled.status = "deleted"
                    crawled.notes = "Skipped: Image URL"
                    logger.info(f"Skipping image URL: {crawled.url}")
                    processed += 1
                    db.add(crawled)
                    db.commit()
                    continue
                
                logger.info(f"Attempting to scrape URL {processed+1}/{total_urls}: {crawled.url}")
                extracted_text, chunks = scrape_page(crawled.url)
                text_len = len(extracted_text) if extracted_text else 0
                logger.info(f"Scraped {crawled.url}: got {text_len} chars, {len(chunks)} chunks")
                
                if extracted_text and len(extracted_text.strip()) > 10:
                    aggregated_lines.append(
                        f"URL: {crawled.url}\n\n{extracted_text}\n\n{'-' * 80}\n"
                    )
                    for chunk in chunks:
                        ingestion_chunks.append(
                            chunk.with_additional_metadata(path=str(kb_path.resolve()))
                        )
                    crawled.status = "scraped"
                    crawled.notes = f"Scraped {len(chunks)} chunks ({len(extracted_text)} chars)"
                    success_count += 1
                    logger.info(f"Successfully scraped {crawled.url}: {len(chunks)} chunks")
                else:
                    text_len = len(extracted_text.strip()) if extracted_text else 0
                    crawled.status = "failed"
                    crawled.notes = f"No extractable text (got {text_len} chars, need 10+)"
                    logger.warning(f"Failed to scrape {crawled.url}: text too short ({text_len} chars)")
            except Exception as e:
                crawled.status = "failed"
                error_msg = str(e)[:200]
                crawled.notes = f"Error: {error_msg}"
                logger.error(f"Scraping error for {crawled.url}: {e}", exc_info=True)

            processed += 1
            db.add(crawled)
            db.commit()

            ingestion_progress.update_job(
                tracker_id,
                total_chunks=total_urls,
                processed_chunks=processed,
                message=f"Scraping {processed}/{total_urls} URLs ({success_count} successful)",
            )
            
            # Small delay between requests to be polite
            time.sleep(0.5)

        if success_count == 0:
            logger.error(f"Scrape job {db_job_id} failed: No pages could be scraped. Processed {processed} URLs, all failed.")
            # Log details about failed URLs
            failed_urls = db.query(models.CrawledUrl).filter(
                models.CrawledUrl.job_id == job.id,
                models.CrawledUrl.status == "failed"
            ).all()
            for failed_url in failed_urls[:10]:  # Log first 10 failures
                logger.error(f"  Failed URL: {failed_url.url} - {failed_url.notes}")
            
            job.status = "failed"
            job.message = "Scraping failed for all URLs."
            job.completed_at = datetime.utcnow()
            db.add(job)
            db.commit()
            ingestion_progress.fail_job(tracker_id, message="No pages could be scraped.")
            return

        combined_text = "".join(aggregated_lines)
        raw_path.write_text(combined_text, encoding="utf-8")
        kb_path.write_text(combined_text, encoding="utf-8")

        display_name = f"Crawl {primary_host} {timestamp}"
        knowledge_doc = models.KnowledgeDocument(
            folder=job.folder,
            filename=kb_filename,
            display_name=display_name,
            doc_type="crawl",
            source=job.root_url,
        )
        db.add(knowledge_doc)
        db.commit()

        job.knowledge_document_id = knowledge_doc.id
        job.scraped_file = str(raw_path.resolve())

        total_chunks = len(ingestion_chunks)
        if total_chunks == 0:
            ingestion_progress.update_job(
                tracker_id,
                total_chunks=0,
                processed_chunks=0,
                message="No textual chunks generated; skipping embedding.",
            )
        else:
            ingestion_progress.update_job(
                tracker_id,
                total_chunks=total_chunks,
                processed_chunks=0,
                message=f"Generating embeddings 0/{total_chunks} chunks",
            )

            def _on_embedding(processed_chunks: int, total: int) -> None:
                ingestion_progress.update_job(
                    tracker_id,
                    total_chunks=total,
                    processed_chunks=processed_chunks,
                    message=f"Generating embeddings {processed_chunks}/{total} chunks",
                )

            def _on_upload(processed_chunks: int, total: int) -> None:
                ingestion_progress.update_job(
                    tracker_id,
                    total_chunks=total,
                    processed_chunks=processed_chunks,
                    message=f"Uploading embeddings {processed_chunks}/{total} chunks",
                )

            if ingestion_chunks:
                upsert_chunks(
                    ingestion_chunks,
                    embedding_callback=_on_embedding,
                    progress_callback=_on_upload,
                )

        job.status = "scraped"
        job.completed_at = datetime.utcnow()
        job.message = f"Scraped {success_count}/{total_urls} URLs"
        db.add(job)
        db.commit()

        ingestion_progress.complete_job(
            tracker_id,
            message=f"Scraped {success_count}/{total_urls} URLs and ingested '{display_name}'.",
        )
    finally:
        db.close()


def _reingest_document(doc_id: int, old_path: str | None = None, job_id: str | None = None) -> None:
    db = SessionLocal()
    try:
        doc = db.get(models.KnowledgeDocument, doc_id)
        if not doc:
            return
        if old_path:
            try:
                delete_by_path(old_path)
            except Exception:
                pass

        path = (KB_ROOT / doc.folder / doc.filename).resolve()
        if not path.exists():
            return
        if doc.doc_type == "pdf":
            try:
                ingestion_progress.update_job(job_id, message="Extracting PDF text")
                document = ingest_pdf(path)
            except Exception as exc:
                ingestion_progress.fail_job(job_id, message=f"Failed: {exc}")
                raise
        else:
            text_doc = ingest_text_file(path)
            chunks = [chunk.with_additional_metadata(path=str(path)) for chunk in text_doc.chunks]
            document = text_doc

        if doc.doc_type != "pdf":
            ingestion_progress.update_job(job_id, message="Preparing text chunks")
            total_chunks = len(chunks)
        else:
            chunks = document.chunks
            total_chunks = len(chunks)

        ingestion_progress.update_job(
            job_id,
            total_chunks=total_chunks,
            processed_chunks=0,
            message=f"Generating embeddings 0/{total_chunks} chunks",
        )

        def _on_embedding(processed: int, total: int) -> None:
            ingestion_progress.update_job(
                job_id,
                processed_chunks=processed,
                total_chunks=total,
                message=f"Generating embeddings {processed}/{total} chunks",
            )

        def _on_upload(processed: int, total: int) -> None:
            ingestion_progress.update_job(
                job_id,
                processed_chunks=processed,
                total_chunks=total,
                message=f"Uploading embeddings {processed}/{total} chunks",
            )

        upsert_chunks(
            chunks,
            embedding_callback=_on_embedding,
            progress_callback=_on_upload,
        )
        ingestion_progress.complete_job(
            job_id,
            message=f"Re-ingested '{doc.display_name}' ({total_chunks} chunks)",
        )
    finally:
        db.close()


@router.get("/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    """Display login page with security checks."""
    from app.admin.security import generate_csrf_token, get_client_ip, check_rate_limit
    
    # If already logged in, redirect to dashboard
    if request.session.get("admin_authenticated"):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    
    # Check rate limiting
    ip_address = get_client_ip(request)
    rate_ok, rate_error = check_rate_limit(ip_address)
    if not rate_ok:
        error = f"Rate limit exceeded. {rate_error}"
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": error},
        )
    
    # Generate CSRF token for this session
    csrf_token = generate_csrf_token()
    request.session["csrf_token"] = csrf_token
    
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error, "csrf_token": csrf_token},
    )


@router.post("/login")
async def admin_login_post(request: Request, db: Session = Depends(get_db)):
    """Handle login form submission with enhanced security."""
    import secrets
    import os
    from app.admin.security import (
        get_client_ip,
        is_ip_locked_out,
        record_failed_login_attempt,
        record_successful_login,
        check_rate_limit,
        verify_csrf_token,
        hash_ip_for_logging
    )
    
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Check rate limiting
    rate_ok, rate_error = check_rate_limit(ip_address)
    if not rate_ok:
        logger.warning(f"[SECURITY] Rate limit exceeded for IP {hash_ip_for_logging(ip_address)}")
        return RedirectResponse(
            url="/admin/login?error=" + urllib.parse.quote_plus(f"Rate limit exceeded. {rate_error}"),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    # Check if IP is locked out
    is_locked, lockout_until = is_ip_locked_out(ip_address)
    if is_locked:
        remaining_minutes = int((lockout_until - datetime.now()).total_seconds() / 60) + 1
        logger.warning(f"[SECURITY] Locked out IP {hash_ip_for_logging(ip_address)} attempted login")
        record_failed_login_attempt(db, ip_address, "unknown", "locked_out")
        return RedirectResponse(
            url="/admin/login?error=" + urllib.parse.quote_plus(
                f"Too many failed attempts. IP address locked for {remaining_minutes} minutes."
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    form_data = await request.form()
    username = form_data.get("username", "").strip()
    password = form_data.get("password", "")
    csrf_token = form_data.get("csrf_token", "")
    
    # Verify CSRF token
    session_csrf = request.session.get("csrf_token")
    if not verify_csrf_token(session_csrf, csrf_token):
        logger.warning(f"[SECURITY] CSRF token mismatch for IP {hash_ip_for_logging(ip_address)}")
        record_failed_login_attempt(db, ip_address, username, "csrf_failure")
        return RedirectResponse(
            url="/admin/login?error=" + urllib.parse.quote_plus("Security token mismatch. Please refresh the page."),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_password:
        logger.error("[SECURITY] Admin password not configured")
        return RedirectResponse(
            url="/admin/login?error=" + urllib.parse.quote_plus("Admin password is not configured."),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    # Validate credentials with constant-time comparison
    username_match = secrets.compare_digest(username, admin_username)
    password_match = secrets.compare_digest(password, admin_password)
    
    if not (username_match and password_match):
        # Record failed attempt
        is_locked, lockout_until = record_failed_login_attempt(db, ip_address, username, "invalid_credentials")
        
        if is_locked:
            remaining_minutes = int((lockout_until - datetime.now()).total_seconds() / 60) + 1
            logger.warning(f"[SECURITY] IP {hash_ip_for_logging(ip_address)} locked out after multiple failed attempts")
            return RedirectResponse(
                url="/admin/login?error=" + urllib.parse.quote_plus(
                    f"Too many failed attempts. IP address locked for {remaining_minutes} minutes."
                ),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        
        # Log failed attempt
        logger.warning(f"[SECURITY] Failed login attempt from IP {hash_ip_for_logging(ip_address)}, username: {username[:3]}***")
        
        # Generic error message (don't reveal which field was wrong)
        return RedirectResponse(
            url="/admin/login?error=" + urllib.parse.quote_plus("Invalid username or password."),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    # Successful login
    record_successful_login(db, ip_address, username)
    
    # Generate new session ID for security (session rotation)
    # Clear old session data first
    old_session_id = request.session.get("_session_id")
    request.session.clear()
    
    # Force session regeneration by modifying session
    # Starlette will generate a new session ID when session data changes
    from app.admin.security import generate_csrf_token
    request.session["admin_authenticated"] = True
    request.session["admin_username"] = username
    request.session["login_time"] = datetime.now().isoformat()
    request.session["login_ip"] = hash_ip_for_logging(ip_address)  # Store hashed IP for logging
    request.session["csrf_token"] = generate_csrf_token()  # New CSRF token for this session
    request.session["_session_rotated"] = True  # Flag to indicate session was rotated
    
    logger.info(f"[SECURITY] Successful admin login from IP {hash_ip_for_logging(ip_address)}, username: {username}")
    
    # Redirect to dashboard
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def admin_logout(request: Request):
    """Handle logout."""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    from datetime import timedelta
    from sqlalchemy import func, case
    
    totals = {
        "users": db.query(models.User).count(),
        "sessions": db.query(models.ChatSession).count(),
        "messages": db.query(models.Message).count(),
    }

    recent_sessions_db: List[models.ChatSession] = (
        db.query(models.ChatSession)
        .options(selectinload(models.ChatSession.user), selectinload(models.ChatSession.messages))
        .order_by(models.ChatSession.started_at.desc())
        .limit(5)
        .all()
    )

    recent_sessions = [
        {
            "id": session.id,
            "started_at": session.started_at,
            "user": session.user,
            "message_count": len(session.messages),
        }
        for session in recent_sessions_db
    ]
    
    # Chart data: Sessions over last 7 days
    seven_days_ago = datetime.now() - timedelta(days=7)
    sessions_by_day = (
        db.query(
            func.date(models.ChatSession.started_at).label("date"),
            func.count(models.ChatSession.id).label("count")
        )
        .filter(models.ChatSession.started_at >= seven_days_ago)
        .group_by(func.date(models.ChatSession.started_at))
        .order_by(func.date(models.ChatSession.started_at))
        .all()
    )
    
    # Messages over last 7 days
    messages_by_day = (
        db.query(
            func.date(models.Message.timestamp).label("date"),
            func.count(models.Message.id).label("count")
        )
        .filter(models.Message.timestamp >= seven_days_ago)
        .group_by(func.date(models.Message.timestamp))
        .order_by(func.date(models.Message.timestamp))
        .all()
    )
    
    # User vs Bot messages
    user_messages = db.query(models.Message).filter(models.Message.is_user_message.is_(True)).count()
    bot_messages = db.query(models.Message).filter(models.Message.is_user_message.is_(False)).count()
    
    # Prepare chart data
    chart_data = {
        "sessions_by_day": {
            "labels": [s.date.strftime("%m/%d") if s.date else "" for s in sessions_by_day],
            "data": [s.count for s in sessions_by_day],
        },
        "messages_by_day": {
            "labels": [m.date.strftime("%m/%d") if m.date else "" for m in messages_by_day],
            "data": [m.count for m in messages_by_day],
        },
        "message_types": {
            "labels": ["User Messages", "Bot Messages"],
            "data": [user_messages, bot_messages],
        }
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "totals": totals,
            "recent_sessions": recent_sessions,
            "chart_data": chart_data,
        },
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})


@router.get("/sessions", response_class=HTMLResponse)
async def admin_sessions(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    sessions = (
        db.query(models.ChatSession)
        .options(selectinload(models.ChatSession.user), selectinload(models.ChatSession.messages))
        .order_by(models.ChatSession.started_at.desc())
        .all()
    )
    formatted = [
        {
            "id": session.id,
            "started_at": session.started_at,
            "user": session.user,
            "message_count": len(session.messages),
        }
        for session in sessions
    ]
    return templates.TemplateResponse("sessions.html", {"request": request, "sessions": formatted})


@router.get("/sessions/{session_id}", response_class=HTMLResponse)
async def admin_session_detail(
    session_id: int,
    request: Request,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    session = (
        db.query(models.ChatSession)
        .options(selectinload(models.ChatSession.user), selectinload(models.ChatSession.messages))
        .filter(models.ChatSession.id == session_id)
        .one_or_none()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    transcript = sorted(session.messages, key=lambda m: m.timestamp)

    return templates.TemplateResponse(
        "session_detail.html",
        {"request": request, "session": session, "transcript": transcript},
    )


@router.get("/sessions/{session_id}/download")
async def download_session_transcript(
    session_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Download chat session transcript as JSON."""
    import json
    
    session = (
        db.query(models.ChatSession)
        .options(selectinload(models.ChatSession.user), selectinload(models.ChatSession.messages))
        .filter(models.ChatSession.id == session_id)
        .one_or_none()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    # Sort messages by timestamp
    messages = sorted(session.messages, key=lambda m: m.timestamp)
    
    # Build JSON structure
    transcript_data = {
        "session_id": session.id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "user": {
            "id": session.user.id if session.user else None,
            "name": session.user.name if session.user else None,
            "email": session.user.email if session.user else None,
            "phone": session.user.phone if session.user else None,
            "created_at": session.user.created_at.isoformat() if session.user and session.user.created_at else None,
        } if session.user else None,
        "message_count": len(messages),
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "is_user_message": msg.is_user_message,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            }
            for msg in messages
        ],
        "exported_at": datetime.now().isoformat(),
    }
    
    # Convert to JSON string
    json_str = json.dumps(transcript_data, indent=2, ensure_ascii=False)
    
    # Generate filename
    filename = f"chat_session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/ingestion", response_class=HTMLResponse)
async def admin_ingestion(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    logger.info("Admin ingestion page accessed")
    def build_status(prefix: str):
        flag = request.query_params.get(f"{prefix}_status")
        if not flag:
            return None
        message = request.query_params.get(f"{prefix}_message", "Completed")
        return {"success": flag == "success", "message": message}

    widget_src = os.getenv("WIDGET_IFRAME_SRC", "http://localhost:8000/embed")
    widget_iframe_template = textwrap.dedent(
        """
        <div id="askcache-chat-window" style="max-width: 420px; margin: 40px auto; border-radius: 24px; box-shadow: 0 24px 55px rgba(15, 23, 42, 0.35); overflow: hidden; background: #ffffff;">
          <div style="background: linear-gradient(135deg, #4338ca 0%, #6366f1 100%); color: #ffffff; padding: 20px 24px; font-size: 18px; font-weight: 600; display:flex; align-items:center; gap:12px;">
            <span style="display:inline-flex; width: 40px; height: 40px; border-radius: 12px; background: rgba(255,255,255,0.15); align-items:center; justify-content:center;">💬</span>
            <span>AskCache.ai Assistant</span>
          </div>
          <iframe src="$src" title="AskCache.ai Assistant" style="display:block; width: 100%; height: 640px; border: none; background: #f8fafc;"></iframe>
        </div>
        """
    ).strip()
    widget_iframe_code = Template(widget_iframe_template).substitute(src=widget_src)

    widget_popup_template = textwrap.dedent(
        """
        <script>
        (function() {
          if (document.getElementById('askcache-launcher')) return;
          const launcher = document.createElement('div');
          launcher.id = 'askcache-launcher';
          launcher.style.position = 'fixed';
          launcher.style.bottom = '24px';
          launcher.style.right = '24px';
          launcher.style.zIndex = '9999';

          const button = document.createElement('button');
          button.textContent = 'Chat with AskCache.ai';
          button.style.cssText = [
            'display:flex',
            'align-items:center',
            'gap:8px',
            'padding:12px 20px',
            'border-radius:999px',
            'background:#4338ca',
            'color:#fff',
            'border:0',
            'font-family:inherit',
            'font-size:14px',
            'cursor:pointer',
            'box-shadow:0 15px 35px rgba(67,56,202,0.35)',
            'font-weight:600'
          ].join(';') + ';';

          const frame = document.createElement('iframe');
          frame.src = "$src";
          frame.width = '420';
          frame.height = '640';
          frame.title = 'AskCache.ai Assistant';
          frame.style.cssText = [
            'display:none',
            'margin-top:16px',
            'border:none',
            'border-radius:24px',
            'box-shadow:0 20px 45px rgba(15,23,42,0.35)'
          ].join(';') + ';';

          button.addEventListener('click', function() {
            const visible = frame.style.display === 'block';
            frame.style.display = visible ? 'none' : 'block';
            button.textContent = visible ? 'Chat with Cache Digitech' : 'Close chat';
          });

          launcher.appendChild(button);
          launcher.appendChild(frame);
          document.body.appendChild(launcher);
        })();
        </script>
        """
    ).strip()
    widget_popup_code = Template(widget_popup_template).substitute(src=widget_src)

    docs = (
        db.query(models.KnowledgeDocument)
        .order_by(models.KnowledgeDocument.folder, models.KnowledgeDocument.created_at.desc())
        .all()
    )
    documents_by_folder: dict[str, list[models.KnowledgeDocument]] = {}
    for doc in docs:
        documents_by_folder.setdefault(doc.folder, []).append(doc)

    latest_crawl_job = (
        db.query(models.CrawlJob)
        .order_by(models.CrawlJob.created_at.desc())
        .first()
    )

    crawl_job_id_param = request.query_params.get("crawl_job_id")
    crawl_job_id_value: int | None = None
    if crawl_job_id_param:
        try:
            crawl_job_id_value = int(crawl_job_id_param)
        except ValueError:
            crawl_job_id_value = None

    selected_crawl_job = None
    if crawl_job_id_value:
        selected_crawl_job = db.get(models.CrawlJob, crawl_job_id_value)
    if not selected_crawl_job and latest_crawl_job:
        selected_crawl_job = latest_crawl_job
        crawl_job_id_value = latest_crawl_job.id

    crawl_job_info = None
    if selected_crawl_job:
        crawl_job_info = {
            "id": selected_crawl_job.id,
            "status": selected_crawl_job.status,
            "message": selected_crawl_job.message,
            "total_discovered": selected_crawl_job.total_discovered,
            "root_url": selected_crawl_job.root_url,
        }

    context = {
        "request": request,
        "pdf_status": build_status("pdf"),
        "crawl_status": build_status("crawl"),
        "doc_status": build_status("doc"),
        "widget_src": widget_src,
        "widget_iframe_code": widget_iframe_code,
        "widget_popup_code": widget_popup_code,
        "documents_by_folder": documents_by_folder,
        "progress_jobs": ingestion_progress.list_jobs(limit=25),
        "highlight_job": request.query_params.get("job"),
        "crawl_job": crawl_job_info,
        "crawl_job_id": crawl_job_id_value,
    }
    return templates.TemplateResponse("ingestion.html", context)


@router.get("/ingestion/progress")
async def ingestion_progress_status(_: str = Depends(require_admin)) -> dict[str, list[dict[str, object]]]:
    jobs = ingestion_progress.list_jobs(limit=25)
    return {"jobs": jobs}


@router.get("/logs", name="admin_logs")
async def get_logs(
    level: str | None = None,
    limit: int = 500,
    _: str = Depends(require_admin),
) -> dict[str, list[dict[str, str]]]:
    """Get recent logs for admin panel."""
    logger.info(f"Logs endpoint accessed (level={level}, limit={limit})")
    handler = get_admin_log_handler()
    logs = handler.get_logs(level=level, limit=limit)
    logger.info(f"Serving {len(logs)} logs")
    return {"logs": logs}


@router.post("/logs/clear")
async def clear_logs(_: str = Depends(require_admin)) -> dict[str, str]:
    """Clear all logs."""
    handler = get_admin_log_handler()
    handler.clear()
    return {"status": "cleared"}


@router.post("/ingestion/pdf")
async def upload_pdf(
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(...),
    folder: str = Form("general"),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Upload PDF with maximum security validation."""
    try:
        # Validate filename
        if not pdf.filename:
            raise ValidationError("Please provide a PDF file.")
        
        # Validate folder name
        folder_name = validate_folder_name(folder)
        folder_path = KB_ROOT / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        
        # Read file content
        contents = await pdf.read()
        
        # Validate file upload (filename, size, type, MIME)
        safe_filename, mime_type = validate_file_upload(
            contents,
            pdf.filename,
            max_size=MAX_FILE_SIZE,
            allowed_extensions=ALLOWED_PDF_EXTENSIONS,
            allowed_mimes=ALLOWED_PDF_MIMES
        )
        
        # Validate path is safe
        original_name = Path(safe_filename).name
        suffix = Path(original_name).suffix or ".pdf"
        stored_filename = build_filename(original_name, suffix, folder_path)
        destination = validate_file_path_safe(
            str(folder_path / stored_filename),
            KB_ROOT
        )
        
        # Write file
        destination.write_bytes(contents)
        
    except ValidationError as e:
        logger.warning(f"[SECURITY] PDF upload validation failed: {e}")
        return RedirectResponse(
            url="/admin/ingestion?pdf_status=error&pdf_message="
            + urllib.parse.quote_plus(str(e)),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        logger.error(f"Error uploading PDF: {e}")
        return RedirectResponse(
            url="/admin/ingestion?pdf_status=error&pdf_message="
            + urllib.parse.quote_plus("Error uploading file. Please try again."),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    record = models.KnowledgeDocument(
        folder=folder_name,
        filename=stored_filename,
        display_name=original_name,
        doc_type="pdf",
        source=str(destination.resolve()),
    )
    db.add(record)
    db.commit()

    job_id = uuid.uuid4().hex
    ingestion_progress.start_job(
        job_id,
        label=f"Ingest PDF · {original_name}",
        message="Queued for ingestion",
    )
    background_tasks.add_task(
        _process_pdf_ingestion,
        str(destination.resolve()),
        job_id,
        original_name,
    )

    return RedirectResponse(
        url="/admin/ingestion?pdf_status=success&pdf_message="
        + urllib.parse.quote_plus(f"Uploaded '{original_name}'")
        + f"&job={job_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/ingestion/crawl")
async def start_crawl(
    background_tasks: BackgroundTasks,
    urls: str = Form(...),
    folder: str = Form("general"),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Start crawl job with maximum security validation."""
    try:
        # Validate URLs input
        urls = validate_string_length(urls, max_length=50000)  # Allow multiple URLs
        urls = sanitize_string(urls)
        
        url_list = [line.strip() for line in urls.splitlines() if line.strip()]
        if not url_list:
            raise ValidationError("Provide at least one URL.")
        
        # Validate each URL
        validated_urls = []
        for url in url_list[:100]:  # Limit to 100 URLs max
            validated_url = validate_url(url)
            validated_urls.append(validated_url)
        
        if not validated_urls:
            raise ValidationError("No valid URLs provided.")
        
        # Validate folder name
        folder_name = validate_folder_name(folder)
        
        # Check for dangerous content
        check_dangerous_content(urls)
        
    except ValidationError as e:
        logger.warning(f"[SECURITY] Crawl validation failed: {e}")
        return RedirectResponse(
            url="/admin/ingestion?crawl_status=error&crawl_message="
            + urllib.parse.quote_plus(str(e)),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    job_record = models.CrawlJob(
        root_url=validated_urls[0],
        folder=folder_name,
        status="pending",
        message="Queued for crawling",
    )
    db.add(job_record)
    db.commit()
    db.refresh(job_record)

    tracker_id = uuid.uuid4().hex
    ingestion_progress.start_job(
        tracker_id,
        label=f"Crawl Links · {folder_name}",
        message="Queued for crawling",
    )
    background_tasks.add_task(_process_crawl_job, job_record.id, url_list, tracker_id)

    return RedirectResponse(
        url="/admin/ingestion?crawl_status=success&crawl_message="
        + urllib.parse.quote_plus("Crawler started in the background.")
        + f"&job={tracker_id}&crawl_job_id={job_record.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/crawl-jobs/{job_id}/links/{link_id}/delete")
async def delete_crawled_link(
    job_id: int,
    link_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    link = (
        db.query(models.CrawledUrl)
        .filter(models.CrawledUrl.job_id == job_id, models.CrawledUrl.id == link_id)
        .one_or_none()
    )
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    link.status = "deleted"
    link.notes = "Manually removed"
    db.add(link)
    db.commit()

    return RedirectResponse(
        url=f"/admin/ingestion?crawl_status=success&crawl_message={urllib.parse.quote_plus('Link deleted.')}&crawl_job_id={job_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/crawl-jobs/{job_id}/scrape")
async def scrape_crawl_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = db.get(models.CrawlJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found")

    if job.status not in {"completed", "scraped"}:
        # Allow restarting after completion but not while running
        if job.status in {"running", "scraping"}:
            return RedirectResponse(
                url=f"/admin/ingestion?crawl_status=error&crawl_message={urllib.parse.quote_plus('Crawl still in progress.')}&crawl_job_id={job_id}",
                status_code=status.HTTP_303_SEE_OTHER,
            )

    tracker_id = uuid.uuid4().hex
    ingestion_progress.start_job(
        tracker_id,
        label=f"Scrape URLs · {job.folder}",
        message="Queued for scraping",
    )
    background_tasks.add_task(_process_scrape_job, job.id, tracker_id)

    return RedirectResponse(
        url=f"/admin/ingestion?crawl_status=success&crawl_message={urllib.parse.quote_plus('Scraping started.')}&job={tracker_id}&crawl_job_id={job_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/crawl-jobs/{job_id}/data")
async def crawl_job_data(
    job_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    job = (
        db.query(models.CrawlJob)
        .options(selectinload(models.CrawlJob.urls))
        .filter(models.CrawlJob.id == job_id)
        .one_or_none()
    )
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    urls = sorted(job.urls, key=lambda item: (item.depth, item.id))
    payload = {
        "job": {
            "id": job.id,
            "root_url": job.root_url,
            "folder": job.folder,
            "status": job.status,
            "message": job.message,
            "total_discovered": job.total_discovered,
            "scraped_file": job.scraped_file,
            "knowledge_document_id": job.knowledge_document_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "urls": [
            {
                "id": link.id,
                "url": link.url,
                "depth": link.depth,
                "status": link.status,
                "notes": link.notes,
                "discovered_at": link.discovered_at.isoformat() if link.discovered_at else None,
            }
            for link in urls
        ],
    }
    return payload


@router.post("/knowledge/{doc_id}/rename")
async def rename_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    new_display_name: str = Form(...),
    new_folder: str = Form(...),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Rename document with maximum security validation."""
    try:
        # Validate doc_id
        if doc_id < 1:
            raise ValidationError("Invalid document ID")
        
        document = db.get(models.KnowledgeDocument, doc_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
        # Validate display name
        cleaned_name = validate_display_name(new_display_name) if new_display_name.strip() else document.display_name
        
        # Validate folder name
        folder_name = validate_folder_name(new_folder)
        
        # Check for dangerous content
        check_dangerous_content(cleaned_name)
        
    except ValidationError as e:
        logger.warning(f"[SECURITY] Document rename validation failed: {e}")
        return RedirectResponse(
            url="/admin/ingestion?doc_status=error&doc_message="
            + urllib.parse.quote_plus(str(e)),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    dest_dir = KB_ROOT / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    old_path = (KB_ROOT / document.folder / document.filename).resolve()
    suffix = Path(document.filename).suffix or (".pdf" if document.doc_type == "pdf" else ".txt")
    current_path = old_path if folder_name == document.folder else None
    stored_filename = build_filename(cleaned_name, suffix, dest_dir, current_path=current_path)
    new_path = dest_dir / stored_filename

    if old_path.exists() and old_path != new_path:
        shutil.move(str(old_path), str(new_path))
    elif folder_name != document.folder and old_path.exists():
        shutil.move(str(old_path), str(new_path))

    document.folder = folder_name
    document.filename = stored_filename
    document.display_name = cleaned_name
    document.source = str(new_path.resolve())
    db.add(document)
    db.commit()

    job_id = uuid.uuid4().hex
    ingestion_progress.start_job(
        job_id,
        label=f"Reindex · {document.display_name}",
        message="Queued for re-ingestion",
    )
    background_tasks.add_task(_reingest_document, document.id, str(old_path), job_id)

    return RedirectResponse(
        url="/admin/ingestion?doc_status=success&doc_message="
        + urllib.parse.quote_plus("Document updated.")
        + f"&job={job_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/knowledge/{doc_id}/delete")
async def delete_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    document = db.get(models.KnowledgeDocument, doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    path = (KB_ROOT / document.folder / document.filename).resolve()
    if path.exists():
        path.unlink()
        parent = path.parent
        try:
            if parent != KB_ROOT and not any(parent.iterdir()):
                parent.rmdir()
        except Exception:
            pass

    db.delete(document)
    db.commit()

    background_tasks.add_task(delete_by_path, str(path))

    return RedirectResponse(
        url="/admin/ingestion?doc_status=success&doc_message="
        + urllib.parse.quote_plus("Document deleted."),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/knowledge/delete-all")
async def delete_all_knowledge(
    confirm: str = Form(...),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete all knowledge base documents with maximum security validation."""
    try:
        # Validate confirmation text
        if not validate_confirm_text(confirm, "DELETE ALL"):
            raise ValidationError("Confirmation text must be exactly 'DELETE ALL'")
    except ValidationError as e:
        logger.warning(f"[SECURITY] Delete all validation failed: {e}")
        return RedirectResponse(
            url="/admin/ingestion?doc_status=error&doc_message="
            + urllib.parse.quote_plus(str(e)),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    
    logger.warning("Starting complete knowledge base deletion...")
    
    # 1. Delete all knowledge documents from database
    documents = db.query(models.KnowledgeDocument).all()
    doc_count = len(documents)
    
    # Delete local files
    deleted_files = 0
    for doc in documents:
        try:
            path = KB_ROOT / doc.folder / doc.filename
            if path.exists():
                path.unlink()
                deleted_files += 1
            # Also delete scraped files if they exist
            if doc.source and Path(doc.source).exists():
                try:
                    Path(doc.source).unlink()
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error deleting file for {doc.filename}: {e}")
    
    # Delete from database
    db.query(models.KnowledgeDocument).delete()
    
    # 2. Delete all crawl jobs and URLs
    crawl_jobs = db.query(models.CrawlJob).all()
    crawl_count = len(crawl_jobs)
    db.query(models.CrawledUrl).delete()
    db.query(models.CrawlJob).delete()
    
    # 3. Delete all vectors from Pinecone
    try:
        vectors_deleted = delete_all()
        logger.info(f"Deleted {vectors_deleted} vectors from Pinecone")
    except Exception as e:
        logger.error(f"Error deleting from Pinecone: {e}")
        vectors_deleted = 0
    
    # 4. Clean up empty folders
    try:
        for folder in KB_ROOT.iterdir():
            if folder.is_dir():
                try:
                    if not any(folder.iterdir()):
                        folder.rmdir()
                except Exception:
                    pass
    except Exception:
        pass
    
    # Clean up scraped folder
    try:
        for file in SCRAPED_ROOT.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                except Exception:
                    pass
    except Exception:
        pass
    
    db.commit()
    
    message = f"Deleted {doc_count} documents ({deleted_files} files), {crawl_count} crawl jobs, and {vectors_deleted} vectors from Pinecone."
    logger.info(message)
    
    return RedirectResponse(
        url="/admin/ingestion?doc_status=success&doc_message="
        + urllib.parse.quote_plus(message),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/bot-ui", response_class=HTMLResponse)
async def bot_ui_settings(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    """Display BOT UI customization page."""
    # Get or create settings (singleton - only one settings record)
    settings = db.query(models.BotUISettings).first()
    if not settings:
        # Create default settings
        settings = models.BotUISettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    status_msg = None
    status_type = request.query_params.get("status")
    if status_type:
        message = request.query_params.get("message", "Settings saved.")
        status_msg = {"success": status_type == "success", "message": message}
    
    return templates.TemplateResponse(
        "bot_ui.html",
        {"request": request, "settings": settings, "status": status_msg},
    )


@router.post("/bot-ui/save")
async def save_bot_ui_settings(
    request: Request,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save BOT UI settings."""
    form_data = await request.form()
    
    # Get or create settings
    settings = db.query(models.BotUISettings).first()
    if not settings:
        settings = models.BotUISettings()
        db.add(settings)
    
    # Handle header image upload
    # In Starlette/FastAPI, files from multipart forms are UploadFile objects in form_data
    header_image_file = form_data.get("header_image")
    
    # Debug: log what we received
    logger.info(f"Form data keys: {list(form_data.keys())}")
    if header_image_file:
        logger.info(f"Header image file received: type={type(header_image_file)}, filename={getattr(header_image_file, 'filename', 'N/A')}, hasattr filename={hasattr(header_image_file, 'filename')}")
        # Check if it's actually an UploadFile-like object
        if hasattr(header_image_file, 'read') and hasattr(header_image_file, 'filename'):
            logger.info(f"File appears to be UploadFile-like: filename={header_image_file.filename}")
    else:
        logger.info("No header_image file found in form_data")
    
    # Check if file was uploaded (must be UploadFile with a filename)
    file_uploaded = False
    if header_image_file:
        # Check if it's an UploadFile instance or has the necessary attributes
        if isinstance(header_image_file, UploadFile):
            if header_image_file.filename and header_image_file.filename.strip():
                file_uploaded = True
        elif hasattr(header_image_file, 'filename') and hasattr(header_image_file, 'read'):
            # Might be a Starlette UploadFile but not recognized as FastAPI UploadFile
            filename = getattr(header_image_file, 'filename', '')
            if filename and filename.strip():
                file_uploaded = True
                logger.info(f"File detected via attributes: {filename}")
    
    if file_uploaded:
        # Create uploads directory if it doesn't exist
        uploads_dir = Path("uploads/header_images")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Get filename
        filename = header_image_file.filename if isinstance(header_image_file, UploadFile) else getattr(header_image_file, 'filename', '')
        
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            return RedirectResponse(
                url="/admin/bot-ui?status=error&message=" + urllib.parse.quote_plus("Invalid image format. Please upload JPG, PNG, GIF, WebP, or SVG."),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        
        import uuid
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = uploads_dir / unique_filename
        
        # Save file
        try:
            # Read file content
            if hasattr(header_image_file, 'read'):
                content = await header_image_file.read()
            else:
                # Fallback: try to read as bytes
                content = await header_image_file.read() if callable(getattr(header_image_file, 'read', None)) else b''
            
            if not content:
                raise ValueError("File content is empty")
            
            file_path.write_bytes(content)
            
            # Generate URL (relative to server)
            settings.header_image_url = f"/admin/uploads/header_images/{unique_filename}"
            logger.info(f"Header image uploaded successfully: {unique_filename} ({len(content)} bytes)")
        except Exception as e:
            logger.error(f"Error saving header image: {e}", exc_info=True)
            return RedirectResponse(
                url="/admin/bot-ui?status=error&message=" + urllib.parse.quote_plus(f"Failed to upload image: {str(e)}"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
    elif form_data.get("header_image_url"):
        # Use provided URL (only if no file was uploaded)
        url_value = form_data.get("header_image_url", "").strip()
        if url_value:
            settings.header_image_url = url_value
        # Don't clear if empty - keep existing value unless explicitly removed
    elif form_data.get("remove_header_image") == "true":
        # Remove header image
        if settings.header_image_url and settings.header_image_url.startswith("/admin/uploads/"):
            # Delete file if it's an uploaded file
            try:
                file_path = Path(settings.header_image_url.lstrip("/admin/"))
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete old header image: {e}")
        settings.header_image_url = None
    
    # Update basic settings
    settings.bot_name = form_data.get("bot_name", settings.bot_name)
    settings.bot_icon_url = form_data.get("bot_icon_url") or None
    settings.welcome_message = form_data.get("welcome_message") or None
    
    # Update colors
    settings.primary_color = form_data.get("primary_color", settings.primary_color)
    settings.secondary_color = form_data.get("secondary_color", settings.secondary_color)
    settings.background_color = form_data.get("background_color", settings.background_color)
    settings.text_color = form_data.get("text_color", settings.text_color)
    settings.user_message_bg = form_data.get("user_message_bg", settings.user_message_bg)
    settings.user_message_text = form_data.get("user_message_text", settings.user_message_text)
    settings.bot_message_bg = form_data.get("bot_message_bg", settings.bot_message_bg)
    settings.bot_message_text = form_data.get("bot_message_text", settings.bot_message_text)
    settings.link_color = form_data.get("link_color", settings.link_color)
    
    # Update widget settings
    settings.widget_position = form_data.get("widget_position", settings.widget_position)
    settings.widget_size = form_data.get("widget_size", settings.widget_size)
    settings.show_branding = form_data.get("show_branding") == "on"
    
    # Update advanced settings
    settings.custom_css = form_data.get("custom_css") or None
    
    # Update full-screen UI custom settings (stored in JSON)
    custom_settings = settings.custom_settings or {}
    
    # Header settings
    custom_settings["header_bg_color"] = form_data.get("header_bg_color", "#ffffff")
    custom_settings["header_text_color"] = form_data.get("header_text_color", "#1e293b")
    custom_settings["header_border_color"] = form_data.get("header_border_color", "#e2e8f0")
    custom_settings["header_height"] = form_data.get("header_height", "64")
    
    # Input bar settings
    custom_settings["input_bg_color"] = form_data.get("input_bg_color", "#ffffff")
    custom_settings["input_border_color"] = form_data.get("input_border_color", "#d1d5db")
    custom_settings["input_text_color"] = form_data.get("input_text_color", "#1e293b")
    custom_settings["input_placeholder_color"] = form_data.get("input_placeholder_color", "#9ca3af")
    custom_settings["input_border_radius"] = form_data.get("input_border_radius", "16")
    custom_settings["input_height"] = form_data.get("input_height", "52")
    custom_settings["input_padding"] = form_data.get("input_padding", "12")
    
    # Sidebar settings
    custom_settings["sidebar_bg_color"] = form_data.get("sidebar_bg_color", "#f9fafb")
    custom_settings["sidebar_text_color"] = form_data.get("sidebar_text_color", "#1e293b")
    custom_settings["sidebar_border_color"] = form_data.get("sidebar_border_color", "#e2e8f0")
    custom_settings["sidebar_width"] = form_data.get("sidebar_width", "280")
    custom_settings["sidebar_chat_hover_bg"] = form_data.get("sidebar_chat_hover_bg", "#f3f4f6")
    custom_settings["sidebar_chat_active_bg"] = form_data.get("sidebar_chat_active_bg", "#e0e7ff")
    
    # Message bubble settings
    custom_settings["message_border_radius"] = form_data.get("message_border_radius", "16")
    custom_settings["message_padding"] = form_data.get("message_padding", "12")
    custom_settings["message_gap"] = form_data.get("message_gap", "24")
    custom_settings["message_max_width"] = form_data.get("message_max_width", "85")
    custom_settings["message_shadow"] = form_data.get("message_shadow", "none")
    
    # Typography settings
    custom_settings["font_family"] = form_data.get("font_family", "system")
    custom_settings["font_size_base"] = form_data.get("font_size_base", "16")
    custom_settings["font_size_small"] = form_data.get("font_size_small", "14")
    custom_settings["font_weight_normal"] = form_data.get("font_weight_normal", "400")
    
    # Button settings
    custom_settings["button_border_radius"] = form_data.get("button_border_radius", "8")
    custom_settings["send_button_size"] = form_data.get("send_button_size", "52")
    
    settings.custom_settings = custom_settings
    
    db.add(settings)
    db.commit()
    
    logger.info("BOT UI settings updated")
    
    return RedirectResponse(
        url="/admin/bot-ui?status=success&message=" + urllib.parse.quote_plus("Settings saved successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/uploads/header_images/{filename}")
async def serve_header_image(filename: str, request: Request):
    """Serve uploaded header images."""
    file_path = Path("uploads/header_images") / filename
    
    # Security: ensure file is within uploads directory
    try:
        file_path.resolve().relative_to(Path("uploads/header_images").resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if file_path.exists() and file_path.is_file():
        from fastapi.responses import FileResponse
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="Image not found")


@router.get("/bot-ui/api/settings")
async def get_bot_ui_settings_api(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    """Get BOT UI settings as JSON for frontend widget."""
    settings = db.query(models.BotUISettings).first()
    
    # Get base URL for uploaded images
    if request:
        base_url = f"{request.url.scheme}://{request.url.netloc}"
    else:
        base_url = ""
    
    from datetime import datetime
    
    if not settings:
        # Return defaults
        default_settings = models.BotUISettings()
        data = {
            "bot_name": default_settings.bot_name,
            "bot_icon_url": default_settings.bot_icon_url,
            "header_image_url": default_settings.header_image_url,
            "welcome_message": default_settings.welcome_message,
            "primary_color": default_settings.primary_color,
            "secondary_color": default_settings.secondary_color,
            "background_color": default_settings.background_color,
            "text_color": default_settings.text_color,
            "user_message_bg": default_settings.user_message_bg,
            "user_message_text": default_settings.user_message_text,
            "bot_message_bg": default_settings.bot_message_bg,
            "bot_message_text": default_settings.bot_message_text,
            "link_color": default_settings.link_color,
            "widget_position": default_settings.widget_position,
            "widget_size": default_settings.widget_size,
            "show_branding": default_settings.show_branding,
            "custom_css": default_settings.custom_css,
            "custom_settings": default_settings.custom_settings or {},
            "settings_updated_at": datetime.now().isoformat(),  # Timestamp for change detection
        }
    else:
        # Convert relative URLs to absolute URLs
        header_image_url = settings.header_image_url
        if header_image_url:
            if header_image_url.startswith("/admin/uploads/") or header_image_url.startswith("/uploads/"):
                header_image_url = f"{base_url}{header_image_url}"
            elif not header_image_url.startswith("http"):
                # If it's a relative path without leading slash, add it
                header_image_url = f"{base_url}/{header_image_url.lstrip('/')}"
        
        bot_icon_url = settings.bot_icon_url
        if bot_icon_url:
            if bot_icon_url.startswith("/admin/uploads/") or bot_icon_url.startswith("/uploads/"):
                bot_icon_url = f"{base_url}{bot_icon_url}"
            elif not bot_icon_url.startswith("http"):
                bot_icon_url = f"{base_url}/{bot_icon_url.lstrip('/')}"
        
        from datetime import datetime
        data = {
            "bot_name": settings.bot_name,
            "bot_icon_url": bot_icon_url,
            "header_image_url": header_image_url,
            "welcome_message": settings.welcome_message,
            "primary_color": settings.primary_color,
            "secondary_color": settings.secondary_color,
            "background_color": settings.background_color,
            "text_color": settings.text_color,
            "user_message_bg": settings.user_message_bg,
            "user_message_text": settings.user_message_text,
            "bot_message_bg": settings.bot_message_bg,
            "bot_message_text": settings.bot_message_text,
            "link_color": settings.link_color,
            "widget_position": settings.widget_position,
            "widget_size": settings.widget_size,
            "show_branding": settings.show_branding,
            "custom_css": settings.custom_css,
            "custom_settings": settings.custom_settings or {},
            "settings_updated_at": settings.updated_at.isoformat() if settings.updated_at else datetime.now().isoformat(),  # Timestamp for change detection
        }
    
    # Return JSON response with cache-busting headers
    return JSONResponse(
        content=data,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@router.get("/settings", response_class=HTMLResponse)
async def app_settings(request: Request, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    """Display app settings page (API URL configuration)."""
    # Get or create settings (singleton - only one settings record)
    settings = db.query(models.AppSettings).first()
    if not settings:
        # Create default settings
        settings = models.AppSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    status_msg = None
    status_type = request.query_params.get("status")
    if status_type:
        message = request.query_params.get("message", "Settings saved.")
        status_msg = {"success": status_type == "success", "message": message}
    
    return templates.TemplateResponse(
        "app_settings.html",
        {"request": request, "settings": settings, "status": status_msg},
    )


@router.post("/settings/api-url")
async def save_api_url(
    request: Request,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save API base URL setting."""
    form_data = await request.form()
    
    # Get or create settings
    settings = db.query(models.AppSettings).first()
    if not settings:
        settings = models.AppSettings()
        db.add(settings)
    
    api_url = form_data.get("api_base_url", "").strip()
    auto_detect = form_data.get("auto_detect_api_url") == "on"
    
    # Validate URL format if provided
    if api_url and not auto_detect:
        if not (api_url.startswith("http://") or api_url.startswith("https://")):
            return RedirectResponse(
                url="/admin/settings?status=error&message=" + urllib.parse.quote_plus("URL must start with http:// or https://"),
                status_code=status.HTTP_303_SEE_OTHER,
            )
    
    settings.api_base_url = api_url if not auto_detect else None
    settings.auto_detect_api_url = auto_detect
    
    db.add(settings)
    db.commit()
    
    logger.info(f"API URL settings updated: auto_detect={auto_detect}, url={api_url if not auto_detect else 'auto'}")
    
    return RedirectResponse(
        url="/admin/settings?status=success&message=" + urllib.parse.quote_plus("API URL settings saved successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/settings/instructions")
async def save_custom_instructions(
    request: Request,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Save custom chatbot instructions."""
    form_data = await request.form()
    
    # Get or create settings
    settings = db.query(models.AppSettings).first()
    if not settings:
        settings = models.AppSettings()
        db.add(settings)
    
    custom_instructions = form_data.get("custom_instructions", "").strip()
    settings.custom_instructions = custom_instructions if custom_instructions else None
    
    db.add(settings)
    db.commit()
    
    logger.info("Custom chatbot instructions updated")
    
    return RedirectResponse(
        url="/admin/settings?status=success&message=" + urllib.parse.quote_plus("Custom instructions saved successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


# LLM provider is always OpenAI - no need for selection endpoint


@router.post("/settings/auto-train")
async def trigger_auto_training(
    background_tasks: BackgroundTasks,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Manually trigger batch auto-training from recent conversations."""
    try:
        from app.services.auto_training import batch_train_from_recent_conversations
        
        # Run batch training in background (function creates its own DB session)
        background_tasks.add_task(batch_train_from_recent_conversations, days_back=7)
        
        logger.info("Batch auto-training triggered")
        return RedirectResponse(
            url="/admin/settings?status=success&message=" + urllib.parse.quote_plus("Auto-training started in background. Check logs for progress."),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as e:
        logger.error(f"Error triggering auto-training: {e}")
        return RedirectResponse(
            url="/admin/settings?status=error&message=" + urllib.parse.quote_plus(f"Failed to start auto-training: {str(e)}"),
            status_code=status.HTTP_303_SEE_OTHER,
        )


@router.get("/api/config")
async def get_api_config(request: Request, db: Session = Depends(get_db)) -> dict:
    """Get API configuration for frontend (public endpoint, no auth required)."""
    settings = db.query(models.AppSettings).first()
    
    # If auto-detect is enabled or no URL is set, try to auto-detect
    if not settings or settings.auto_detect_api_url or not settings.api_base_url:
        # Try to detect from request origin
        try:
            # Get origin from request headers (frontend's origin)
            origin = request.headers.get("origin") or request.headers.get("referer", "")
            
            # If we have an origin, use it but replace port with backend port
            if origin and origin.startswith("http"):
                from urllib.parse import urlparse
                parsed = urlparse(origin)
                # Use the same hostname but backend port
                api_url = f"{parsed.scheme}://{parsed.hostname}:8000"
            else:
                # Get host from request
                host = request.headers.get("host", "localhost:8000")
                # Extract hostname (remove port if present)
                hostname = host.split(":")[0]
                
                # Use the same protocol as the request
                scheme = "https" if request.url.scheme == "https" else "http"
                
                # Prefer localhost for local development
                if hostname in ["localhost", "127.0.0.1"]:
                    api_url = "http://localhost:8000"
                else:
                    # Use the request hostname
                    api_url = f"{scheme}://{hostname}:8000"
        except Exception:
            # Fallback to localhost
            api_url = "http://localhost:8000"
        
        return {
            "api_base_url": api_url,
            "auto_detect": True,
        }
    
    return {
        "api_base_url": settings.api_base_url,
        "auto_detect": False,
    }
