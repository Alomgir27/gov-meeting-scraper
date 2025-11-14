"""
Error type detection and retry decision logic for timeout, network, and bot-detection errors.

Error Types:
- TIMEOUT: Connection/read timeouts
- NETWORK: Connection failures, DNS errors
- BOT_DETECTION: Access denied, CAPTCHA challenges
- CLOUDFLARE: Cloudflare protection pages
- SERVER_ERROR: 5xx HTTP status codes
- RATE_LIMIT: 429 status or rate limit messages
- UNKNOWN: Unclassified errors

Retry Strategy: TIMEOUT, NETWORK, SERVER_ERROR, BOT_DETECTION, CLOUDFLARE are retriable
"""
from enum import Enum
from typing import Optional


class ErrorType(Enum):
    TIMEOUT = "timeout"
    BOT_DETECTION = "bot_detection"
    CLOUDFLARE = "cloudflare"
    NETWORK = "network"
    SERVER_ERROR = "server_error"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


BOT_DETECTION_INDICATORS = [
    "access denied",
    "captcha",
    "blocked",
    "forbidden",
    "please verify",
    "security check",
    "unusual traffic",
    "robot",
    "automated"
]

CLOUDFLARE_INDICATORS = [
    "cloudflare",
    "cf-ray",
    "checking your browser",
    "ddos protection"
]


def detect_error_type(error_msg: str, status_code: Optional[int] = None) -> ErrorType:
    error_lower = error_msg.lower()
    
    if "timeout" in error_lower or "timed out" in error_lower or "timed_out" in error_lower or "err_timed_out" in error_lower or "err_connection_timed_out" in error_lower:
        return ErrorType.TIMEOUT
        
    if status_code == 429 or "rate limit" in error_lower:
        return ErrorType.RATE_LIMIT
        
    if any(indicator in error_lower for indicator in CLOUDFLARE_INDICATORS):
        return ErrorType.CLOUDFLARE
        
    if any(indicator in error_lower for indicator in BOT_DETECTION_INDICATORS):
        return ErrorType.BOT_DETECTION
        
    if status_code and 500 <= status_code < 600:
        return ErrorType.SERVER_ERROR
        
    if "connection" in error_lower or "network" in error_lower or "err_connection" in error_lower or "getaddrinfo" in error_lower or "dns" in error_lower:
        return ErrorType.NETWORK
        
    return ErrorType.UNKNOWN


def is_retriable(error_type: ErrorType) -> bool:
    return error_type in {
        ErrorType.TIMEOUT,
        ErrorType.NETWORK,
        ErrorType.SERVER_ERROR,
        ErrorType.BOT_DETECTION,
        ErrorType.CLOUDFLARE
    }
