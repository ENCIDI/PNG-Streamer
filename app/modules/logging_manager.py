import logging
import sys
from logging.handlers import RotatingFileHandler

from app import paths

_CONFIGURED = False


def init_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
    file_handler = RotatingFileHandler(
        paths.LOGS_DIR / "app.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
