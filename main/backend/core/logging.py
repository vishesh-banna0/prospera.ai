from __future__ import annotations

import logging
from contextvars import ContextVar

# A request-scoped id, set by the API middleware for each incoming request and
# read back by the log formatter. contextvars keeps this correct even when many
# requests are handled concurrently on the same event loop.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every log record.

    Without this, ``%(request_id)s`` in the format string would raise because
    the attribute is missing on records emitted outside a request.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(request_id)s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, with a consistent, request-aware format.

    Idempotent: calling it again replaces the handler rather than stacking
    duplicate handlers (which would print every line multiple times).
    """

    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.addFilter(RequestIdFilter())

    # Replace any handlers we previously installed so re-configuration is safe.
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Thin wrapper so call sites don't import logging
    directly and everyone gets the same configured hierarchy."""

    return logging.getLogger(name)


# Purpose:
# Provide one consistent, request-correlated logging setup for the whole
# backend so every log line can be traced to the request that produced it.
#
# What Should Not Live Here:
# - Business logic.
# - Per-module log message wording (belongs at the call sites).
