from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_user_message: Mapped[bool] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    folder: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    root_url: Mapped[str] = mapped_column(String(512), nullable=False)
    folder: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    total_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scraped_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    knowledge_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    knowledge_document: Mapped["KnowledgeDocument | None"] = relationship()
    urls: Mapped[list["CrawledUrl"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class CrawledUrl(Base):
    __tablename__ = "crawled_urls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    job: Mapped[CrawlJob] = relationship(back_populates="urls")


class BotUISettings(Base):
    __tablename__ = "bot_ui_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Basic settings
    bot_name: Mapped[str] = mapped_column(String(255), nullable=False, default="Cache Digitech Virtual Assistant")
    bot_icon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Colors
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#4338ca")  # Header/brand color
    secondary_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")  # Accent color
    background_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#ffffff")  # Chat background
    text_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#1e293b")  # Main text
    user_message_bg: Mapped[str] = mapped_column(String(7), nullable=False, default="#4338ca")  # User bubble
    user_message_text: Mapped[str] = mapped_column(String(7), nullable=False, default="#ffffff")  # User text
    bot_message_bg: Mapped[str] = mapped_column(String(7), nullable=False, default="#ffffff")  # Bot bubble
    bot_message_text: Mapped[str] = mapped_column(String(7), nullable=False, default="#1e293b")  # Bot text
    link_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#4338ca")  # Link color
    
    # Widget settings
    widget_position: Mapped[str] = mapped_column(String(20), nullable=False, default="bottom-right")  # bottom-right, bottom-left, etc.
    widget_size: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")  # small, medium, large
    show_branding: Mapped[bool] = mapped_column(nullable=False, default=True)
    
    # Advanced settings (stored as JSON)
    custom_css: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # API Configuration
    api_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # API base URL for frontend
    # Auto-detect if not set
    auto_detect_api_url: Mapped[bool] = mapped_column(nullable=False, default=True)
    # Custom Chatbot Instructions
    custom_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)  # Custom instructions for chatbot
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
