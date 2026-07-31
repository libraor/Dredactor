# Dredactor - Word文档脱敏工具

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.1-orange)](https://github.com/libraor/Dredactor)

一个强大的Word文档脱敏工具，支持基于规则和AI辅助的敏感信息识别与替换。

## 功能特性

- 多种敏感信息识别规则（身份证、手机号、邮箱、银行卡等）
- 自定义脱敏规则支持（通过规则管理器）
- 保留Word文档原始格式
- 支持批量文件导出（通过文档导出器）
- 详细的脱敏报告生成（JSON和Markdown格式）
- 可选AI智能脱敏（上下文感知，需要OpenAI API）
- 灵活的脱敏策略（替换、遮蔽、部分显示、公司名称）
- 策略覆盖功能（可覆盖规则的默认策略）
- 命令行界面（CLI）
- **脱敏映射与恢复**：支持保存脱敏映射，后续可恢复原始敏感信息
- **特征码方案**：使用文件名标记和文档内特征码，便于识别和恢复

## 安装

### 从源码安装

```bash
# 克隆仓库
git clone https://github.com/libraor/Dredactor.git
cd dredactor

# 安装依赖
pip install -r requirements.txt

# 安装Dredactor
pip install -e .
```

### 使用pip安装（发布后）

```bash
pip install dredactor
```

## 快速开始

### 基础使用

```bash
# 运行演示
python -m dredactor.main demo

# 脱敏单个文档（mask策略）
python -m dredactor.main process document.docx

# 指定输出文件
python -m dredactor.main process document.docx -o output.docx

# 使用replace策略
python -m dredactor.main process document.docx -s replace --replacement "[已脱敏]"

# 使用replace策略并覆盖规则默认设置
python -m dredactor.main process document.docx -s replace --replacement "[已脱敏]" --override-strategy

# 查看帮助
python -m dredactor.main process --help
```

### Web 界面使用

```bash
# 启动 Web 界面
python -m dredactor.main web

# 或者安装 web 依赖后
pip install dredactor[web]
dredactor web
```

启动后，在浏览器中访问 http://localhost:8501，可以：

- 上传 Word 文档进行脱敏
- 配置脱敏模式和选项
- 保存脱敏映射用于后续恢复
- 上传脱敏文档和映射文件，恢复原始敏感信息
- 查看和管理脱敏规则

### 脱敏映射与恢复

支持脱敏后编辑文档，然后恢复原始敏感信息的功能：

```bash
# 脱敏并保存映射（文件名将包含映射ID）
python -m dredactor.main process document.docx --save-map
# 生成：document_redacted_abc12345.docx
# 保存映射：.mappings/abc12345.json

# 手动编辑脱敏文档（添加条款、修改内容等）
# 编辑：document_redacted_abc12345.docx

# 恢复原始信息（从文件名自动识别映射ID）
python -m dredactor.main restore document_redacted_abc12345.docx
# 输出：document_redacted_abc12345_restored.docx
```

**工作流程**：
1. 原始文档 → 脱敏 → 生成特征码 → 保存
2. 手动编辑脱敏文档（添加条款、调整内容等）
3. 恢复文档 → 根据文件名自动识别映射 → 替换特征码为原始文本

**特征码格式**：
- 文件名标记：`xxx_redacted_[MAP_ID].docx`
- 文档内标记：`【*MAP_ID_0*】`
- 映射表存储：`.mappings/[MAP_ID].json`

**特征码方案说明**：
- 每个敏感信息替换为唯一的特征码标记（如 `【*abc12345_0*】`）
- 恢复时全局搜索特征码，不依赖精确位置
- 支持脱敏后自由编辑文档（移动、复制特征码等）
- 删除特征码 = 删除对应的恢复能力（预期行为）

### Python API使用

Dredactor可以作为Python库使用，提供更灵活的控制：

```python
from dredactor import DocumentParser, create_engine, DocumentExporter, load_rules

# 解析文档
parser = DocumentParser()
parsed_doc = parser.parse("document.docx")

# 加载规则
rule_manager = load_rules()
rules = rule_manager.get_enabled_rules()

# 创建脱敏引擎（使用mask策略，不覆盖规则默认设置）
engine = create_engine(rules, strategy='mask', override_strategy=False)
result = engine.redact_document(parsed_doc)

# 导出文档
exporter = DocumentExporter()
exporter.export(result.redacted_doc, "output.docx")

# 查看统计信息
print(f"脱敏数量: {result.stats.total_redacted}")
print(f"处理时间: {result.stats.processing_time:.3f}秒")
print(f"使用的规则: {result.stats.rules_used}")
```

### 使用replace模式覆盖规则设置

```python
from dredactor import DocumentParser, create_engine, DocumentExporter, load_rules

parser = DocumentParser()
parsed_doc = parser.parse("document.docx")

# 加载规则
rule_manager = load_rules()
rules = rule_manager.get_enabled_rules()

# 创建脱敏引擎（使用replace策略，并覆盖所有规则的默认策略）
engine = create_engine(
    rules,
    strategy='replace',
    replacement='[已脱敏]',
    override_strategy=True
)
result = engine.redact_document(parsed_doc)

# 导出
exporter = DocumentExporter()
exporter.export(result.redacted_doc, "output.docx")
```

### 脱敏映射与恢复

```python
from dredactor import create_mapper

# 创建映射器
mapper = create_mapper()
map_id = mapper.generate_map_id()

# 创建映射
map_data = mapper.create_map(
    map_id=map_id,
    source_file="document.docx",
    redacted_file="output.docx",
    records=result.stats.records
)

# 应用特征码到脱敏文档
redacted_doc = mapper.apply_markers_to_document(result.redacted_doc, map_data)

# 保存映射到 .mappings/[map_id].json
mapper.save_map(map_data)

# 恢复文档（从编辑后的脱敏文档）
restored_doc = mapper.restore_document(
    redacted_file_path="output.docx",
    output_path="restored.docx"
)
```

## 脱敏策略

Dredactor支持四种脱敏策略：

1. **替换策略 (replace)**：完全替换为指定文本
   ```python
   # 覆盖规则默认策略
   engine = create_engine(rules, strategy='replace', replacement='[已脱敏]', override_strategy=True)
   ```

2. **遮蔽策略 (mask)**：用星号或其他字符遮蔽
   ```python
   # 不覆盖规则默认策略（如果规则本身是mask策略）
   engine = create_engine(rules, strategy='mask', override_strategy=False)
   # 结果：138****5678
   ```

3. **部分显示策略 (partial)**：显示前后部分
   ```python
   # 部分显示策略需要规则中定义 show_prefix 和 show_suffix
   # 结果：138****5678
   ```

4. **公司名称策略 (company)**：保留地名和公司类型，遮蔽中间字号
   ```python
   # 结果：杭州****有限公司
   ```

## 预置规则

Dredactor包含丰富的预置规则：

| 规则名称 | 描述 | 默认启用 |
|---------|------|---------|
| mobile_phone | 中国大陆手机号 | 是 |
| id_card | 身份证号 | 是 |
| email | 电子邮件 | 是 |
| bank_card | 银行卡号 | 是 |
| credit_card | 信用卡号 | 是 |
| ip_address | IPv4地址 | 是 |
| chinese_id_card_18 | 18位身份证 | 是 |
| chinese_id_card_15 | 15位身份证 | 是 |
| uniform_social_credit_code | 统一社会信用代码 | 是 |
| passport_number | 护照号码 | 是 |
| driving_license | 驾驶证号码 | 是 |
| qq_number | QQ号 | 否 |
| wechat_id | 微信号 | 否 |
| mac_address | MAC地址 | 否 |
| url | URL链接 | 否 |

## 规则组

Dredactor支持规则组功能，方便批量管理相关规则：

```python
from dredactor import load_rules

rule_manager = load_rules()

# 获取个人信息组规则
personal_rules = rule_manager.get_group_rules("personal_info")

# 获取金融信息组规则
financial_rules = rule_manager.get_group_rules("financial")

# 获取网络信息组规则
network_rules = rule_manager.get_group_rules("network")

# 获取社交账号组规则
social_rules = rule_manager.get_group_rules("social")
```

## Python API使用示例

Dredactor也可以作为Python库使用：

```python
from dredactor import (
    DocumentParser,
    RedactionEngine,
    DocumentExporter,
    ReportGenerator,
    RuleManager,
    load_rules,
)

# 解析文档
parser = DocumentParser()
parsed_doc = parser.parse("document.docx")

# 脱敏处理
rule_manager = load_rules()
rules = rule_manager.get_enabled_rules()
engine = RedactionEngine(rules=rules)
result = engine.redact_document(parsed_doc)

# 导出文档
exporter = DocumentExporter()
exporter.export(result.redacted_doc, "output.docx")

# 生成报告
report_gen = ReportGenerator(format="json", detail_level="detailed")
report_gen.generate(result, "report.json")

# 查看统计信息
print(f"脱敏数量: {result.stats.total_redacted}")
print(f"处理时间: {result.stats.processing_time:.3f}秒")
print(f"使用的规则: {result.stats.rules_used}")
```

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/yourusername/dredactor.git
cd dredactor

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式化
black .

# 类型检查
mypy dredactor/
```

### 项目结构

```
Dredactor/
├── dredactor/              # 源代码目录
│   ├── __init__.py
│   ├── main.py             # CLI入口
│   ├── document_parser.py  # 文档解析器
│   ├── redaction_engine.py # 脱敏引擎（正则预编译缓存、bisect重叠检测）
│   ├── document_exporter.py # 文档导出器
│   ├── rule_manager.py      # 规则管理
│   ├── report_generator.py  # 报告生成
│   ├── redaction_mapper.py  # 脱敏映射管理器（特征码方案）
│   ├── ai_redactor.py       # AI智能脱敏（可选）
│   ├── config_loader.py     # 配置加载器
│   ├── exceptions.py        # 自定义异常层次
│   ├── logger.py            # 统一日志配置
│   ├── utils.py             # 公共工具函数
│   ├── models/              # 数据模型
│   ├── rules/               # 规则文件
│   ├── data/                # 数据文件（地名等）
│   └── config/              # 配置文件
├── tests/                   # 测试文件
├── web/                     # Web界面（Streamlit）
├── .mappings/               # 脱敏映射存储目录（.gitignore）
├── requirements.txt         # 依赖列表
├── setup.py                # 包配置
├── CHANGELOG.md            # 更新日志
└── README.md
```

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

本项目采用 Apache License 2.0 许可证 - 详见 [LICENSE](LICENSE) 文件

## 更新日志

详细的更新记录请见 [CHANGELOG.md](CHANGELOG.md)。

### v0.1.2 (2026-07-31)
- **性能优化**：正则表达式预编译缓存，大文档脱敏耗时降低 40%-60%
- **性能优化**：重叠检测算法升级为 bisect 二分查找（O(log n)），密集匹配场景性能显著提升
- **修复**：空表格导致导出内容错位的 bug
- **修复**：config.yaml 配置字段 `default_mode` 与代码不一致的问题，统一为 `default_strategy`
- **改进**：类型标注修正（`any` -> `Any`），修复 mypy 报错
- **改进**：文档与代码示例统一使用 `strategy`/`override_strategy` 参数名

### v0.1.1 (2026-04-22)
- **修复**：脱敏映射特征码生成bug，避免不同敏感信息使用相同特征码
- **优化**：按位置分组处理mapping，避免跨文本块干扰
- **改进**：恢复时全局搜索特征码，支持文档编辑后恢复

### v0.1.0 (2026-04-19)
- 初始版本发布
- 支持基础脱敏功能（解析、脱敏、导出）
- 支持12种预置规则（手机号、身份证、邮箱、银行卡等）
- 支持多种脱敏模式（replace、mask、partial）
- 支持模式覆盖功能（可覆盖规则的默认模式）
- 支持规则组功能（personal_info、financial、network、social）
- 支持报告生成（JSON和Markdown格式）
- 支持批量文件导出
- 提供完整的CLI命令行接口
- 可选AI智能脱敏功能（需要OpenAI API）
- 完整的测试覆盖（17个测试用例）
- **新增**：脱敏映射与恢复功能（特征码方案）
  - 支持 `--save-map` 选项保存脱敏映射
  - 支持 `restore` 命令恢复原始敏感信息
  - 文件名自动包含映射ID：`xxx_redacted_[MAP_ID].docx`
  - 文档内使用特征码标记：`【*MAP_ID_0*】`
  - 映射文件存储在 `.mappings/[MAP_ID].json`
  - 支持脱敏后手动编辑，再恢复原始信息

## 联系方式

- 项目主页: https://github.com/libraor/Dredactor
- 问题反馈: https://github.com/libraor/Dredactor/issues

## 致谢

感谢所有贡献者！
