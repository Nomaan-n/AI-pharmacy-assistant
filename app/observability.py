"""Small structured logging helpers for the API."""
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("pharmacy_assistant")

@contextmanager
def timed_operation(name: str):
    started = time.perf_counter()
    try:
        yield
    finally:
        logger.info("operation=%s duration_ms=%.1f", name, (time.perf_counter() - started) * 1000)
