"""Dredactor核心数据模型定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RedactionMode(Enum):
    """脱敏模式枚举"""

    REPLACE = "replace"  # 完全替换
    MASK = "mask"  # 遮蔽（用星号）
    PARTIAL = "partial"  # 部分显示


@dataclass
class Rule:
    """脱敏规则定义"""

    name: str  # 规则名称
    pattern: str  # 正则表达式
    description: str = ""  # 规则描述
    enabled: bool = True  # 是否启用
    mode: str = "mask"  # 脱敏模式
    priority: int = 10  # 优先级（数值越大优先级越高）
    replacement: Optional[str] = None  # 自定义替换文本
    show_prefix: int = 3  # 部分显示模式：显示前n位
    show_suffix: int = 4  # 部分显示模式：显示后n位

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "pattern": self.pattern,
            "description": self.description,
            "enabled": self.enabled,
            "mode": self.mode,
            "priority": self.priority,
            "replacement": self.replacement,
            "show_prefix": self.show_prefix,
            "show_suffix": self.show_suffix,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """从字典创建规则"""
        return cls(
            name=data.get("name", ""),
            pattern=data.get("pattern", ""),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            mode=data.get("mode", "mask"),
            priority=data.get("priority", 10),
            replacement=data.get("replacement"),
            show_prefix=data.get("show_prefix", 3),
            show_suffix=data.get("show_suffix", 4),
        )


@dataclass
class TextBlock:
    """文本块，表示文档中的文本元素"""

    text: str  # 文本内容
    type: str = "paragraph"  # 类型：paragraph, table_cell, header, footer
    location: str = ""  # 位置描述（如第x段落）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    # 格式信息（用于保留原格式）
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class TableCell:
    """表格单元格"""

    text: str  # 单元格文本
    row: int  # 行号
    col: int  # 列号
    metadata: Dict[str, Any] = field(default_factory=dict)  # 格式等信息


@dataclass
class Table:
    """表格数据结构"""

    rows: List[List[TableCell]] = field(default_factory=list)  # 表格行
    location: str = ""  # 表格位置
    metadata: Dict[str, Any] = field(default_factory=dict)  # 表格属性（如边框、宽度等）

    @property
    def row_count(self) -> int:
        """行数"""
        return len(self.rows)

    @property
    def col_count(self) -> int:
        """列数"""
        return len(self.rows[0]) if self.rows else 0

    def get_cell(self, row: int, col: int) -> Optional[TableCell]:
        """获取单元格"""
        if 0 <= row < self.row_count and 0 <= col < self.col_count:
            return self.rows[row][col]
        return None

    def set_cell(self, row: int, col: int, cell: TableCell) -> None:
        """设置单元格"""
        if 0 <= row < self.row_count and 0 <= col < self.col_count:
            self.rows[row][col] = cell


@dataclass
class ParsedDocument:
    """解析后的Word文档"""

    file_path: str = ""  # 源文件路径
    file_name: str = ""  # 文件名
    title: str = ""  # 文档标题

    # 文档内容
    paragraphs: List[TextBlock] = field(default_factory=list)  # 段落列表
    tables: List[Table] = field(default_factory=list)  # 表格列表
    headers: List[str] = field(default_factory=list)  # 页眉
    footers: List[str] = field(default_factory=list)  # 页脚

    # 文档元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.file_name and self.file_path:
            import os

            self.file_name = os.path.basename(self.file_path)

    @property
    def paragraph_count(self) -> int:
        """段落数量"""
        return len(self.paragraphs)

    @property
    def table_count(self) -> int:
        """表格数量"""
        return len(self.tables)

    @property
    def total_text_length(self) -> int:
        """总文本长度"""
        length = sum(len(p.text) for p in self.paragraphs)
        for table in self.tables:
            for row in table.rows:
                for cell in row:
                    length += len(cell.text)
        return length


@dataclass
class RedactionRecord:
    """脱敏记录"""

    rule_name: str  # 使用的规则名称
    original_text: str  # 原始文本
    redacted_text: str  # 脱敏后文本
    location: str  # 位置描述
    start_pos: int  # 在文本中的起始位置
    end_pos: int  # 在文本中的结束位置

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_name": self.rule_name,
            "original_text": self.original_text,
            "redacted_text": self.redacted_text,
            "location": self.location,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
        }


@dataclass
class RedactionStats:
    """脱敏统计信息"""

    total_redacted: int = 0  # 总脱敏数量
    rules_used: Dict[str, int] = field(default_factory=dict)  # 各规则使用次数
    records: List[RedactionRecord] = field(default_factory=list)  # 脱敏记录
    processing_time: float = 0.0  # 处理时间（秒）

    def add_record(self, record: RedactionRecord) -> None:
        """添加脱敏记录"""
        self.records.append(record)
        self.total_redacted += 1
        self.rules_used[record.rule_name] = self.rules_used.get(record.rule_name, 0) + 1

    def get_rule_count(self, rule_name: str) -> int:
        """获取特定规则的使用次数"""
        return self.rules_used.get(rule_name, 0)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_redacted": self.total_redacted,
            "rules_used": self.rules_used,
            "records": [r.to_dict() for r in self.records],
            "processing_time": self.processing_time,
        }


@dataclass
class RedactionResult:
    """脱敏结果"""

    original_doc: ParsedDocument  # 原始文档
    redacted_doc: ParsedDocument  # 脱敏后文档
    stats: RedactionStats  # 统计信息
    success: bool = True  # 是否成功
    error_message: Optional[str] = None  # 错误信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "error_message": self.error_message,
            "stats": self.stats.to_dict(),
            "original_file": self.original_doc.file_path,
        }
