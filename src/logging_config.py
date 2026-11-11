"""Logging setup shared by the pipeline, the dashboard and the scripts."""
from __future__ import annotations

import logging
import os

_CONFIGURED = False


def configure_logging(level: str | int | None = None) -> None:
    """Configure root logging once. The level comes from ``FMA_LOG_LEVEL`` (default WARNING)."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = level or os.environ.get("FMA_LOG_LEVEL", "WARNING")
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Module logger under the ``fma`` namespace."""
    configure_logging()
    return logging.getLogger(f"fma.{name.split('.')[-1]}")
