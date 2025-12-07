import logging
import sys

def configure_logging(level=logging.INFO):
    
    if logging.getLogger().handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    logging.basicConfig(level=level, handlers=[handler])

configure_logging()
