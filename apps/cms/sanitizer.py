import nh3

ALLOWED_TAGS = {
    'a', 'b', 'strong', 'i', 'em', 'u', 'p', 'br', 'span',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote'
}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title', 'target'},
    '*': {'class', 'style', 'data-cms-key'}
}

def sanitize_html(dirty_html: str) -> str:
    """
    Sanitizes user/admin entered HTML using nh3 (Rust-powered high-speed sanitizer)
    to prevent XSS vulnerabilities.
    """
    if not dirty_html:
        return ""
    if not isinstance(dirty_html, str):
        dirty_html = str(dirty_html)

    return nh3.clean(
        dirty_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel="noopener noreferrer"
    )

def sanitize_text(text: str) -> str:
    """Strip all HTML tags completely for plain text fields."""
    if not text:
        return ""
    return nh3.clean_text(str(text))
