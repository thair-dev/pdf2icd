"""Project-wide logger utility for pdf2icd."""

from __future__ import annotations

import logging
import sys


def get_logger() -> logging.Logger:
    """Return a singleton logger instance with project-wide formatting.

    Returns:
        logging.Logger: Configured logger instance

    """
    log = logging.getLogger("pdf2icd")
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s [%(module)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log
