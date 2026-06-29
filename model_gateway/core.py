"""Image utilities — base64 encoding, URL detection, format validation

Mirrors ark-cli's core.py. Used by vision_ask capability for image handling.
"""
import base64
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

# Supported image formats → MIME type
MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".svg": "image/svg+xml",
}


def is_url(s: str) -> bool:
    """Check if a string is an HTTP(S) URL."""
    try:
        parsed = urlparse(s)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def is_data_url(s: str) -> bool:
    """Check if a string is a data URL (base64-encoded inline image)."""
    return s.startswith("data:")


def encode_to_data_url(path: str) -> str:
    """Encode a local image file to a base64 data URL string."""
    p = Path(path)
    ext = p.suffix.lower()
    mime = MIME_MAP.get(ext, mimetypes.guess_type(p.name)[0] or "application/octet-stream")
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def get_image_mime(path: str) -> str:
    """Get MIME type for an image file."""
    ext = Path(path).suffix.lower()
    return MIME_MAP.get(ext, "application/octet-stream")
