"""数据模型定义"""

from .base import (
    ParsedDocument,
    TextBlock,
    Table,
    TableCell,
    RedactionResult,
    RedactionStats,
    RedactionRecord,
    Rule,
    RedactionMethod,
    RedactionStrategy,
    IRREVERSIBLE_STRATEGIES,
)

__all__ = [
    "ParsedDocument",
    "TextBlock",
    "Table",
    "TableCell",
    "RedactionResult",
    "RedactionStats",
    "RedactionRecord",
    "Rule",
    "RedactionMethod",
    "RedactionStrategy",
    "IRREVERSIBLE_STRATEGIES",
]
