"""Dredactor 统一日志配置"""

import logging
import sys
from typing import Optional


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """配置并返回 Dredactor 根日志器

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        console: 是否输出到控制台

    Returns:
        logging.Logger: 配置好的日志器
    """
    root_logger = logging.getLogger("dredactor")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取子日志器

    Args:
        name: 模块名（通常使用 __name__）

    Returns:
        logging.Logger: 子日志器
    """
    if not name.startswith("dredactor"):
        name = f"dredactor.{name}"
    logger = logging.getLogger(name)

    root = logging.getLogger("dredactor")
    if not root.handlers:
        setup_logger()

    return logger
