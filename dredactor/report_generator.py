"""报告生成器 - 生成脱敏报告"""

import json
import os
from datetime import datetime
from typing import Optional

from .models import RedactionResult


class ReportGenerator:
    """报告生成器

    功能：
    - 生成JSON格式报告
    - 生成Markdown格式报告
    - 生成HTML格式报告
    - 支持详细的脱敏对比
    """

    def __init__(
        self,
        format: str = "json",
        detail_level: str = "detailed",
        include_comparison: bool = False,
    ):
        """
        初始化报告生成器

        Args:
            format: 报告格式 (json, markdown, html, both)
            detail_level: 详细程度 (simple, detailed, full)
            include_comparison: 是否包含脱敏对比
        """
        self.format = format.lower()
        self.detail_level = detail_level.lower()
        self.include_comparison = include_comparison

    def generate(
        self,
        result: RedactionResult,
        output_path: str,
    ) -> bool:
        """
        生成脱敏报告

        Args:
            result: 脱敏结果对象
            output_path: 输出文件路径

        Returns:
            bool: 是否生成成功
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            if self.format in ["json", "both"]:
                json_path = output_path
                if self.format == "both":
                    json_path = self._change_extension(output_path, "json")

                if not self._generate_json_report(result, json_path):
                    return False

            if self.format in ["markdown", "both"]:
                md_path = output_path
                if self.format == "both":
                    md_path = self._change_extension(output_path, "md")

                if not self._generate_markdown_report(result, md_path):
                    return False

            return True

        except Exception as e:
            print(f"错误：生成报告失败 - {str(e)}")
            return False

    def _generate_json_report(
        self, result: RedactionResult, output_path: str
    ) -> bool:
        """
        生成JSON格式报告

        Args:
            result: 脱敏结果对象
            output_path: 输出文件路径

        Returns:
            bool: 是否生成成功
        """
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "format_version": "1.0.0",
                "summary": self._generate_summary(result),
            }

            # 根据详细程度添加更多信息
            if self.detail_level in ["detailed", "full"]:
                report["stats"] = result.stats.to_dict()
                report["rules_used"] = list(result.stats.rules_used.keys())

            # 添加脱敏对比
            if self.include_comparison and self.detail_level == "full":
                report["comparison"] = self._generate_comparison(result)

            # 写入文件
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            print(f"错误：生成JSON报告失败 - {str(e)}")
            return False

    def _generate_markdown_report(
        self, result: RedactionResult, output_path: str
    ) -> bool:
        """
        生成Markdown格式报告

        Args:
            result: 脱敏结果对象
            output_path: 输出文件路径

        Returns:
            bool: 是否生成成功
        """
        try:
            lines = []

            # 标题
            lines.append("# Dredactor 脱敏报告")
            lines.append("")
            lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

            # 摘要
            lines.append("## 摘要")
            lines.append("")
            summary = self._generate_summary(result)
            lines.append(f"- **源文件**: {summary['source_file']}")
            lines.append(f"- **处理状态**: {'成功' if summary['success'] else '失败'}")
            lines.append(f"- **脱敏数量**: {summary['total_redacted']}")
            lines.append(f"- **使用规则数**: {summary['rules_used_count']}")
            lines.append(f"- **处理时间**: {summary['processing_time']:.3f}秒")
            lines.append("")

            # 规则统计
            if self.detail_level in ["detailed", "full"]:
                lines.append("## 规则使用统计")
                lines.append("")
                lines.append("| 规则名称 | 脱敏数量 |")
                lines.append("|----------|----------|")

                for rule_name, count in result.stats.rules_used.items():
                    lines.append(f"| {rule_name} | {count} |")
                lines.append("")

            # 脱敏记录
            if self.detail_level == "full" and result.stats.records:
                lines.append("## 脱敏详情")
                lines.append("")

                for i, record in enumerate(result.stats.records, 1):
                    lines.append(f"### 记录 {i}")
                    lines.append("")
                    lines.append(f"- **规则**: {record.rule_name}")
                    lines.append(f"- **位置**: {record.location}")
                    lines.append(f"- **原文**: `{record.original_text}`")
                    lines.append(f"- **脱敏后**: `{record.redacted_text}`")
                    lines.append(f"- **位置**: {record.start_pos}-{record.end_pos}")
                    lines.append("")

            # 写入文件
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            return True

        except Exception as e:
            print(f"错误：生成Markdown报告失败 - {str(e)}")
            return False

    def _generate_summary(self, result: RedactionResult) -> dict:
        """
        生成报告摘要

        Args:
            result: 脱敏结果对象

        Returns:
            dict: 摘要信息
        """
        return {
            "source_file": result.original_doc.file_path,
            "file_name": result.original_doc.file_name,
            "success": result.success,
            "error_message": result.error_message,
            "total_redacted": result.stats.total_redacted,
            "rules_used_count": len(result.stats.rules_used),
            "processing_time": result.stats.processing_time,
        }

    def _generate_comparison(self, result: RedactionResult) -> list:
        """
        生成脱敏对比信息

        Args:
            result: 脱敏结果对象

        Returns:
            list: 对比信息列表
        """
        comparisons = []

        # 段落对比
        for i, (orig_para, redacted_para) in enumerate(
            zip(result.original_doc.paragraphs, result.redacted_doc.paragraphs)
        ):
            if orig_para.text != redacted_para.text:
                comparisons.append(
                    {
                        "type": "paragraph",
                        "index": i,
                        "location": orig_para.location,
                        "original": orig_para.text,
                        "redacted": redacted_para.text,
                    }
                )

        # 表格对比
        for i, (orig_table, redacted_table) in enumerate(
            zip(result.original_doc.tables, result.redacted_doc.tables)
        ):
            for row_idx, (orig_row, redacted_row) in enumerate(
                zip(orig_table.rows, redacted_table.rows)
            ):
                for col_idx, (orig_cell, redacted_cell) in enumerate(
                    zip(orig_row, redacted_row)
                ):
                    if orig_cell.text != redacted_cell.text:
                        comparisons.append(
                            {
                                "type": "table_cell",
                                "table_index": i,
                                "row": row_idx,
                                "col": col_idx,
                                "original": orig_cell.text,
                                "redacted": redacted_cell.text,
                            }
                        )

        return comparisons

    def _change_extension(self, file_path: str, new_ext: str) -> str:
        """
        更改文件扩展名

        Args:
            file_path: 原文件路径
            new_ext: 新扩展名

        Returns:
            str: 新文件路径
        """
        base = os.path.splitext(file_path)[0]
        return f"{base}.{new_ext}"

    def generate_summary_text(self, result: RedactionResult) -> str:
        """
        生成摘要文本

        Args:
            result: 脱敏结果对象

        Returns:
            str: 摘要文本
        """
        summary = self._generate_summary(result)

        lines = []
        lines.append("脱敏处理完成")
        lines.append(f"  源文件: {summary['file_name']}")
        lines.append(f"  处理状态: {'成功' if summary['success'] else '失败'}")

        if summary['success']:
            lines.append(f"  脱敏数量: {summary['total_redacted']}")
            lines.append(f"  使用规则数: {summary['rules_used_count']}")
            lines.append(f"  处理时间: {summary['processing_time']:.3f}秒")

            if result.stats.rules_used:
                lines.append("  规则使用情况:")
                for rule_name, count in result.stats.rules_used.items():
                    lines.append(f"    - {rule_name}: {count}")
        else:
            lines.append(f"  错误信息: {summary['error_message']}")

        return "\n".join(lines)


def generate_report(
    result: RedactionResult,
    output_path: str,
    format: str = "json",
    detail_level: str = "detailed",
    include_comparison: bool = False,
) -> bool:
    """
    便捷函数：生成脱敏报告

    Args:
        result: 脱敏结果对象
        output_path: 输出文件路径
        format: 报告格式
        detail_level: 详细程度
        include_comparison: 是否包含对比

    Returns:
        bool: 是否生成成功
    """
    generator = ReportGenerator(
        format=format,
        detail_level=detail_level,
        include_comparison=include_comparison,
    )
    return generator.generate(result, output_path)
