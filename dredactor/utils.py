"""Dredactor 公共工具函数"""

import copy

from .models import ParsedDocument, TextBlock, Table, TableCell


def clone_document(document: ParsedDocument) -> ParsedDocument:
    """创建文档的深拷贝

    使用 copy.deepcopy 确保所有嵌套对象都被正确复制，
    避免修改副本时影响原始文档。

    Args:
        document: 原始文档

    Returns:
        ParsedDocument: 文档的深拷贝
    """
    return copy.deepcopy(document)
