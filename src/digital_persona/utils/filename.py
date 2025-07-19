import re

def sanitize_filename(name: str) -> str:
    """
    Replace any character in the input string that is not alphanumeric, a dash, an underscore, or a dot.

    Args:
        name (str): The input filename or string to sanitize. It should be a string containing the original filename.

    Returns:
        str: A sanitized version of the input string where invalid characters are replaced with underscores.
    """
    return re.sub(r'[^\w\-.]', '_', name)
