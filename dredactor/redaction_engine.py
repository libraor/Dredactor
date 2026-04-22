"""脱敏引擎 - 执行文本脱敏处理"""

import re
import time
from typing import List, Optional, Tuple

from .models import (
    ParsedDocument,
    RedactionMode,
    RedactionRecord,
    RedactionResult,
    RedactionStats,
    Rule,
    Table,
    TableCell,
    TextBlock,
)


class RedactionEngine:
    """脱敏引擎

    功能：
    - 基于规则的文本脱敏
    - 支持多种脱敏模式（替换、遮蔽、部分显示）
    - 记录脱敏位置和统计信息
    - 保留原始格式
    """

    def __init__(
        self,
        rules: Optional[List[Rule]] = None,
        default_mode: str = "mask",
        replacement_text: str = "****",
        override_mode: bool = False,
    ):
        """
        初始化脱敏引擎

        Args:
            rules: 脱敏规则列表
            default_mode: 默认脱敏模式
            replacement_text: 替换文本
            override_mode: 是否覆盖规则的默认模式
        """
        self.rules = rules or []
        self.default_mode = default_mode
        self.replacement_text = replacement_text
        self.override_mode = override_mode

    def set_rules(self, rules: List[Rule]) -> None:
        """设置脱敏规则"""
        self.rules = rules

    def add_rule(self, rule: Rule) -> None:
        """添加单个规则"""
        self.rules.append(rule)

    def redact_document(
        self, document: ParsedDocument, redact_tables: bool = True
    ) -> RedactionResult:
        """
        对整个文档执行脱敏

        Args:
            document: 解析后的文档对象
            redact_tables: 是否脱敏表格内容

        Returns:
            RedactionResult: 脱敏结果
        """
        start_time = time.time()

        # 创建文档副本
        redacted_doc = self._clone_document(document)

        # 创建统计信息对象
        stats = RedactionStats()

        # 脱敏段落
        for i, para in enumerate(document.paragraphs):
            redacted_text, records = self.redact_text(para.text, f"段落{i+1}")
            redacted_doc.paragraphs[i].text = redacted_text

            # 添加记录
            for record in records:
                record.location = f"段落{i+1}"
                stats.add_record(record)

        # 脱敏表格
        if redact_tables:
            for table_idx, table in enumerate(document.tables):
                for row_idx, row in enumerate(table.rows):
                    for col_idx, cell in enumerate(row):
                        location = f"表格{table_idx+1}行{row_idx+1}列{col_idx+1}"
                        redacted_text, records = self.redact_text(cell.text, location)

                        # 更新脱敏文档中的表格
                        redacted_doc.tables[table_idx].rows[row_idx][col_idx].text = redacted_text

                        # 添加记录
                        for record in records:
                            record.location = location
                            stats.add_record(record)

        # 计算处理时间
        stats.processing_time = time.time() - start_time

        return RedactionResult(
            original_doc=document,
            redacted_doc=redacted_doc,
            stats=stats,
            success=True,
        )

    def redact_text(
        self, text: str, location: str = "unknown"
    ) -> Tuple[str, List[RedactionRecord]]:
        """
        对文本执行脱敏

        Args:
            text: 原始文本
            location: 文本位置描述

        Returns:
            Tuple[str, List[RedactionRecord]]: (脱敏后文本, 脱敏记录列表)
        """
        original_text = text
        records = []
        replacements = []

        for rule in sorted(self.rules, key=lambda r: r.priority, reverse=True):
            if not rule.enabled:
                continue

            matches = list(re.finditer(rule.pattern, original_text))

            if not matches:
                continue

            for match in matches:
                match_start = match.start()
                match_end = match.end()

                if any(
                    match_start < existing_end and match_end > existing_start
                    for existing_start, existing_end, _ in replacements
                ):
                    continue

                original = match.group()
                redacted = self._redact_match(original, rule)

                replacements.append((match_start, match_end, redacted))

                record = RedactionRecord(
                    rule_name=rule.name,
                    original_text=original,
                    redacted_text=redacted,
                    location=location,
                    start_pos=match_start,
                    end_pos=match_end,
                )
                records.append(record)

        replacements.sort(key=lambda x: x[0], reverse=True)

        redacted_text = original_text
        for start, end, redacted in replacements:
            redacted_text = redacted_text[:start] + redacted + redacted_text[end:]

        return redacted_text, records

    def _redact_match(self, text: str, rule: Rule) -> str:
        """
        对匹配的文本执行脱敏

        Args:
            text: 匹配的文本
            rule: 使用的规则

        Returns:
            str: 脱敏后的文本
        """
        # 如果设置覆盖模式，使用引擎默认模式
        if self.override_mode:
            mode = self.default_mode
        else:
            mode = rule.mode or self.default_mode

        if mode == "replace":
            return self._replace_mode(text, rule)
        elif mode == "mask":
            return self._mask_mode(text)
        elif mode == "partial":
            return self._partial_mode(text, rule)
        else:
            # 默认使用遮蔽模式
            return self._mask_mode(text)

    def _replace_mode(self, text: str, rule: Rule) -> str:
        """
        替换模式：完全替换为指定文本

        Args:
            text: 原始文本
            rule: 使用的规则

        Returns:
            str: 替换后的文本
        """
        replacement = rule.replacement or self.replacement_text
        return replacement

    def _mask_mode(self, text: str) -> str:
        return "*" * len(text)

    def _partial_mode(self, text: str, rule: Rule) -> str:
        """
        部分显示模式：显示前后部分

        Args:
            text: 原始文本
            rule: 使用的规则

        Returns:
            str: 部分遮蔽后的文本
        """
        prefix = rule.show_prefix
        suffix = rule.show_suffix

        if len(text) <= prefix + suffix:
            # 文本太短，使用遮蔽模式
            return self._mask_mode(text)

        show_prefix = text[:prefix]
        show_suffix = text[-suffix:]
        mask_length = len(text) - prefix - suffix
        masked = "*" * mask_length

        return f"{show_prefix}{masked}{show_suffix}"

    def _clone_document(self, document: ParsedDocument) -> ParsedDocument:
        """
        创建文档的深拷贝

        Args:
            document: 原始文档

        Returns:
            ParsedDocument: 文档副本
        """
        # 创建新文档对象
        cloned = ParsedDocument(
            file_path=document.file_path,
            file_name=document.file_name,
            title=document.title,
        )

        # 复制段落
        cloned.paragraphs = [
            TextBlock(
                text=para.text,
                type=para.type,
                location=para.location,
                metadata=para.metadata.copy(),
                font_name=para.font_name,
                font_size=para.font_size,
                bold=para.bold,
                italic=para.italic,
                underline=para.underline,
            )
            for para in document.paragraphs
        ]

        # 复制表格
        cloned.tables = []
        for table in document.tables:
            cloned_table = Table(location=table.location, metadata=table.metadata.copy())

            for row in table.rows:
                cloned_row = []
                for cell in row:
                    cloned_cell = TableCell(
                        text=cell.text,
                        row=cell.row,
                        col=cell.col,
                        metadata=cell.metadata.copy(),
                    )
                    cloned_row.append(cloned_cell)
                cloned_table.rows.append(cloned_row)

            cloned.tables.append(cloned_table)

        # 复制页眉页脚
        cloned.headers = document.headers.copy()
        cloned.footers = document.footers.copy()

        # 复制元数据
        cloned.metadata = document.metadata.copy()

        return cloned

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            dict: 统计信息字典
        """
        return {
            "rule_count": len(self.rules),
            "enabled_rule_count": sum(1 for r in self.rules if r.enabled),
            "default_mode": self.default_mode,
            "replacement_text": self.replacement_text,
            "override_mode": self.override_mode,
        }


def create_engine(
    rules: Optional[List[Rule]] = None,
    mode: str = "mask",
    replacement: str = "****",
    override_mode: bool = False,
) -> RedactionEngine:
    """
    便捷函数：创建脱了敏引擎

    Args:
        rules: 脱敏规则列表
        mode: 脱敏模式
        replacement: 替换文本
        override_mode: 是否覆盖规则的默认模式

    Returns:
        RedactionEngine: 脱敏引擎实例
    """
    return RedactionEngine(
        rules=rules, default_mode=mode, replacement_text=replacement, override_mode=override_mode
    )
