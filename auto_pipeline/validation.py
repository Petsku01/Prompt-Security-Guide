"""Input validation for auto_pipeline."""
import re
from urllib.parse import urlparse

MAX_QUERY_LENGTH = 200
MAX_URL_LENGTH = 2048

# Allow alphanumeric, spaces, and common search/URL characters
QUERY_PATTERN = re.compile(r'^[\w\s\-\.\:\?\&\=\%\+\'\"]+$', re.UNICODE)


def validate_query(query: str) -> str:
    """Validate and sanitize search query.
    
    Args:
        query: Raw search query string
        
    Returns:
        Sanitized query string
        
    Raises:
        ValueError: If query is invalid
    """
    if not query:
        raise ValueError("Query cannot be empty")
    
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError(f"Query too long: {len(query)} > {MAX_QUERY_LENGTH}")
    
    cleaned = query.strip()
    
    # Remove any null bytes or control characters
    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)
    
    return cleaned


def validate_url(url: str) -> bool:
    """Check if URL is safe to process.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL is valid and safe, False otherwise
    """
    if not url or len(url) > MAX_URL_LENGTH:
        return False
    
    try:
        parsed = urlparse(url)
        
        # Must have http/https scheme
        if parsed.scheme not in ('http', 'https'):
            return False
        
        # Must have a netloc (domain)
        if not parsed.netloc:
            return False
        
        # Block obvious dangerous patterns
        dangerous_patterns = [
            'javascript:',
            'data:',
            'file:',
            'ftp:',
        ]
        url_lower = url.lower()
        for pattern in dangerous_patterns:
            if pattern in url_lower:
                return False
        
        return True
        
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as filename.
    
    Args:
        name: Raw filename string
        
    Returns:
        Safe filename string
    """
    # Remove/replace unsafe characters
    safe = re.sub(r'[^\w\-\.]', '_', name)
    # Remove leading/trailing dots and underscores
    safe = safe.strip('._')
    # Limit length
    return safe[:100] if safe else 'unnamed'
