# 更新日志

本项目的重要变更记录。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [Unreleased] - 2026-07-31

### 性能优化

- **正则表达式预编译缓存**（`redaction_engine.py`）：`RedactionEngine` 新增 `_compiled_cache` 与 `_get_compiled_pattern()`，正则在首次使用时编译一次并缓存，避免每次 `redact_text()` 调用重复编译。大文档场景下预计文本脱敏耗时降低 40%-60%。
- **重叠检测算法升级**（`redaction_engine.py`）：`redact_text()` 中规则重叠检测由 O(n) 线性扫描改为基于 `bisect` 的 O(log n) 二分查找。维护按 `start` 排序的 `intervals` 列表，仅检查相邻区间即可判定重叠，密集匹配场景下性能显著提升。

### Bug 修复

- **空表格导致导出内容错位**（`document_exporter.py`）：`_export_with_original_format()` 遍历文档元素时，空表格也会递增 `table_idx`，导致后续表格内容写入错误位置。现增加 `if table.rows:` 校验，与解析器 `_extract_content` 的非空逻辑对齐。
- **配置字段名不匹配**（`config/config.yaml`）：`config.yaml` 中 `default_mode` 字段与代码中 `default_strategy` 不一致，导致用户配置的默认策略被忽略。已统一为 `default_strategy`，与 `config_loader._DEFAULT_CONFIG` 和 `RedactionEngine` 参数一致。

### 代码质量

- **类型标注修正**（`rule_manager.py`）：`list_rules()` 返回类型由 `List[Dict[str, any]]`（误用内置函数 `any`）修正为 `List[Dict[str, Any]]`，并补充 `Any` 导入，修复 mypy 报错。

## [0.1.1] - 此前版本

- 初始发布版本，支持基于正则规则的 Word 文档脱敏、特征码映射恢复、格式保留导出、JSON/Markdown 报告生成。
