"""Shared utilities for the cricket-analytics project."""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable  # noqa: TC003 — used at runtime in decorators
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Decorator that retries a sync function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Initial delay in seconds before the first retry.
        backoff_factor: Multiplier applied to delay after each retry.
        exceptions: Tuple of exception types to catch and retry on.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=max_attempts,
                            error=str(exc),
                        )
                        raise
                    logger.warning(
                        "retry_attempt",
                        func=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(exc),
                    )
                    time.sleep(delay)
                    delay *= backoff_factor
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Decorator that retries an async function with exponential backoff.

    Same semantics as ``retry`` but uses ``asyncio.sleep`` instead of
    ``time.sleep``.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "retry_exhausted",
                            func=func.__name__,
                            attempts=max_attempts,
                            error=str(exc),
                        )
                        raise
                    logger.warning(
                        "retry_attempt",
                        func=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(exc),
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            raise RuntimeError("unreachable")  # pragma: no cover

        return wrapper

    return decorator
