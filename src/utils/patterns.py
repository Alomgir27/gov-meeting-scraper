"""
Centralized regex patterns, keywords, and constants for meeting data extraction.

Pattern Categories:
- Date patterns: Multiple formats (ISO, US, long, short)
- Year patterns: Detection and validation
- Month patterns: Full and abbreviated names
- Meeting keywords: Container detection
- Link keywords: Agenda, minutes, video classification
- Platform detection: Video streaming services
- File extensions: Documents and videos
- Pagination patterns: Navigation keywords and selectors
- Validation constraints: Title length, year range
"""
import re

# Date Patterns - Full formats with year
DATE_PATTERNS_WITH_YEAR = [
    r'\d{4}-\d{2}-\d{2}',  # ISO: 2025-11-20
    r'\d{1,2}/\d{1,2}/\d{4}',  # US: 11/20/2025
    r'\d{1,2}-\d{1,2}-\d{4}',  # Dash: 11-20-2025
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',  # Long: November 20, 2025
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}'  # Short: Nov 20, 2025
]

# Date Patterns - Formats without year (need context year)
DATE_PATTERNS_WITHOUT_YEAR = [
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',  # Long: November 20
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}',  # Short: Nov 20
]

# Combined date pattern for quick detection
DATE_PATTERN_COMBINED = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|' \
                        r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}|' \
                        r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}'

# Date validation - strict ISO format
DATE_VALIDATION_PATTERN = r'^\d{4}-\d{2}-\d{2}$'

# Simple date pattern for quick detection
DATE_SIMPLE_PATTERN = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'

# Date with optional month names
DATE_WITH_MONTH_PATTERN = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'

# Year Patterns
YEAR_PATTERN = r'\b(20\d{2})\b'  # Word boundary: 2010-2099
YEAR_PATTERN_STRICT = r'^\s*(20\d{2})\s*$'  # Exact match with whitespace
YEAR_PATTERN_SIMPLE = r'(20\d{2})'  # Simple capture
YEAR_PATTERN_BOUNDARY = r'\b20\d{2}\b'  # With word boundary
YEAR_IN_STRING_PATTERN = r'\d{4}'  # Any 4-digit number

# Month Patterns
MONTH_PATTERN_FULL = r'^(January|February|March|April|May|June|July|August|September|October|November|December)'
MONTH_PATTERN_SHORT = r'^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
MONTH_PATTERN_ANY = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'

# HTML Class/ID patterns
CONTENT_PATTERN = r'content|main'  # Main content areas
MEETING_DIV_PATTERNS = ['meeting', 'agenda', 'item', 'event', 'row', 'card', 'calendar', 'session', 'board']

# Meeting Keywords - for container detection
MEETING_KEYWORDS = [
    'meeting', 'agenda', 'minutes', 'board', 'council', 
    'session', 'hearing', 'commission', 'committee'
]

# Agenda Keywords - for link classification
AGENDA_KEYWORDS = [
    'agenda', 'packet', 'notice', 'proposed', 'docs', 
    'document', 'board book', 'material'
]

# Minutes Keywords - for link classification
MINUTES_KEYWORDS = [
    'minutes', 'summary', 'transcript', 'notes', 'action', 'record'
]

# Video Keywords - for link classification
VIDEO_KEYWORDS = [
    'video', 'watch', 'recording', 'stream', 'media', 
    'play', 'live', 'broadcast'
]

# Video Platforms - domain detection
VIDEO_PLATFORMS = [
    'youtube', 'vimeo', 'swagit', 'granicus', 'civicclerk', 
    'champds', 'viebit', 'sharepoint'
]

# File Extensions
DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.html']
VIDEO_EXTENSIONS = ['.mp4', '.webm', '.avi', '.mov', '.wmv', '.m4v', '.flv', '.m3u8']

# Pagination Keywords
PAGINATION_KEYWORDS = ['next', 'older', 'more', 'previous', 'prev']

# Detail Page Keywords
DETAIL_PAGE_KEYWORDS = ['detail', 'view', 'full', 'more info', 'read more']

# Cancelled Meeting Keywords
CANCELLED_KEYWORDS = ['cancel', 'cancelled', 'postponed']

# HTML Attribute Patterns
MEETING_ATTR_PATTERNS = ['data-date', 'data-meeting', 'class="meeting', 'id="meeting']

# CSS Selectors for Pagination
PAGINATION_SELECTORS = [
    'a[rel="next"]',
    'a.next',
    'a.pagination-next',
    'li.next a',
    'a[aria-label*="next"]',
    'nav[role="navigation"] a',
]

# Numeric Constraints
YEAR_MIN = 2010
YEAR_MAX = 2030
TITLE_MIN_LENGTH = 5
TITLE_MAX_LENGTH = 300

# Pre-compiled Patterns (for performance)
COMPILED_PATTERNS = {
    'year': re.compile(YEAR_PATTERN),
    'year_strict': re.compile(YEAR_PATTERN_STRICT),
    'year_simple': re.compile(YEAR_PATTERN_SIMPLE),
    'year_boundary': re.compile(YEAR_PATTERN_BOUNDARY),
    'year_in_string': re.compile(YEAR_IN_STRING_PATTERN),
    'date_combined': re.compile(DATE_PATTERN_COMBINED, re.IGNORECASE),
    'date_simple': re.compile(DATE_SIMPLE_PATTERN),
    'date_with_month': re.compile(DATE_WITH_MONTH_PATTERN, re.IGNORECASE),
    'date_validation': re.compile(DATE_VALIDATION_PATTERN),
    'month_full': re.compile(MONTH_PATTERN_FULL, re.IGNORECASE),
    'month_short': re.compile(MONTH_PATTERN_SHORT, re.IGNORECASE),
    'month_any': re.compile(MONTH_PATTERN_ANY, re.IGNORECASE),
    'content_area': re.compile(CONTENT_PATTERN, re.IGNORECASE),
}
