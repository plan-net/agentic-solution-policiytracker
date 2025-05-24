import os
import re
from pathlib import Path
from typing import List

from src.utils.exceptions import ConfigurationError


def validate_path_security(path: str) -> bool:
    """Validate path to prevent traversal attacks."""
    if ".." in path or "~" in path:
        return False
    
    # Additional security checks
    dangerous_patterns = [
        r"\.\.\/",  # Path traversal
        r"\/\.\.",  # Path traversal
        r"^\.\.",   # Relative path up
        r"^\/etc",  # System directories
        r"^\/proc", # System directories
        r"^\/sys",  # System directories
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, path):
            return False
    
    return True


def validate_file_extension(file_path: str, allowed_extensions: List[str]) -> bool:
    """Check if file has allowed extension."""
    extension = Path(file_path).suffix.lower()
    return extension in [ext.lower() for ext in allowed_extensions]


def validate_file_size(file_path: str, max_size_mb: int) -> bool:
    """Check if file size is within limits."""
    try:
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb <= max_size_mb
    except OSError:
        return False


def validate_directory_exists(path: str) -> bool:
    """Check if directory exists and is accessible."""
    # Resolve relative paths to absolute paths
    resolved_path = os.path.abspath(path)
    return os.path.isdir(resolved_path) and os.access(resolved_path, os.R_OK)


def validate_context_file(context_path: str) -> None:
    """Validate context file exists and has required structure."""
    if not os.path.exists(context_path):
        raise ConfigurationError("context_file", f"Context file not found: {context_path}")
    
    if not validate_path_security(context_path):
        raise ConfigurationError("context_file", "Invalid path in context file")
    
    # Additional validation can be added here for YAML structure


def get_supported_extensions() -> List[str]:
    """Get list of supported file extensions."""
    return [".md", ".markdown", ".pdf", ".docx", ".txt", ".html"]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent issues."""
    # Remove dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized