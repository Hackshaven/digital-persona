import re

def sanitize_filename(name: str) -> str:
    """Replace any character that is not alphanumeric, dash, underscore, or dot."""
    return re.sub(r'[^\w\-.]', '_', name)
