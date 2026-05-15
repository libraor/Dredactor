"""Dredactor 配置加载器 - 加载和管理 config.yaml"""

import os
from typing import Any, Dict, Optional

import yaml

from .logger import get_logger

logger = get_logger(__name__)

_DEFAULT_CONFIG = {
    "redaction": {
        "default_strategy": "replace",
        "replacement_text": "[已脱敏]",
        "partial_reveal": {
            "show_prefix": 3,
            "show_suffix": 4,
        },
        "preserve_formatting": True,
    },
    "rules": {
        "default_rules_file": "rules/default_rules.json",
        "custom_rules_file": "rules/custom_rules.json",
        "enable_custom_rules": True,
    },
    "ai": {
        "enabled": False,
        "api_key": "",
        "provider": "openai",
        "model": "gpt-4",
        "api_base": "",
        "max_tokens": 4096,
    },
    "output": {
        "default_suffix": "_redacted",
        "overwrite_original": False,
        "output_dir": "",
    },
    "report": {
        "format": "both",
        "detail_level": "detailed",
        "include_comparison": False,
        "output_dir": "reports",
    },
    "logging": {
        "level": "INFO",
        "file": "",
        "console": True,
    },
}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """深度合并两个字典，override 中的值优先"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigLoader:
    """配置加载器

    加载 config.yaml 并提供类型安全的访问接口。
    如果配置文件不存在或部分缺失，使用默认值填充。
    """

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = self._get_default_config_path()

        self._config_path = config_path
        self._config: Dict[str, Any] = {}

        self._load()

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        package_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(package_dir, "config", "config.yaml")

    def _load(self) -> None:
        """加载配置文件"""
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f) or {}
                self._config = _deep_merge(_DEFAULT_CONFIG, user_config)
                logger.info("已加载配置文件: %s", self._config_path)
            except Exception as e:
                logger.warning("加载配置文件失败，使用默认配置 - %s", str(e))
                self._config = _DEFAULT_CONFIG.copy()
        else:
            logger.info("配置文件不存在，使用默认配置: %s", self._config_path)
            self._config = _DEFAULT_CONFIG.copy()

    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径

        Args:
            key_path: 配置路径，如 "redaction.default_strategy"
            default: 默认值

        Returns:
            配置值
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    @property
    def redaction(self) -> Dict[str, Any]:
        return self._config.get("redaction", {})

    @property
    def rules(self) -> Dict[str, Any]:
        return self._config.get("rules", {})

    @property
    def ai(self) -> Dict[str, Any]:
        return self._config.get("ai", {})

    @property
    def output(self) -> Dict[str, Any]:
        return self._config.get("output", {})

    @property
    def report(self) -> Dict[str, Any]:
        return self._config.get("report", {})

    @property
    def logging_config(self) -> Dict[str, Any]:
        return self._config.get("logging", {})

    @property
    def full_config(self) -> Dict[str, Any]:
        return self._config.copy()

    def reload(self) -> None:
        """重新加载配置"""
        self._load()


_config_instance: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """获取全局配置实例（单例模式）

    Args:
        config_path: 配置文件路径（仅首次调用有效）

    Returns:
        ConfigLoader: 配置加载器实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance


def reset_config() -> None:
    """重置全局配置实例（主要用于测试）"""
    global _config_instance
    _config_instance = None
