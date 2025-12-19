"""Système de logging pour agentichat."""

import logging
import sys
from pathlib import Path
from typing import Any


def setup_logger(name: str, level: str = "INFO", log_file: Path | None = None) -> logging.Logger:
    """Configure un logger.

    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Fichier de log optionnel

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Éviter les doublons de handlers
    if logger.handlers:
        return logger

    # Format avec timestamp
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler console (seulement si DEBUG)
    if level.upper() == "DEBUG":
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Handler fichier si spécifié
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Récupère un logger existant.

    Args:
        name: Nom du logger

    Returns:
        Logger
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager pour logger une opération."""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs: Any) -> None:
        """Initialise le contexte.

        Args:
            logger: Logger à utiliser
            operation: Nom de l'opération
            **kwargs: Paramètres additionnels à logger
        """
        self.logger = logger
        self.operation = operation
        self.kwargs = kwargs

    def __enter__(self) -> "LogContext":
        """Entre dans le contexte."""
        params = ", ".join(f"{k}={v}" for k, v in self.kwargs.items())
        self.logger.debug(f"[START] {self.operation} ({params})")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sort du contexte."""
        if exc_type:
            self.logger.error(f"[ERROR] {self.operation}: {exc_val}")
        else:
            self.logger.debug(f"[END] {self.operation}")
