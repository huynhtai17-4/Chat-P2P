"""
Simple logging helper used across the Core modules.
"""

import logging
import sys


def configure_logging(level=logging.INFO):
    """
    Configure a root logger with a consistent format.
    Safe to call multiple times (subsequent calls have no effect).
    """
    if logging.getLogger().handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[handler])


# Automatically configure logging with default settings when module is imported.
configure_logging()

