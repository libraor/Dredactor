"""脱敏映射管理器 - 使用特征码方案"""

import json
import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .models.base import ParsedDocument, RedactionRecord, TextBlock, Table, TableCell

# 特征码标记格式
MARKER_PREFIX = "【*"
MARKER_SUFFIX = "*】"


@dataclass
class RedactionMapping:
    """脱敏映射条目"""

    original_text: str  # 原始敏感文本
    redacted_text: str  # 脱敏后的文本（如 ***********）
    marker: str  # 特征码标记（如 MAP_ID_0）
    rule_name: str  # 使用的规则名称
    location: str  # 位置描述
    start_pos: int  # 在脱敏文档中的起始位置
    end_pos: int  # 在脱敏文档中的结束位置

    def to_dict(self) -> Dict:
        return {
            "original_text": self.original_text,
            "redacted_text": self.redacted_text,
            "marker": self.marker,
            "rule_name": self.rule_name,
            "location": self.location,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "RedactionMapping":
        return cls(
            original_text=data["original_text"],
            redacted_text=data.get("redacted_text", ""),
            marker=data["marker"],
            rule_name=data.get("rule_name", ""),
            location=data.get("location", ""),
            start_pos=data.get("start_pos", 0),
            end_pos=data.get("end_pos", 0),
        )


@dataclass
class RedactionMapData:
    """完整的脱敏映射数据"""

    map_id: str  # 映射ID
    source_file: str  # 源文件路径
    redacted_file: str  # 脱敏文件路径
    mappings: List[RedactionMapping]  # 映射列表
    timestamp: str  # 创建时间戳

    def to_dict(self) -> Dict:
        return {
            "map_id": self.map_id,
            "source_file": self.source_file,
            "redacted_file": self.redacted_file,
            "mappings": [m.to_dict() for m in self.mappings],
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "RedactionMapData":
        return cls(
            map_id=data.get("map_id", ""),
            source_file=data.get("source_file", ""),
            redacted_file=data.get("redacted_file", ""),
            mappings=[RedactionMapping.from_dict(m) for m in data.get("mappings", [])],
            timestamp=data.get("timestamp", ""),
        )


class RedactionMapper:
    """脱敏映射管理器

    使用特征码方案：
    - 文件名标记：xxx_redacted_[MAP_ID].docx
    - 文档内标记：【*MAP_ID_0*】
    - 映射表存储：.mappings/[MAP_ID].json
    """

    MAPPINGS_DIR = ".mappings"

    def __init__(self):
        """初始化映射器"""
        self._ensure_mappings_dir()

    def _ensure_mappings_dir(self):
        """确保映射目录存在"""
        if not os.path.exists(self.MAPPINGS_DIR):
            os.makedirs(self.MAPPINGS_DIR)

    def generate_map_id(self) -> str:
        """生成新的映射ID"""
        return str(uuid.uuid4())[:8]

    def create_map(
        self,
        map_id: str,
        source_file: str,
        redacted_file: str,
        records: List[RedactionRecord],
        original_document: Optional[ParsedDocument] = None,
    ) -> RedactionMapData:
        """创建脱敏映射

        Args:
            map_id: 映射ID
            source_file: 源文件路径
            redacted_file: 脱敏文件路径
            records: 脱敏记录列表

        Returns:
            RedactionMapData: 映射数据
        """
        from datetime import datetime

        mappings = []
        for i, record in enumerate(records):
            marker = f"{map_id}_{i}"
            # 直接使用原始文本长度（简化处理）
            mappings.append(
                RedactionMapping(
                    original_text=record.original_text,
                    redacted_text=record.redacted_text,
                    marker=marker,
                    rule_name=record.rule_name,
                    location=record.location,
                    start_pos=record.start_pos,
                    end_pos=record.end_pos,
                )
            )

        return RedactionMapData(
            map_id=map_id,
            source_file=source_file,
            redacted_file=redacted_file,
            mappings=mappings,
            timestamp=datetime.now().isoformat(),
        )

    def _find_redacted_text_position(self, record: RedactionRecord) -> Tuple[int, int]:
        """查找脱敏文本在对应文本块中的位置

        由于 RedactionRecord 记录的是原始文档中的位置，
        我们需要根据这个信息推断脱敏文本的位置。

        对于简单的脱敏（如替换为固定字符），
        脱敏文本的位置就是原始文本的位置。

        Args:
            record: 脱敏记录

        Returns:
            Tuple[int, int]: (起始位置, 结束位置）
        """
        # 对于mask和replace模式，脱敏文本位置与原始文本位置相同
        # 因为脱敏是直接替换文本的
        # 计算脱敏文本的长度
        redacted_length = len(record.redacted_text)
        # 使用原始起始位置，但长度是脱敏后的长度
        return (record.start_pos, record.start_pos + redacted_length)

    def save_map(self, map_data: RedactionMapData, map_path: Optional[str] = None) -> bool:
        """保存映射文件

        Args:
            map_data: 映射数据
            map_path: 映射文件路径（可选，默认保存到 .mappings/[map_id].json）

        Returns:
            bool: 是否成功
        """
        try:
            if map_path is None:
                map_path = os.path.join(self.MAPPINGS_DIR, f"{map_data.map_id}.json")

            with open(map_path, "w", encoding="utf-8") as f:
                json.dump(map_data.to_dict(), f, ensure_ascii=False, indent=2)

            return True
        except Exception:
            return False

    def load_map(self, map_path: str) -> Optional[RedactionMapData]:
        """加载映射文件

        Args:
            map_path: 映射文件路径

        Returns:
            RedactionMapData: 映射数据，失败返回None
        """
        try:
            with open(map_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return RedactionMapData.from_dict(data)
        except Exception:
            return None

    def extract_map_id_from_filename(self, filename: str) -> Optional[str]:
        """从文件名提取映射ID

        格式：xxx_redacted_[MAP_ID].docx
        """
        if "_redacted_" in filename:
            parts = filename.split("_redacted_")
            if len(parts) == 2:
                # 去除扩展名
                map_id = os.path.splitext(parts[1])[0]
                return map_id
        return None

    def get_map_path_from_redacted_file(self, redacted_file: str) -> Optional[str]:
        """根据脱敏文件路径获取映射文件路径

        Args:
            redacted_file: 脱敏文件路径

        Returns:
            str: 映射文件路径，如果没有找到返回None
        """
        filename = os.path.basename(redacted_file)
        map_id = self.extract_map_id_from_filename(filename)
        if map_id:
            return os.path.join(self.MAPPINGS_DIR, f"{map_id}.json")
        return None

    def generate_redacted_filename(self, original_file: str, map_id: str) -> str:
        """生成脱敏文件名

        格式：xxx_redacted_[MAP_ID].docx
        """
        base, ext = os.path.splitext(original_file)
        return f"{base}_redacted_{map_id}{ext}"

    def apply_markers_to_document(self, document: ParsedDocument, map_data: RedactionMapData) -> ParsedDocument:
        """在文档中应用特征码标记

        将脱敏文本替换为特征码标记

        Args:
            document: 文档对象（已经包含脱敏后的文本）
            map_data: 映射数据

        Returns:
            ParsedDocument: 应用标记后的文档
        """
        from .redaction_engine import RedactionEngine
        engine = RedactionEngine()
        redacted_doc = engine._clone_document(document)

        location_mappings = {}
        for mapping in map_data.mappings:
            loc = mapping.location
            if loc not in location_mappings:
                location_mappings[loc] = []
            location_mappings[loc].append(mapping)

        for i, para in enumerate(redacted_doc.paragraphs):
            location = f"段落{i+1}"
            if location in location_mappings:
                redacted_doc.paragraphs[i].text = self._apply_markers_to_text_by_location(
                    para.text, location_mappings[location]
                )

        for table_idx, table in enumerate(redacted_doc.tables):
            for row_idx, row in enumerate(table.rows):
                for col_idx, cell in enumerate(row):
                    location = f"表格{table_idx+1}行{row_idx+1}列{col_idx+1}"
                    if location in location_mappings:
                        redacted_doc.tables[table_idx].rows[row_idx][col_idx].text = (
                            self._apply_markers_to_text_by_location(cell.text, location_mappings[location])
                        )

        return redacted_doc

    def _apply_markers_to_text_by_location(self, text: str, mappings: List["RedactionMapping"]) -> str:
        """根据位置应用标记到文本

        只处理当前文本块的 mapping，避免跨文本块干扰。

        Args:
            text: 文本内容
            mappings: 当前文本块的映射列表

        Returns:
            str: 应用标记后的文本
        """
        if not mappings:
            return text

        result = text

        sorted_mappings = sorted(
            mappings,
            key=lambda m: len(m.redacted_text) if m.redacted_text else 0,
            reverse=True
        )

        replacements = []
        for mapping in sorted_mappings:
            marker = f"{MARKER_PREFIX}{mapping.marker}{MARKER_SUFFIX}"
            search_text = mapping.redacted_text
            if not search_text:
                continue
            start = 0
            while True:
                idx = result.find(search_text, start)
                if idx == -1:
                    break
                overlap = False
                for r_start, r_end, _ in replacements:
                    if idx < r_end and idx + len(search_text) > r_start:
                        overlap = True
                        break
                if not overlap:
                    replacements.append((idx, idx + len(search_text), marker))
                    break
                start = idx + 1

        replacements.sort(key=lambda x: x[0], reverse=True)

        for start, end, marker in replacements:
            result = result[:start] + marker + result[end:]

        return result

    def restore_document(
        self, redacted_file_path: str, output_path: str, map_path: Optional[str] = None
    ) -> Tuple[bool, Optional[ParsedDocument]]:
        """恢复脱敏文档

        Args:
            redacted_file_path: 脱敏文档路径
            output_path: 输出文件路径
            map_path: 映射文件路径（可选，默认从文件名推断）

        Returns:
            Tuple[bool, Optional[ParsedDocument]]: (是否成功, 恢复后的文档)
        """
        try:
            # 确定映射文件路径
            if map_path is None:
                map_path = self.get_map_path_from_redacted_file(redacted_file_path)
                if not map_path:
                    return False, None

            # 加载映射
            map_data = self.load_map(map_path)
            if not map_data:
                return False, None

            # 解析脱敏文档
            from .document_parser import DocumentParser
            parser = DocumentParser()
            doc = parser.parse(redacted_file_path)

            # 恢复文档
            restored_doc = self._restore_document_content(doc, map_data)

            # 导出（使用脱敏文档作为原始文档以保留格式）
            from .document_exporter import DocumentExporter
            exporter = DocumentExporter()
            exporter.export(restored_doc, output_path, overwrite=True, original_file_path=redacted_file_path)

            return True, restored_doc
        except Exception:
            return False, None

    def _restore_document_content(self, document: ParsedDocument, map_data: RedactionMapData) -> ParsedDocument:
        """恢复文档内容

        Args:
            document: 文档对象
            map_data: 映射数据

        Returns:
            ParsedDocument: 恢复后的文档
        """
        from .redaction_engine import RedactionEngine
        engine = RedactionEngine()
        restored_doc = engine._clone_document(document)

        # 创建标记到原始文本的映射
        marker_map = {}
        for mapping in map_data.mappings:
            marker_text = f"{MARKER_PREFIX}{mapping.marker}{MARKER_SUFFIX}"
            marker_map[marker_text] = mapping.original_text

        # 恢复段落
        for i, para in enumerate(restored_doc.paragraphs):
            restored_doc.paragraphs[i].text = self._restore_text(para.text, marker_map)

        # 恢复表格
        for table_idx, table in enumerate(restored_doc.tables):
            for row_idx, row in enumerate(table.rows):
                for col_idx, cell in enumerate(row):
                    restored_doc.tables[table_idx].rows[row_idx][col_idx].text = (
                        self._restore_text(cell.text, marker_map)
                    )

        return restored_doc

    def _restore_text(self, text: str, marker_map: Dict[str, str]) -> str:
        """恢复文本

        Args:
            text: 包含标记的文本
            marker_map: 标记到原始文本的映射

        Returns:
            str: 恢复后的文本
        """
        result = text
        for marker, original in marker_map.items():
            result = result.replace(marker, original)
        return result

    def get_map_summary(self, map_data: RedactionMapData) -> str:
        """获取映射摘要信息

        Args:
            map_data: 映射数据

        Returns:
            str: 摘要信息
        """
        lines = []
        lines.append(f"映射ID: {map_data.map_id}")
        lines.append(f"源文件: {map_data.source_file}")
        lines.append(f"脱敏文件: {map_data.redacted_file}")
        lines.append(f"映射数量: {len(map_data.mappings)}")
        lines.append(f"创建时间: {map_data.timestamp}")

        if map_data.mappings:
            # 统计各规则的使用情况
            rule_stats = {}
            for mapping in map_data.mappings:
                rule_stats[mapping.rule_name] = rule_stats.get(mapping.rule_name, 0) + 1

            lines.append("\n规则分布:")
            for rule_name, count in sorted(rule_stats.items()):
                lines.append(f"  {rule_name}: {count}处")

        return "\n".join(lines)


def create_mapper() -> RedactionMapper:
    """便捷函数：创建映射器"""
    return RedactionMapper()
