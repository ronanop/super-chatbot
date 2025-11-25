"""
Maximum security input validation for admin panel.
Implements comprehensive validation, sanitization, and security checks.
"""
from __future__ import annotations

import re
import os
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse
import mimetypes

# Try to import python-magic (optional, falls back to mimetypes)
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# Security constants
MAX_STRING_LENGTH = 10000  # Maximum string length
MAX_FILENAME_LENGTH = 255  # Maximum filename length
MAX_FOLDER_LENGTH = 100  # Maximum folder name length
MAX_URL_LENGTH = 2048  # Maximum URL length
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB maximum file size
MAX_DISPLAY_NAME_LENGTH = 500  # Maximum display name length

# Allowed file extensions (whitelist approach)
ALLOWED_PDF_EXTENSIONS = {'.pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
ALLOWED_TEXT_EXTENSIONS = {'.txt', '.md', '.markdown'}
ALLOWED_UPLOAD_EXTENSIONS = ALLOWED_PDF_EXTENSIONS | ALLOWED_IMAGE_EXTENSIONS | ALLOWED_TEXT_EXTENSIONS

# Allowed MIME types
ALLOWED_PDF_MIMES = {'application/pdf'}
ALLOWED_IMAGE_MIMES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
    'image/webp', 'image/svg+xml'
}
ALLOWED_TEXT_MIMES = {
    'text/plain', 'text/markdown', 'text/x-markdown'
}

# Validation patterns
FOLDER_NAME_PATTERN = re.compile(r'^[a-z0-9_-]{1,100}$')
DISPLAY_NAME_PATTERN = re.compile(r'^[\w\s\-.,!?()]{1,500}$')
FILENAME_PATTERN = re.compile(r'^[\w\s\-_.()]{1,255}$')
HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)
INTEGER_PATTERN = re.compile(r'^\d+$')
ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9]+$')

# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    re.compile(r'\.\./'),  # Path traversal
    re.compile(r'\.\.\\'),  # Windows path traversal
    re.compile(r'[<>"\']'),  # HTML/script injection
    re.compile(r'[;&|`$]'),  # Command injection
    re.compile(r'\x00'),  # Null byte
    re.compile(r'[\r\n]'),  # Newlines (for log injection)
]

# Blocked filenames (Windows reserved names)
BLOCKED_FILENAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


def validate_string_length(value: str, max_length: int = MAX_STRING_LENGTH, min_length: int = 0) -> str:
    """Validate string length."""
    if not isinstance(value, str):
        raise ValidationError(f"Expected string, got {type(value).__name__}")
    
    value = value.strip()
    
    if len(value) < min_length:
        raise ValidationError(f"String too short (minimum {min_length} characters)")
    
    if len(value) > max_length:
        raise ValidationError(f"String too long (maximum {max_length} characters)")
    
    return value


def sanitize_string(value: str, allow_html: bool = False) -> str:
    """Sanitize string to prevent XSS and injection attacks."""
    if not isinstance(value, str):
        raise ValidationError(f"Expected string, got {type(value).__name__}")
    
    # Remove null bytes
    value = value.replace('\x00', '')
    
    # Remove dangerous characters if HTML not allowed
    if not allow_html:
        # Remove HTML tags
        value = re.sub(r'<[^>]+>', '', value)
        # Remove script tags and event handlers
        value = re.sub(r'(?i)(javascript|on\w+\s*=)', '', value)
    
    # Remove control characters except newlines and tabs (if needed)
    value = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', value)
    
    return value.strip()


def validate_folder_name(folder: str) -> str:
    """Validate and sanitize folder name."""
    folder = validate_string_length(folder, MAX_FOLDER_LENGTH, 1)
    folder = sanitize_string(folder)
    
    # Convert to lowercase and replace invalid chars
    folder = re.sub(r'[^a-z0-9_-]', '-', folder.lower())
    folder = folder.strip('-').strip('_')
    
    if not folder:
        folder = "general"
    
    if not FOLDER_NAME_PATTERN.match(folder):
        raise ValidationError("Invalid folder name format")
    
    # Block dangerous folder names
    if folder.lower() in BLOCKED_FILENAMES:
        raise ValidationError("Folder name not allowed")
    
    return folder


def validate_display_name(name: str) -> str:
    """Validate display name."""
    name = validate_string_length(name, MAX_DISPLAY_NAME_LENGTH, 1)
    name = sanitize_string(name)
    
    if not DISPLAY_NAME_PATTERN.match(name):
        raise ValidationError("Invalid display name format")
    
    return name


def validate_filename(filename: str) -> str:
    """Validate filename for security."""
    if not filename:
        raise ValidationError("Filename cannot be empty")
    
    filename = validate_string_length(filename, MAX_FILENAME_LENGTH, 1)
    
    # Get base filename without path
    filename = Path(filename).name
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError("Filename contains invalid characters")
    
    # Check for blocked filenames
    base_name = Path(filename).stem.upper()
    if base_name in BLOCKED_FILENAMES:
        raise ValidationError("Filename not allowed")
    
    # Validate pattern
    if not FILENAME_PATTERN.match(filename):
        raise ValidationError("Invalid filename format")
    
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(f"File extension not allowed: {ext}")
    
    return filename


def validate_file_upload(
    file_content: bytes,
    filename: str,
    max_size: int = MAX_FILE_SIZE,
    allowed_extensions: Optional[set] = None,
    allowed_mimes: Optional[set] = None
) -> Tuple[str, str]:
    """Validate uploaded file with maximum security."""
    # Validate filename
    safe_filename = validate_filename(filename)
    
    # Check file size
    if len(file_content) > max_size:
        raise ValidationError(f"File too large (maximum {max_size / 1024 / 1024:.1f}MB)")
    
    if len(file_content) == 0:
        raise ValidationError("File is empty")
    
    # Get file extension
    ext = Path(safe_filename).suffix.lower()
    
    # Check extension whitelist
    if allowed_extensions and ext not in allowed_extensions:
        raise ValidationError(f"File type not allowed: {ext}")
    
    # Detect MIME type from content (more secure than trusting filename)
    if HAS_MAGIC:
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
        except Exception:
            # Fallback to mimetypes if magic fails
            mime_type, _ = mimetypes.guess_type(safe_filename)
            mime_type = mime_type or 'application/octet-stream'
    else:
        # Fallback to mimetypes if python-magic not available
        mime_type, _ = mimetypes.guess_type(safe_filename)
        mime_type = mime_type or 'application/octet-stream'
    
    # Validate MIME type
    if allowed_mimes and mime_type not in allowed_mimes:
        raise ValidationError(f"File MIME type not allowed: {mime_type}")
    
    # Verify extension matches MIME type
    expected_extensions = {
        'application/pdf': {'.pdf'},
        'image/jpeg': {'.jpg', '.jpeg'},
        'image/png': {'.png'},
        'image/gif': {'.gif'},
        'image/webp': {'.webp'},
        'image/svg+xml': {'.svg'},
        'text/plain': {'.txt'},
        'text/markdown': {'.md', '.markdown'},
    }
    
    if mime_type in expected_extensions:
        if ext not in expected_extensions[mime_type]:
            raise ValidationError(f"File extension {ext} does not match MIME type {mime_type}")
    
    return safe_filename, mime_type


def validate_path(path: str, base_path: Path, must_exist: bool = False) -> Path:
    """Validate file path and prevent path traversal."""
    # Normalize path
    path = Path(path)
    
    # Resolve to absolute path
    try:
        resolved = path.resolve()
    except Exception as e:
        raise ValidationError(f"Invalid path: {e}")
    
    # Ensure path is within base_path
    try:
        resolved.relative_to(base_path.resolve())
    except ValueError:
        raise ValidationError("Path traversal detected")
    
    # Check if path exists (if required)
    if must_exist and not resolved.exists():
        raise ValidationError("Path does not exist")
    
    return resolved


def validate_url(url: str) -> str:
    """Validate URL format and security."""
    url = validate_string_length(url, MAX_URL_LENGTH, 1)
    url = sanitize_string(url)
    
    # Basic format check
    if not URL_PATTERN.match(url):
        raise ValidationError("Invalid URL format")
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL: {e}")
    
    # Security checks
    if parsed.scheme not in ('http', 'https'):
        raise ValidationError("Only http and https URLs are allowed")
    
    # Block dangerous protocols
    dangerous_schemes = ('javascript', 'data', 'file', 'vbscript')
    if parsed.scheme.lower() in dangerous_schemes:
        raise ValidationError(f"Dangerous URL scheme: {parsed.scheme}")
    
    # Block localhost access (unless explicitly allowed)
    # Uncomment if you want to block localhost:
    # if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0'):
    #     raise ValidationError("Localhost URLs not allowed")
    
    return url


def validate_hex_color(color: str) -> str:
    """Validate hex color code."""
    color = validate_string_length(color, 7, 7)
    color = sanitize_string(color)
    
    if not HEX_COLOR_PATTERN.match(color):
        raise ValidationError("Invalid color format (must be #RRGGBB)")
    
    return color.upper()


def validate_integer(value: str, min_value: int = 0, max_value: int = 2**31 - 1) -> int:
    """Validate integer from string."""
    value = validate_string_length(value, 20, 1)
    
    if not INTEGER_PATTERN.match(value):
        raise ValidationError("Invalid integer format")
    
    try:
        int_value = int(value)
    except ValueError:
        raise ValidationError("Invalid integer value")
    
    if int_value < min_value:
        raise ValidationError(f"Integer too small (minimum {min_value})")
    
    if int_value > max_value:
        raise ValidationError(f"Integer too large (maximum {max_value})")
    
    return int_value


def validate_id(doc_id: str) -> int:
    """Validate document/session ID."""
    return validate_integer(doc_id, min_value=1)


def validate_confirm_text(text: str, expected: str = "DELETE ALL") -> bool:
    """Validate confirmation text."""
    text = validate_string_length(text, 100, 1)
    text = sanitize_string(text)
    
    return text.strip() == expected


def validate_csrf_token(token: str) -> str:
    """Validate CSRF token format."""
    token = validate_string_length(token, 200, 32)
    
    # CSRF tokens should be URL-safe base64
    if not re.match(r'^[A-Za-z0-9_-]{32,200}$', token):
        raise ValidationError("Invalid CSRF token format")
    
    return token


def validate_query_param(param: Optional[str], max_length: int = 500) -> Optional[str]:
    """Validate query parameter."""
    if param is None:
        return None
    
    param = validate_string_length(param, max_length)
    param = sanitize_string(param)
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(param):
            raise ValidationError("Query parameter contains dangerous characters")
    
    return param


def validate_json_input(data: dict, schema: dict) -> dict:
    """Validate JSON input against schema."""
    if not isinstance(data, dict):
        raise ValidationError("Expected JSON object")
    
    validated = {}
    
    for key, rules in schema.items():
        if key not in data:
            if rules.get('required', False):
                raise ValidationError(f"Missing required field: {key}")
            continue
        
        value = data[key]
        value_type = rules.get('type', str)
        
        # Type validation
        if not isinstance(value, value_type):
            raise ValidationError(f"Invalid type for {key}: expected {value_type.__name__}")
        
        # String-specific validation
        if value_type == str:
            max_len = rules.get('max_length', MAX_STRING_LENGTH)
            min_len = rules.get('min_length', 0)
            value = validate_string_length(value, max_len, min_len)
            value = sanitize_string(value, allow_html=rules.get('allow_html', False))
            
            # Pattern validation
            if 'pattern' in rules:
                if not rules['pattern'].match(value):
                    raise ValidationError(f"Invalid format for {key}")
        
        # Integer-specific validation
        elif value_type == int:
            min_val = rules.get('min_value', 0)
            max_val = rules.get('max_value', 2**31 - 1)
            if value < min_val or value > max_val:
                raise ValidationError(f"Value out of range for {key}")
        
        validated[key] = value
    
    return validated


def check_dangerous_content(content: str) -> None:
    """Check for dangerous content patterns."""
    content_lower = content.lower()
    
    # Check for script tags
    if re.search(r'<script[^>]*>', content_lower):
        raise ValidationError("Script tags not allowed")
    
    # Check for event handlers
    if re.search(r'on\w+\s*=', content_lower):
        raise ValidationError("Event handlers not allowed")
    
    # Check for javascript: protocol
    if 'javascript:' in content_lower:
        raise ValidationError("JavaScript protocol not allowed")
    
    # Check for SQL injection patterns
    sql_patterns = [
        r'union\s+select',
        r';\s*drop\s+table',
        r';\s*delete\s+from',
        r';\s*update\s+.*\s+set',
        r'exec\s*\(',
        r'execute\s*\(',
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, content_lower):
            raise ValidationError("Potentially dangerous SQL pattern detected")


def sanitize_for_database(value: str) -> str:
    """Sanitize value for database storage (additional layer)."""
    # SQLAlchemy ORM protects against SQL injection, but this adds extra safety
    value = sanitize_string(value)
    
    # Remove SQL comment patterns
    value = re.sub(r'--.*', '', value)
    value = re.sub(r'/\*.*?\*/', '', value, flags=re.DOTALL)
    
    return value


def validate_file_path_safe(file_path: str, base_directory: Path) -> Path:
    """Validate file path is safe and within base directory."""
    # Normalize the path
    try:
        # Remove any path traversal attempts
        normalized = Path(file_path).resolve()
        base_resolved = base_directory.resolve()
        
        # Ensure the path is within base directory
        try:
            normalized.relative_to(base_resolved)
        except ValueError:
            raise ValidationError("Path traversal detected")
        
        return normalized
    except Exception as e:
        raise ValidationError(f"Invalid file path: {e}")


# Note: KB_ROOT constant is defined in routes.py, not here
# This module provides validation functions that accept base_directory as parameter

