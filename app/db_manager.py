"""
Advanced Database Manager for PopCorn
Provides connection pooling, retry logic, and transaction management
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Base exception for database errors"""


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""


class DatabaseOperationError(DatabaseError):
    """Raised when database operation fails"""


class DatabaseManager:
    """
    Advanced database manager with retry logic and connection pooling.
    Handles transient errors and provides robust database operations.
    """

    def __init__(
            self,
            max_retries: int = 3,
            retry_delay: float = 1.0,
            backoff_factor: float = 2.0):
        """
        Initialize database manager.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
            backoff_factor: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self._stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'retried_operations': 0,
            'total_retry_attempts': 0
        }

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Check if an error is retryable.

        Args:
            error: The exception to check

        Returns:
            True if the error should trigger a retry
        """
        error_msg = str(error).lower()

        # SQLite-specific retryable errors
        retryable_patterns = [
            'database is locked',
            'unable to open database',
            'disk i/o error',
            'database disk image is malformed',
            'attempt to write a readonly database',
            'no such table',  # May occur during initialization
        ]

        return any(pattern in error_msg for pattern in retryable_patterns)

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: str = "database operation",
        **kwargs
    ) -> Any:
        """
        Execute a database operation with automatic retry on failure.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            operation_name: Name of the operation (for logging)
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function

        Raises:
            DatabaseOperationError: If all retry attempts fail
        """
        self._stats['total_operations'] += 1
        last_error = None
        delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                # Execute the operation
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success
                self._stats['successful_operations'] += 1
                if attempt > 0:
                    logger.info(
                        f"✅ {operation_name} succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_error = e

                # Check if we should retry
                if attempt < self.max_retries and self._is_retryable_error(e):
                    self._stats['retried_operations'] += 1
                    self._stats['total_retry_attempts'] += 1

                    logger.warning(
                        f"⚠️ {operation_name} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    logger.info(f"Retrying in {delay:.1f}s...")

                    # Wait before retry with exponential backoff
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor
                else:
                    # Non-retryable error or max retries reached
                    break

        # All retries failed
        self._stats['failed_operations'] += 1
        error_msg = f"{operation_name} failed after {self.max_retries + 1} attempts: {last_error}"
        logger.error(f"❌ {error_msg}")
        raise DatabaseOperationError(error_msg) from last_error

    @asynccontextmanager
    async def get_db_with_retry(self):
        """
        Get database connection with automatic retry on failure.

        Usage:
            async with db_manager.get_db_with_retry() as conn:
                # Use connection
                pass
        """
        from app.database import get_connection_from_pool

        conn = None
        try:
            # Get connection with retry
            async def get_conn():
                with get_connection_from_pool() as c:
                    return c

            conn = await self.execute_with_retry(
                get_conn,
                operation_name="get database connection"
            )

            yield conn

        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise DatabaseConnectionError(
                f"Could not establish database connection: {e}") from e
        finally:
            # Connection is returned to pool automatically by context manager
            pass

    async def execute_query_with_retry(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = True
    ) -> Any:
        """
        Execute a SQL query with retry logic.

        Args:
            query: SQL query to execute
            params: Query parameters
            fetch_one: If True, return single row
            fetch_all: If True, return all rows

        Returns:
            Query results
        """
        from app.database import get_connection_from_pool

        async def execute():
            with get_connection_from_pool() as conn:
                cursor = conn.execute(query, params)

                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.lastrowid

        return await self.execute_with_retry(
            execute,
            operation_name=f"execute query: {query[:50]}..."
        )

    async def execute_transaction_with_retry(
        self,
        operations: list[tuple[str, tuple]]
    ) -> bool:
        """
        Execute multiple operations in a transaction with retry logic.

        Args:
            operations: List of (query, params) tuples

        Returns:
            True if successful
        """
        from app.database import get_connection_from_pool

        async def execute_transaction():
            with get_connection_from_pool() as conn:
                try:
                    conn.execute("BEGIN TRANSACTION")

                    for query, params in operations:
                        conn.execute(query, params)

                    conn.execute("COMMIT")
                    return True

                except Exception as e:
                    conn.execute("ROLLBACK")
                    raise e

        return await self.execute_with_retry(
            execute_transaction,
            operation_name="execute transaction"
        )

    def get_stats(self) -> dict:
        """Get database manager statistics"""
        stats = self._stats.copy()

        if stats['total_operations'] > 0:
            stats['success_rate'] = (
                stats['successful_operations'] /
                stats['total_operations'] *
                100)
            stats['retry_rate'] = (
                stats['retried_operations'] / stats['total_operations'] * 100
            )
        else:
            stats['success_rate'] = 0.0
            stats['retry_rate'] = 0.0

        return stats

    def reset_stats(self):
        """Reset statistics"""
        self._stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'retried_operations': 0,
            'total_retry_attempts': 0
        }


# Global database manager instance
db_manager = DatabaseManager(
    max_retries=3,
    retry_delay=1.0,
    backoff_factor=2.0)


def with_db_retry(operation_name: str = "database operation"):
    """
    Decorator to add retry logic to database functions.

    Usage:
        @with_db_retry("get user data")
        async def get_user(user_id: int):
            # Database operation
            pass
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await db_manager.execute_with_retry(
                func,
                *args,
                operation_name=operation_name,
                **kwargs
            )
        return wrapper
    return decorator


# Convenience functions for common operations

async def safe_execute(
        query: str,
        params: tuple = (),
        fetch_one: bool = False) -> Any:
    """
    Safely execute a query with retry logic.

    Args:
        query: SQL query
        params: Query parameters
        fetch_one: Return single row if True

    Returns:
        Query results
    """
    return await db_manager.execute_query_with_retry(
        query=query,
        params=params,
        fetch_one=fetch_one,
        fetch_all=not fetch_one
    )


async def safe_transaction(operations: list[tuple[str, tuple]]) -> bool:
    """
    Safely execute a transaction with retry logic.

    Args:
        operations: List of (query, params) tuples

    Returns:
        True if successful
    """
    return await db_manager.execute_transaction_with_retry(operations)


def get_db_stats() -> dict:
    """Get database manager statistics"""
    return db_manager.get_stats()


# Health check function
async def check_database_health() -> dict:
    """
    Check database health and return status.

    Returns:
        Dictionary with health status
    """
    from app.database import get_connection_from_pool

    health = {
        'status': 'unknown',
        'responsive': False,
        'error': None,
        'stats': None
    }

    try:
        # Try to execute a simple query
        start_time = time.time()

        with get_connection_from_pool() as conn:
            result = conn.execute("SELECT 1").fetchone()

        response_time = (time.time() - start_time) * 1000  # ms

        if result and result[0] == 1:
            health['status'] = 'healthy'
            health['responsive'] = True
            health['response_time_ms'] = round(response_time, 2)
            health['stats'] = get_db_stats()
        else:
            health['status'] = 'unhealthy'
            health['error'] = 'Unexpected query result'

    except Exception as e:
        health['status'] = 'unhealthy'
        health['error'] = str(e)
        logger.error(f"Database health check failed: {e}")

    return health


# Made with ❤️ by Bob

# Made with Bob
