"""Process-wide logging setup so app.* loggers are actually visible.

Without this, INFO-level records (e.g. the privacy-masking observability
logs in app/safeguards/middleware.py) are silently dropped - Python's
default "handler of last resort" only surfaces WARNING and above.
"""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Attach a root stream handler once, at or above `level`.

    Idempotent - calling this more than once (e.g. across FastAPI app
    factory calls in tests) does not attach duplicate handlers.
    """

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    logging.basicConfig(level=level, format=_LOG_FORMAT)
