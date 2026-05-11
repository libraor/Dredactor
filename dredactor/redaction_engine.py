"""脱敏引擎 - 执行文本脱敏处理"""

import re
import time
from typing import List, Optional, Tuple

from .models import (
    ParsedDocument,
    RedactionMethod,
    RedactionStrategy,
    RedactionRecord,
    RedactionResult,
    RedactionStats,
    Rule,
    Table,
    TableCell,
    TextBlock,
    IRREVERSIBLE_STRATEGIES,
)


class RedactionEngine:
    """脱敏引擎

    功能：
    - 基于规则的文本脱敏
    - 支持多种脱敏策略（替换、遮蔽、部分显示、公司名称）
    - 记录脱敏位置和统计信息
    - 保留原始格式
    """

    def __init__(
        self,
        rules: Optional[List[Rule]] = None,
        default_strategy: str = "replace",
        replacement_text: str = "[已脱敏]",
        override_strategy: bool = False,
    ):
        """
        初始化脱敏引擎

        Args:
            rules: 脱敏规则列表
            default_strategy: 默认脱敏策略
            replacement_text: 替换文本
            override_strategy: 是否覆盖规则的默认策略
        """
        self.rules = rules or []
        self.default_strategy = default_strategy
        self.replacement_text = replacement_text
        self.override_strategy = override_strategy
        self._warned_strategies: set = set()

        # 不可恢复策略警告
        if self.default_strategy in IRREVERSIBLE_STRATEGIES:
            print(f"警告：默认策略 '{self.default_strategy}' 为不可恢复策略，脱敏后无法还原原始数据")
            self._warned_strategies.add(self.default_strategy)

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
                redacted = self._redact_match(original, rule, match=match)

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

    def _redact_match(self, text: str, rule: Rule, match: Optional[re.Match] = None) -> str:
        """
        对匹配的文本执行脱敏

        Args:
            text: 匹配的文本
            rule: 使用的规则
            match: 正则匹配对象（company策略需要使用命名捕获组）

        Returns:
            str: 脱敏后的文本
        """
        # 如果设置覆盖策略，使用引擎默认策略
        if self.override_strategy:
            strategy = self.default_strategy
        else:
            strategy = rule.strategy or self.default_strategy

        # 不可恢复策略警告（每种策略只警告一次）
        if strategy in IRREVERSIBLE_STRATEGIES and strategy not in self._warned_strategies:
            print(f"警告：策略 '{strategy}' 为不可恢复策略，脱敏后无法还原原始数据")
            self._warned_strategies.add(strategy)

        if strategy == "replace":
            return self._replace_strategy(text, rule)
        elif strategy == "mask":
            return self._mask_strategy(text)
        elif strategy == "partial":
            return self._partial_strategy(text, rule)
        elif strategy == "company":
            return self._company_strategy(text, rule, match)
        else:
            # 默认使用遮蔽策略
            return self._mask_strategy(text)

    def _replace_strategy(self, text: str, rule: Rule) -> str:
        """
        替换策略：完全替换为指定文本

        Args:
            text: 原始文本
            rule: 使用的规则

        Returns:
            str: 替换后的文本
        """
        replacement = rule.replacement or self.replacement_text
        return replacement

    def _mask_strategy(self, text: str) -> str:
        """遮蔽策略：完全用星号遮蔽"""
        return "*" * len(text)

    def _partial_strategy(self, text: str, rule: Rule) -> str:
        """
        部分显示策略：显示前后部分，中间遮蔽

        Args:
            text: 原始文本
            rule: 使用的规则

        Returns:
            str: 部分遮蔽后的文本
        """
        prefix = rule.show_prefix
        suffix = rule.show_suffix

        if len(text) <= prefix + suffix:
            return self._mask_strategy(text)

        show_prefix = text[:prefix]
        show_suffix = text[-suffix:]
        mask_length = len(text) - prefix - suffix
        masked = "*" * mask_length

        return f"{show_prefix}{masked}{show_suffix}"

    def _company_strategy(self, text: str, rule: Rule, match: Optional[re.Match] = None) -> str:
        """
        公司名称脱敏策略：保留地名前缀和公司类型后缀，遮蔽中间字号部分

        这是针对公司名称数据类型的特殊脱敏策略，本质上是 partial 方式的变体。
        依赖正则模式中的命名捕获组：
        - geo: 地理前缀（省份/城市）
        - district: 区/县（可选）
        - name: 公司名称核心（被遮蔽部分）
        - type: 公司类型后缀

        Args:
            text: 原始匹配文本
            rule: 使用的规则
            match: 正则匹配对象（包含命名捕获组）

        Returns:
            str: 脱敏后的文本，如 "杭州****有限公司"
        """
        if match is None:
            return self._mask_strategy(text)

        try:
            geo = match.group("geo") or ""
            district = match.group("district") or ""
            name = match.group("name") or ""
            type_suffix = match.group("type") or ""
        except IndexError:
            return self._mask_strategy(text)

        prefix = geo + district

        if name:
            masked = "*" * len(name)
            return f"{prefix}{masked}{type_suffix}"
        else:
            return self._mask_strategy(text)

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
            "default_strategy": self.default_strategy,
            "replacement_text": self.replacement_text,
            "override_strategy": self.override_strategy,
        }


def create_engine(
    rules: Optional[List[Rule]] = None,
    strategy: str = "replace",
    replacement: str = "[已脱敏]",
    override_strategy: bool = False,
) -> RedactionEngine:
    """
    便捷函数：创建脱敏引擎

    Args:
        rules: 脱敏规则列表
        strategy: 脱敏策略
        replacement: 替换文本
        override_strategy: 是否覆盖规则的默认策略

    Returns:
        RedactionEngine: 脱敏引擎实例
    """
    return RedactionEngine(
        rules=rules, default_strategy=strategy, replacement_text=replacement, override_strategy=override_strategy
    )
