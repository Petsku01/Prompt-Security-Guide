"""Input validation for auto_pipeline."""
import re
from urllib.parse import urlparse
import ipaddress
import socket

BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '169.254.169.254'}
BLOCKED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),
]


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
    
    if not QUERY_PATTERN.match(cleaned):
        raise ValueError(f"Query contains invalid characters")
    
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

        hostname = parsed.hostname
        if hostname in BLOCKED_HOSTS:
            return False
            
        try:
            ip = ipaddress.ip_address(hostname)
            for network in BLOCKED_NETWORKS:
                if ip in network:
                    return False
        except ValueError:
            pass # Not an IP, continue

        
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
