"""Dredactor 自定义异常层次"""


class DredactorError(Exception):
    """Dredactor 基础异常"""


class ParseError(DredactorError):
    """文档解析异常"""

    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        super().__init__(f"文档解析失败 ({file_path}): {message}")


class FileNotFoundError_(ParseError):
    """文件不存在异常"""

    def __init__(self, file_path: str):
        super().__init__(file_path, "文件不存在")


class InvalidFileFormatError(ParseError):
    """不支持的文件格式异常"""

    def __init__(self, file_path: str, expected: str = ".docx"):
        self.expected = expected
        super().__init__(file_path, f"不支持的文件格式，期望 {expected}")


class RedactionError(DredactorError):
    """脱敏处理异常"""


class InvalidStrategyError(RedactionError):
    """无效的脱敏策略异常"""

    def __init__(self, strategy: str, valid_strategies: list = None):
        self.strategy = strategy
        self.valid_strategies = valid_strategies or []
        msg = f"无效的脱敏策略: '{strategy}'"
        if self.valid_strategies:
            msg += f"，有效策略: {self.valid_strategies}"
        super().__init__(msg)


class InvalidRuleError(RedactionError):
    """无效的脱敏规则异常"""

    def __init__(self, rule_name: str, message: str):
        self.rule_name = rule_name
        super().__init__(f"规则 '{rule_name}' 无效: {message}")


class ExportError(DredactorError):
    """文档导出异常"""

    def __init__(self, output_path: str, message: str):
        self.output_path = output_path
        super().__init__(f"文档导出失败 ({output_path}): {message}")


class FileExistsError_(ExportError):
    """输出文件已存在异常"""

    def __init__(self, output_path: str):
        super().__init__(output_path, "文件已存在")


class MappingError(DredactorError):
    """映射操作异常"""


class MappingSaveError(MappingError):
    """映射保存异常"""

    def __init__(self, map_id: str, message: str):
        self.map_id = map_id
        super().__init__(f"映射保存失败 ({map_id}): {message}")


class MappingLoadError(MappingError):
    """映射加载异常"""

    def __init__(self, map_path: str, message: str):
        self.map_path = map_path
        super().__init__(f"映射加载失败 ({map_path}): {message}")


class MappingNotFoundError(MappingError):
    """映射未找到异常"""

    def __init__(self, map_id: str):
        self.map_id = map_id
        super().__init__(f"映射未找到: {map_id}")


class RestoreError(DredactorError):
    """文档恢复异常"""

    def __init__(self, message: str):
        super().__init__(f"文档恢复失败: {message}")


class ReportError(DredactorError):
    """报告生成异常"""

    def __init__(self, output_path: str, message: str):
        self.output_path = output_path
        super().__init__(f"报告生成失败 ({output_path}): {message}")


class RuleManagerError(DredactorError):
    """规则管理异常"""


class RuleLoadError(RuleManagerError):
    """规则加载异常"""

    def __init__(self, path: str, message: str):
        self.path = path
        super().__init__(f"规则加载失败 ({path}): {message}")


class RuleValidationError(RuleManagerError):
    """规则验证异常"""

    def __init__(self, rule_name: str, message: str):
        self.rule_name = rule_name
        super().__init__(f"规则验证失败 '{rule_name}': {message}")


class AIError(DredactorError):
    """AI 模块异常"""

    def __init__(self, message: str):
        super().__init__(f"AI 模块错误: {message}")
