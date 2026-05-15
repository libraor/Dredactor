"""Dredactor - Word文档脱敏工具"""

from .document_parser import DocumentParser, parse_document
from .redaction_engine import RedactionEngine, create_engine
from .document_exporter import DocumentExporter, export_document
from .report_generator import ReportGenerator, generate_report
from .rule_manager import RuleManager, load_rules
from .redaction_mapper import (
    RedactionMapper,
    create_mapper,
    RedactionMapping,
    RedactionMapData,
    MARKER_PREFIX,
    MARKER_SUFFIX,
)
from .models import (
    RedactionMethod,
    RedactionStrategy,
    IRREVERSIBLE_STRATEGIES,
    Rule,
)
from .exceptions import (
    DredactorError,
    ParseError,
    InvalidFileFormatError,
    RedactionError,
    InvalidStrategyError,
    InvalidRuleError,
    ExportError,
    MappingError,
    MappingSaveError,
    MappingLoadError,
    MappingNotFoundError,
    RestoreError,
    ReportError,
    RuleManagerError,
    RuleLoadError,
    RuleValidationError,
    AIError,
)
from .utils import clone_document
from .logger import get_logger, setup_logger

# AI模块（可选）
try:
    from .ai_redactor import AIRedactor, create_ai_redactor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

__all__ = [
    "DocumentParser",
    "parse_document",
    "RedactionEngine",
    "create_engine",
    "DocumentExporter",
    "export_document",
    "ReportGenerator",
    "generate_report",
    "RuleManager",
    "load_rules",
    "RedactionMapper",
    "create_mapper",
    "RedactionMapping",
    "RedactionMapData",
    "MARKER_PREFIX",
    "MARKER_SUFFIX",
    "RedactionMethod",
    "RedactionStrategy",
    "IRREVERSIBLE_STRATEGIES",
    "Rule",
    "AI_AVAILABLE",
    "DredactorError",
    "ParseError",
    "InvalidFileFormatError",
    "RedactionError",
    "InvalidStrategyError",
    "InvalidRuleError",
    "ExportError",
    "MappingError",
    "MappingSaveError",
    "MappingLoadError",
    "MappingNotFoundError",
    "RestoreError",
    "ReportError",
    "RuleManagerError",
    "RuleLoadError",
    "RuleValidationError",
    "AIError",
    "clone_document",
    "get_logger",
    "setup_logger",
]

if AI_AVAILABLE:
    __all__.extend(["AIRedactor", "create_ai_redactor"])