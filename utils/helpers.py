# utils/helpers.py
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# YouTube URL regex patterns
YOUTUBE_REGEX_PATTERNS = [
    r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})'
]

def is_youtube_url(text):
    """Check if text contains a YouTube URL"""
    for pattern in YOUTUBE_REGEX_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return True
    return False

def extract_youtube_id_from_text(text):
    """Extract YouTube video ID from text using regex"""
    for pattern in YOUTUBE_REGEX_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS"""
    if not seconds:
        return "Unknown"
    
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_filesize(mb_size):
    """Format filesize from MB to human-readable format"""
    if mb_size < 1:
        return f"{mb_size * 1024:.1f} KB"
    elif mb_size < 1024:
        return f"{mb_size:.1f} MB"
    else:
        return f"{mb_size / 1024:.2f} GB"