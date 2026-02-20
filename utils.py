"""
Utility functions for the Release Flow framework.

This module provides helper functions for retry logic, rate limiting,
logging setup, and other common operations.
"""

import asyncio
import logging
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, Any, Optional

logger = logging.getLogger(__name__)

# Package-level logger name used across all modules
PACKAGE_LOGGER = "release_flow"


def setup_logging(
    *,
    verbosity: int = 0,
    log_file: Optional[str] = None,
    quiet: bool = False,
) -> None:
    """Configure logging for the Release Flow framework.

    Call this once from the CLI entry point. Library code should never call
    ``logging.basicConfig()`` directly.

    Args:
        verbosity: 0 = WARNING (default), 1 = INFO (``--verbose``),
                   2+ = DEBUG (``--debug``).
        log_file: Optional path to a log file. File always receives DEBUG
                  level regardless of console verbosity.
        quiet: When True, suppress console output below ERROR.
    """
    # Determine console log level
    if quiet:
        console_level = logging.ERROR
    elif verbosity >= 2:
        console_level = logging.DEBUG
    elif verbosity >= 1:
        console_level = logging.INFO
    else:
        console_level = logging.WARNING

    # Root package logger
    pkg_logger = logging.getLogger(PACKAGE_LOGGER)
    pkg_logger.setLevel(logging.DEBUG)  # handlers decide what to show
    pkg_logger.handlers.clear()

    # Console handler
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_fmt)
    pkg_logger.addHandler(console_handler)

    # File handler (always DEBUG)
    if log_file:
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)
        pkg_logger.addHandler(file_handler)

    pkg_logger.debug(
        "Logging configured: console=%s, file=%s",
        logging.getLevelName(console_level),
        log_file or "none",
    )

T = TypeVar('T')


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts.
        initial_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay in seconds between retries.
        exponential_base: Base for exponential backoff calculation.
        exceptions: Tuple of exception types to catch and retry.
        
    Returns:
        Decorated function with retry logic.
        
    Example:
        ```python
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def unstable_network_call():
            # Make API call
            pass
        ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            """Synchronous wrapper for retry logic."""
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            """Asynchronous wrapper for retry logic."""
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
            
            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RateLimiter:
    """
    Simple rate limiter for API calls.
    
    Ensures that operations don't exceed a specified rate limit.
    
    Example:
        ```python
        limiter = RateLimiter(calls_per_second=2)
        
        for i in range(10):
            limiter.wait()
            make_api_call()
        ```
    """
    
    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize the rate limiter.
        
        Args:
            calls_per_second: Maximum number of calls allowed per second.
        """
        if calls_per_second <= 0:
            raise ValueError("calls_per_second must be positive")
        
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time: Optional[float] = None
    
    def wait(self) -> None:
        """
        Wait if necessary to respect the rate limit.
        
        This method blocks until enough time has passed since the last call.
        """
        if self.last_call_time is not None:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                time.sleep(sleep_time)
        
        self.last_call_time = time.time()
    
    async def wait_async(self) -> None:
        """
        Async version of wait().
        
        This method waits asynchronously to respect the rate limit.
        """
        if self.last_call_time is not None:
            elapsed = time.time() - self.last_call_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                await asyncio.sleep(sleep_time)
        
        self.last_call_time = time.time()


def validate_positive_int(value: int, name: str) -> int:
    """
    Validate that a value is a positive integer.
    
    Args:
        value: Value to validate.
        name: Name of the parameter for error messages.
        
    Returns:
        The validated value.
        
    Raises:
        ValueError: If value is not a positive integer.
    """
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {type(value).__name__}")
    
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    
    return value


def validate_non_negative_number(value: float, name: str) -> float:
    """
    Validate that a value is a non-negative number.
    
    Args:
        value: Value to validate.
        name: Name of the parameter for error messages.
        
    Returns:
        The validated value.
        
    Raises:
        ValueError: If value is negative.
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    
    if value < 0:
        raise ValueError(f"{name} cannot be negative, got {value}")
    
    return value


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.
    
    Args:
        text: String to truncate.
        max_length: Maximum length of the result.
        suffix: Suffix to add if truncated.
        
    Returns:
        Truncated string.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
