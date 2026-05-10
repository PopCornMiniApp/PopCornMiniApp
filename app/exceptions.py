"""
Custom Exceptions for PopCorn Mini App
Provides specific exception types for better error handling and debugging
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Base Exception Classes
# ══════════════════════════════════════════════════════════════════════

class PopCornException(Exception):
    """Base exception for all PopCorn application errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ══════════════════════════════════════════════════════════════════════
# Database Exceptions
# ══════════════════════════════════════════════════════════════════════

class DatabaseError(PopCornException):
    """Base class for database-related errors"""


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""

    def __init__(self, message: str = "Failed to connect to database",
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails"""

    def __init__(self, query: str, error: str,
                 details: Optional[Dict[str, Any]] = None):
        message = f"Query failed: {error}"
        details = details or {}
        details['query'] = query
        super().__init__(message, details)


class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated"""

    def __init__(self,
                 message: str = "Database integrity constraint violated",
                 details: Optional[Dict[str,
                                        Any]] = None):
        super().__init__(message, details)


# ══════════════════════════════════════════════════════════════════════
# Backup & Restore Exceptions
# ══════════════════════════════════════════════════════════════════════

class BackupError(PopCornException):
    """Base class for backup-related errors"""


class BackupCreationError(BackupError):
    """Raised when backup creation fails"""

    def __init__(self, message: str = "Failed to create backup",
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class BackupRestoreError(BackupError):
    """Raised when backup restore fails"""

    def __init__(self, message: str = "Failed to restore backup",
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class BackupNotFoundError(BackupError):
    """Raised when requested backup is not found"""

    def __init__(
            self,
            backup_id: Optional[int] = None,
            backup_path: Optional[str] = None):
        details = {}
        if backup_id:
            details['backup_id'] = backup_id
        if backup_path:
            details['backup_path'] = backup_path
        super().__init__("Backup not found", details)


class BackupCorruptedError(BackupError):
    """Raised when backup file is corrupted"""

    def __init__(self, backup_path: str, reason: str):
        details = {'backup_path': backup_path, 'reason': reason}
        super().__init__("Backup file is corrupted", details)


# ══════════════════════════════════════════════════════════════════════
# Sync & HuggingFace Exceptions
# ══════════════════════════════════════════════════════════════════════

class SyncError(PopCornException):
    """Base class for synchronization errors"""


class HuggingFaceSyncError(SyncError):
    """Raised when HuggingFace sync fails"""

    def __init__(self, operation: str, error: str,
                 details: Optional[Dict[str, Any]] = None):
        message = f"HuggingFace {operation} failed: {error}"
        super().__init__(message, details)


class SyncConfigurationError(SyncError):
    """Raised when sync configuration is invalid"""

    def __init__(self, message: str = "Invalid sync configuration",
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


# ══════════════════════════════════════════════════════════════════════
# Content & Media Exceptions
# ══════════════════════════════════════════════════════════════════════

class ContentError(PopCornException):
    """Base class for content-related errors"""


class ContentNotFoundError(ContentError):
    """Raised when requested content is not found"""

    def __init__(self, content_type: str, content_id: int):
        details = {'content_type': content_type, 'content_id': content_id}
        super().__init__(f"{content_type.capitalize()} not found", details)


class StreamingError(ContentError):
    """Raised when streaming fails"""

    def __init__(self, message: str = "Streaming failed",
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)


class TMDBError(ContentError):
    """Raised when TMDB API interaction fails"""

    def __init__(self, operation: str, error: str,
                 details: Optional[Dict[str, Any]] = None):
        message = f"TMDB {operation} failed: {error}"
        super().__init__(message, details)


# ══════════════════════════════════════════════════════════════════════
# Authentication & Authorization Exceptions
# ══════════════════════════════════════════════════════════════════════

class AuthenticationError(PopCornException):
    """Base class for authentication errors"""


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid"""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired"""

    def __init__(self, message: str = "Authentication token has expired"):
        super().__init__(message)


class UnauthorizedError(AuthenticationError):
    """Raised when user is not authorized for an action"""

    def __init__(self, action: str, details: Optional[Dict[str, Any]] = None):
        message = f"Not authorized to perform: {action}"
        super().__init__(message, details)


# ══════════════════════════════════════════════════════════════════════
# Validation Exceptions
# ══════════════════════════════════════════════════════════════════════

class ValidationError(PopCornException):
    """Base class for validation errors"""


class InvalidInputError(ValidationError):
    """Raised when input validation fails"""

    def __init__(self, field: str, value: Any, reason: str):
        details = {'field': field, 'value': str(value), 'reason': reason}
        super().__init__(f"Invalid input for {field}", details)


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing"""

    def __init__(self, field: str):
        super().__init__(f"Required field missing: {field}", {'field': field})


# ══════════════════════════════════════════════════════════════════════
# Rate Limiting Exceptions
# ══════════════════════════════════════════════════════════════════════

class RateLimitError(PopCornException):
    """Raised when rate limit is exceeded"""

    def __init__(
            self,
            limit: int,
            window: int,
            retry_after: Optional[int] = None):
        details = {
            'limit': limit,
            'window_seconds': window,
            'retry_after_seconds': retry_after or window
        }
        super().__init__("Rate limit exceeded", details)


# ══════════════════════════════════════════════════════════════════════
# Network & External Service Exceptions
# ══════════════════════════════════════════════════════════════════════

class NetworkError(PopCornException):
    """Base class for network-related errors"""


class ConnectionTimeoutError(NetworkError):
    """Raised when network connection times out"""

    def __init__(self, url: str, timeout: int):
        details = {'url': url, 'timeout_seconds': timeout}
        super().__init__("Connection timeout", details)


class ExternalServiceError(NetworkError):
    """Raised when external service call fails"""

    def __init__(self, service: str, error: str,
                 details: Optional[Dict[str, Any]] = None):
        message = f"{service} service error: {error}"
        super().__init__(message, details)


# ══════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════

def log_exception(
        exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log an exception with context information

    Args:
        exc: The exception to log
        context: Additional context information
    """
    context = context or {}

    if isinstance(exc, PopCornException):
        logger.error(
            f"{exc.__class__.__name__}: {exc.message}",
            extra={
                'exception_type': exc.__class__.__name__,
                'details': exc.details,
                'context': context
            },
            exc_info=True
        )
    else:
        logger.error(
            f"{exc.__class__.__name__}: {str(exc)}",
            extra={
                'exception_type': exc.__class__.__name__,
                'context': context
            },
            exc_info=True
        )


def handle_database_error(
        error: Exception,
        operation: str,
        **kwargs) -> DatabaseError:
    """
    Convert generic database errors to specific DatabaseError types

    Args:
        error: The original exception
        operation: Description of the operation that failed
        **kwargs: Additional context

    Returns:
        Appropriate DatabaseError subclass
    """
    import sqlite3

    details = {'operation': operation, **kwargs}

    if isinstance(error, sqlite3.IntegrityError):
        return DatabaseIntegrityError(str(error), details)
    elif isinstance(error, sqlite3.OperationalError):
        if 'locked' in str(error).lower():
            return DatabaseConnectionError("Database is locked", details)
        return DatabaseQueryError(operation, str(error), details)
    elif isinstance(error, sqlite3.DatabaseError):
        return DatabaseError(str(error), details)
    else:
        return DatabaseError(
            f"Unexpected database error: {str(error)}", details)


# Made with ❤️ by Bob

# Made with Bob
