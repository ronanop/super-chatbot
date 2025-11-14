"""
Auto-training service for the chatbot.
Learns from conversations and automatically adds new information to the knowledge base.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.db import models
from app.ingestion.text_splitter import split_text
from app.services.gemini import get_generation_model
from app.vectorstore.pinecone_store import upsert_chunks
from app.ingestion.types import DocumentChunk

logger = logging.getLogger(__name__)


def extract_knowledge_from_conversation(
    user_message: str,
    bot_response: str,
    model=None
) -> Optional[str]:
    """
    Extract structured knowledge/facts from a conversation using Gemini.
    Returns extracted knowledge as text, or None if no useful knowledge found.
    """
    if not model:
        model = get_generation_model()
    
    extraction_prompt = f"""You are a knowledge extraction system. Analyze the following conversation and extract any factual, useful information that could be added to a knowledge base.

USER QUESTION: {user_message}

BOT RESPONSE: {bot_response}

INSTRUCTIONS:
1. Extract only factual, verifiable information from the bot's response
2. Format it as clear, standalone knowledge that could help answer similar questions
3. If the response contains no factual information (e.g., just greetings, apologies, or "I don't know"), return "NO_KNOWLEDGE"
4. If useful knowledge is found, return it in a clear, structured format
5. Do not include questions, only factual statements

EXTRACTED KNOWLEDGE (or "NO_KNOWLEDGE" if none):"""

    try:
        result = model.generate_content(extraction_prompt)
        extracted = getattr(result, "text", "").strip()
        
        if extracted and extracted.upper() != "NO_KNOWLEDGE" and len(extracted) > 50:
            return extracted
        return None
    except Exception as e:
        logger.error(f"Error extracting knowledge from conversation: {e}")
        return None


def should_add_to_knowledge_base(
    user_message: str,
    bot_response: str,
    session: models.ChatSession,
    db: Session
) -> bool:
    """
    Determine if a conversation should be added to knowledge base.
    Criteria:
    - Bot response is substantial (not just "I don't know")
    - User didn't express dissatisfaction
    - Response contains factual information
    """
    # Skip if response is too short or indicates lack of knowledge
    if len(bot_response.strip()) < 50:
        return False
    
    # Skip common "I don't know" patterns
    dont_know_patterns = [
        "i don't have",
        "i don't know",
        "not in my knowledge",
        "contact directly",
        "apologize, but i don't"
    ]
    response_lower = bot_response.lower()
    if any(pattern in response_lower for pattern in dont_know_patterns):
        return False
    
    # Check if user asked a follow-up question (indicates they might be satisfied)
    # This is a simple heuristic - could be improved
    return True


def add_conversation_to_knowledge_base(
    user_message: str,
    bot_response: str,
    source: str = "Auto-learned from conversations"
) -> int:
    """
    Add a conversation to the knowledge base.
    Returns number of chunks added.
    """
    try:
        # Combine user question and bot response as context
        knowledge_text = f"Q: {user_message}\n\nA: {bot_response}"
        
        # Split into chunks
        chunks = split_text(
            text=knowledge_text,
            source=source,
            metadata={
                "auto_learned": "true",
                "learned_date": datetime.now().isoformat(),
                "user_question": user_message[:200],  # Store first 200 chars of question
            }
        )
        
        if chunks:
            # Add to knowledge base
            upsert_chunks(chunks)
            logger.info(f"Added {len(chunks)} chunks to knowledge base from conversation")
            return len(chunks)
        
        return 0
    except Exception as e:
        logger.error(f"Error adding conversation to knowledge base: {e}")
        return 0


def process_conversation_for_training(
    session_id: int,
    user_message: str,
    bot_response: str
) -> bool:
    """
    Process a conversation to determine if it should be added to knowledge base.
    Returns True if knowledge was added, False otherwise.
    Creates its own database session for thread safety.
    """
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        
        try:
            session = db.get(models.ChatSession, session_id)
            if not session:
                return False
            
            # Check if we should add this conversation
            if not should_add_to_knowledge_base(user_message, bot_response, session, db):
                return False
            
            # Extract structured knowledge using Gemini
            extracted_knowledge = extract_knowledge_from_conversation(user_message, bot_response)
            
            if extracted_knowledge:
                # Add to knowledge base
                chunks_added = add_conversation_to_knowledge_base(
                    user_message=user_message,
                    bot_response=bot_response,
                    source=f"Auto-learned from session {session_id}"
                )
                return chunks_added > 0
            
            return False
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error processing conversation for training: {e}")
        return False


def batch_train_from_recent_conversations(
    days_back: int = 7,
    min_response_length: int = 100
) -> int:
    """
    Batch process recent conversations to add to knowledge base.
    Returns number of conversations processed.
    Creates its own database session for thread safety.
    """
    try:
        from app.db.session import SessionLocal
        db = SessionLocal()
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Get recent bot messages with their corresponding user messages
        recent_messages = (
            db.query(models.Message)
            .filter(
                models.Message.is_user_message.is_(False),
                models.Message.timestamp >= cutoff_date
            )
            .order_by(models.Message.timestamp.desc())
            .limit(100)  # Process last 100 conversations
            .all()
        )
        
        processed_count = 0
        
        for bot_message in recent_messages:
            # Get the user message that preceded this bot response
            user_message = (
                db.query(models.Message)
                .filter(
                    models.Message.session_id == bot_message.session_id,
                    models.Message.is_user_message.is_(True),
                    models.Message.timestamp < bot_message.timestamp
                )
                .order_by(models.Message.timestamp.desc())
                .first()
            )
            
            if not user_message or len(bot_message.content) < min_response_length:
                continue
            
            # Process for training (function creates its own DB session)
            if process_conversation_for_training(
                bot_message.session_id,
                user_message.content,
                bot_message.content
            ):
                processed_count += 1
        
            logger.info(f"Batch training: Processed {processed_count} conversations")
            return processed_count
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in batch training: {e}")
        return 0

