"""
OpenAI LLM service.
"""
from __future__ import annotations

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Provider type
PROVIDER_OPENAI = "openai"


class LLMResponse:
    """Response wrapper for LLM outputs."""
    def __init__(self, text: str, provider: str = PROVIDER_OPENAI):
        self.text = text
        self.provider = provider


def get_llm_provider_from_db(db) -> str:
    """Get the LLM provider setting from database. Always returns OpenAI."""
    return PROVIDER_OPENAI


def generate_content(
    prompt: str,
    provider: str | None = None,
    model_name: str | None = None,
    db=None,
    conversation_history: list[dict] | None = None,
    image_url: str | None = None,  # URL to image for vision analysis
) -> LLMResponse:
    """
    Generate content using OpenAI.
    
    Args:
        prompt: The prompt text (or current user message if conversation_history is provided)
        provider: Ignored (kept for compatibility, always uses OpenAI)
        model_name: Specific model name. If None, uses default for OpenAI.
        db: Database session (optional, ignored)
        conversation_history: List of previous messages in format [{"role": "user|assistant", "content": "..."}, ...]
        image_url: URL to image for vision analysis
    
    Returns:
        LLMResponse with text and provider info
    """
    return _generate_openai(prompt, model_name, conversation_history, image_url)


def _get_openai_model(model_name: str | None = None):
    """Get OpenAI client instance."""
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    
    default_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    model_name = model_name or default_model
    
    # Cache client
    if not hasattr(_get_openai_model, "_client"):
        _get_openai_model._client = OpenAI(api_key=api_key)
    
    return _get_openai_model._client, model_name


def _generate_openai(prompt: str, model_name: str | None = None, conversation_history: list[dict] | None = None, image_url: str | None = None) -> LLMResponse:
    """Generate content using OpenAI. Supports GPT-4 Vision for image inputs."""
    client, model = _get_openai_model(model_name)
    
    # Use GPT-4 Vision if image is provided
    if image_url:
        # Force use of vision-capable model
        vision_model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
        model = vision_model
        logger.info(f"Using vision model {vision_model} for image analysis")
    
    # Build messages array for OpenAI
    messages = []
    
    # Add conversation history if provided
    if conversation_history:
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Map "assistant" role to OpenAI's expected format
            if role == "assistant":
                messages.append({"role": "assistant", "content": content})
            elif role == "user":
                # Check if this history message has an image (from previous conversation)
                # Note: We can't include images in history, so we just include the text
                # The current message with image will be handled separately below
                messages.append({"role": "user", "content": content})
    
    # Add current user message (with image if provided)
    if image_url:
        # For vision models, include image in the message
        import base64
        import requests
        from pathlib import Path
        
        # Fetch image and convert to base64
        try:
            image_data = None
            mime_type = "image/jpeg"  # Default
            
            # First, try to read from local file system (more reliable)
            if image_url.startswith("/uploads/chat_images/"):
                # Extract filename from path
                filename = image_url.split("/uploads/chat_images/")[-1]
                local_path = Path("uploads/chat_images") / filename
                
                if local_path.exists():
                    logger.info(f"Reading image from local file: {local_path}")
                    with open(local_path, "rb") as f:
                        image_data = f.read()
                    
                    # Determine MIME type from file extension
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(str(local_path))
                    if not mime_type:
                        # Fallback based on extension
                        ext = local_path.suffix.lower()
                        mime_map = {
                            ".jpg": "image/jpeg",
                            ".jpeg": "image/jpeg",
                            ".png": "image/png",
                            ".gif": "image/gif",
                            ".webp": "image/webp"
                        }
                        mime_type = mime_map.get(ext, "image/jpeg")
                else:
                    logger.warning(f"Local image file not found: {local_path}")
            
            # If not found locally, try fetching via HTTP
            if image_data is None:
                # Handle both absolute URLs and relative paths
                if image_url.startswith("/"):
                    # Relative path - construct full URL
                    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
                    full_url = f"{base_url.rstrip('/')}{image_url}"
                else:
                    full_url = image_url
                
                logger.info(f"Fetching image from URL: {full_url}")
                image_response = requests.get(full_url, timeout=30)
                image_response.raise_for_status()
                image_data = image_response.content
                
                # Determine MIME type from URL
                import mimetypes
                mime_type, _ = mimetypes.guess_type(image_url)
                if not mime_type:
                    # Try to get from Content-Type header
                    content_type = image_response.headers.get("Content-Type")
                    if content_type and content_type.startswith("image/"):
                        mime_type = content_type
                    else:
                        mime_type = "image/jpeg"  # Default
            
            if not image_data or len(image_data) == 0:
                raise ValueError("Image data is empty")
            
            logger.info(f"Successfully loaded image, size: {len(image_data)} bytes, MIME type: {mime_type}")
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Create vision message with image
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    }
                ]
            })
            logger.info("Image successfully added to vision message")
        except Exception as e:
            logger.error(f"Failed to process image for vision: {e}", exc_info=True)
            # Don't fall back to text-only - raise the error so user knows image processing failed
            raise RuntimeError(f"Failed to process image: {e}") from e
    else:
        messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
    )
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("OpenAI API returned no text.")
    return LLMResponse(text=text, provider=PROVIDER_OPENAI)


def generate_image_openai(prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
    """
    Generate an image using OpenAI DALL-E.
    
    Args:
        prompt: Text description of the image to generate
        size: Image size - "1024x1024", "1792x1024", or "1024x1792"
        quality: Image quality - "standard" or "hd"
    
    Returns:
        URL of the generated image
    """
    from openai import OpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    
    client = OpenAI(api_key=api_key)
    
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
    )
    
    image_url = response.data[0].url
    if not image_url:
        raise RuntimeError("OpenAI DALL-E API returned no image URL.")
    
    return image_url


def is_image_generation_request(message: str) -> bool:
    """
    Detect if the user is asking for image generation.
    Checks for common phrases that indicate image generation requests.
    """
    message_lower = message.lower().strip()
    
    # Keywords that suggest image generation
    image_keywords = [
        "generate an image",
        "create an image",
        "make an image",
        "draw a picture",
        "show me a picture",
        "show me an image",
        "generate a picture",
        "create a picture",
        "make a picture",
        "draw me",
        "image of",
        "picture of",
        "visualize",
        "illustrate",
        "dall-e",
        "dalle",
    ]
    
    # Check if message contains image generation keywords
    for keyword in image_keywords:
        if keyword in message_lower:
            return True
    
    # Check for patterns like "an image of X" or "a picture of X"
    import re
    patterns = [
        r"^(generate|create|make|draw|show)\s+(me\s+)?(an?\s+)?(image|picture|photo|illustration|visualization)",
        r"(an?\s+)?(image|picture|photo|illustration)\s+of\s+",
    ]
    
    for pattern in patterns:
        if re.search(pattern, message_lower):
            return True
    
    return False


def extract_image_prompt(message: str) -> str:
    """
    Extract a clean image generation prompt from the user's message.
    Removes common request phrases and returns just the description.
    """
    import re
    
    # Remove common request phrases
    patterns_to_remove = [
        r"^(generate|create|make|draw|show)\s+(me\s+)?(an?\s+)?(image|picture|photo|illustration|visualization)\s+(of\s+)?",
        r"^(can\s+you\s+)?(generate|create|make|draw|show)\s+(me\s+)?(an?\s+)?(image|picture|photo)\s+(of\s+)?",
        r"please\s+(generate|create|make|draw|show)\s+(me\s+)?(an?\s+)?(image|picture|photo)\s+(of\s+)?",
        r"i\s+(want|need|would\s+like)\s+(an?\s+)?(image|picture|photo)\s+(of\s+)?",
    ]
    
    cleaned = message
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    # If cleaned is too short or empty, use original message
    if len(cleaned) < 5:
        cleaned = message
    
    # Ensure prompt is descriptive (DALL-E works better with detailed prompts)
    if len(cleaned) < 20:
        cleaned = f"A high-quality, detailed image of {cleaned}"
    
    return cleaned
