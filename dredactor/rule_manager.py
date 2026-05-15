"""规则管理器 - 管理脱敏规则"""

import json
import os
import re
from typing import Dict, List, Optional

import yaml

from .logger import get_logger
from .models import Rule, IRREVERSIBLE_STRATEGIES

logger = get_logger(__name__)


class RuleManager:
    """脱敏规则管理器

    功能：
    - 加载默认规则和自定义规则
    - 规则验证
    - 规则的启用/禁用
    - 规则的添加/删除
    - 规则分组管理
    """

    def __init__(
        self,
        default_rules_path: Optional[str] = None,
        custom_rules_path: Optional[str] = None,
    ):
        """
        初始化规则管理器

        Args:
            default_rules_path: 默认规则文件路径
            custom_rules_path: 自定义规则文件路径
        """
        # 获取规则文件的默认路径
        if default_rules_path is None:
            default_rules_path = self._get_default_rules_path()
        if custom_rules_path is None:
            custom_rules_path = self._get_custom_rules_path()

        self.default_rules_path = default_rules_path
        self.custom_rules_path = custom_rules_path

        # 规则存储
        self.rules: Dict[str, Rule] = {}  # 所有规则（按名称索引）
        self.groups: Dict[str, List[str]] = {}  # 规则分组

        # 加载规则
        self._load_rules()

    def _get_default_rules_path(self) -> str:
        """获取默认规则文件路径"""
        # 尝试相对于包目录的路径
        try:
            package_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(package_dir, "rules", "default_rules.json")
        except Exception:
            return "dredactor/rules/default_rules.json"

    def _get_custom_rules_path(self) -> str:
        """获取自定义规则文件路径"""
        # 优先使用当前目录下的自定义规则
        if os.path.exists("rules/custom_rules.json"):
            return "rules/custom_rules.json"
        elif os.path.exists("custom_rules.json"):
            return "custom_rules.json"
        else:
            # 使用相对于包目录的路径
            package_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(package_dir, "rules", "custom_rules.json")

    def _load_rules(self) -> None:
        """加载所有规则"""
        # 加载默认规则
        self._load_default_rules()

        # 加载自定义规则
        self._load_custom_rules()

        # 按优先级排序
        self._sort_rules_by_priority()

    def _load_default_rules(self) -> None:
        """加载默认规则"""
        if os.path.exists(self.default_rules_path):
            try:
                with open(self.default_rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 加载规则
                for rule_data in data.get("rules", []):
                    rule = Rule.from_dict(rule_data)
                    self.rules[rule.name] = rule

                # 加载规则分组
                self.groups.update(data.get("groups", {}))

                # 解析动态模式
                self._resolve_dynamic_patterns()

            except Exception as e:
                logger.warning("加载默认规则失败 - %s", str(e))
        else:
            logger.warning("默认规则文件不存在 - %s", self.default_rules_path)

    def _load_custom_rules(self) -> None:
        """加载自定义规则"""
        if os.path.exists(self.custom_rules_path):
            try:
                with open(self.custom_rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 加载自定义规则（覆盖默认规则）
                for rule_data in data.get("rules", []):
                    rule = Rule.from_dict(rule_data)
                    self.rules[rule.name] = rule

                # 加载自定义规则分组
                self.groups.update(data.get("groups", {}))

            except Exception as e:
                logger.warning("加载自定义规则失败 - %s", str(e))

    def _sort_rules_by_priority(self) -> None:
        """按优先级排序规则（优先级高的在前）"""
        # 使用dict保持插入顺序（Python 3.7+）
        sorted_rules = sorted(
            self.rules.items(), key=lambda x: x[1].priority, reverse=True
        )
        self.rules = dict(sorted_rules)

    def get_all_rules(self) -> List[Rule]:
        """获取所有规则"""
        return list(self.rules.values())

    def get_enabled_rules(self) -> List[Rule]:
        """获取已启用的规则"""
        return [rule for rule in self.rules.values() if rule.enabled]

    def get_rule(self, name: str) -> Optional[Rule]:
        """根据名称获取规则"""
        return self.rules.get(name)

    def get_group_rules(self, group_name: str) -> List[Rule]:
        """获取规则组中的规则"""
        rule_names = self.groups.get(group_name, [])
        return [self.rules[name] for name in rule_names if name in self.rules]

    def add_rule(self, rule: Rule, save_to_custom: bool = True) -> bool:
        """
        添加自定义规则

        Args:
            rule: 规则对象
            save_to_custom: 是否保存到自定义规则文件

        Returns:
            bool: 是否添加成功
        """
        if not self._validate_rule(rule):
            return False

        self.rules[rule.name] = rule

        if save_to_custom:
            return self._save_custom_rule(rule)

        return True

    def _validate_rule(self, rule: Rule) -> bool:
        """验证规则"""
        # 检查规则名称
        if not rule.name or not isinstance(rule.name, str):
            logger.error("规则名称无效")
            return False

        # 检查正则表达式
        try:
            re.compile(rule.pattern)
        except re.error as e:
            logger.error("正则表达式无效 - %s", str(e))
            return False

        # 检查脱敏策略
        valid_strategies = ["replace", "mask", "partial", "company"]
        if rule.strategy not in valid_strategies:
            logger.error("脱敏策略无效，必须是 %s 之一", valid_strategies)
            return False

        # 不可恢复策略警告
        if rule.strategy in IRREVERSIBLE_STRATEGIES:
            logger.warning("策略 '%s' 为不可恢复策略，脱敏后无法还原原始数据", rule.strategy)

        return True

    def _save_custom_rule(self, rule: Rule) -> bool:
        """保存自定义规则到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.custom_rules_path), exist_ok=True)

            # 加载现有规则
            custom_rules = {}
            if os.path.exists(self.custom_rules_path):
                with open(self.custom_rules_path, "r", encoding="utf-8") as f:
                    custom_rules = json.load(f)

            # 更新规则
            if "rules" not in custom_rules:
                custom_rules["rules"] = []

            # 检查是否已存在同名规则
            existing_index = None
            for i, r in enumerate(custom_rules["rules"]):
                if r.get("name") == rule.name:
                    existing_index = i
                    break

            rule_dict = rule.to_dict()
            if existing_index is not None:
                custom_rules["rules"][existing_index] = rule_dict
            else:
                custom_rules["rules"].append(rule_dict)

            # 保存
            with open(self.custom_rules_path, "w", encoding="utf-8") as f:
                json.dump(custom_rules, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error("保存自定义规则失败 - %s", str(e))
            return False

    def remove_rule(self, name: str) -> bool:
        """
        删除规则

        Args:
            name: 规则名称

        Returns:
            bool: 是否删除成功
        """
        if name not in self.rules:
            return False

        del self.rules[name]

        # 从自定义规则文件中删除
        try:
            if os.path.exists(self.custom_rules_path):
                with open(self.custom_rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "rules" in data:
                    data["rules"] = [r for r in data["rules"] if r.get("name") != name]

                    with open(self.custom_rules_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error("删除规则失败 - %s", str(e))
            return False

    def enable_rule(self, name: str) -> bool:
        """
        启用规则

        Args:
            name: 规则名称

        Returns:
            bool: 是否启用成功
        """
        rule = self.rules.get(name)
        if not rule:
            return False

        rule.enabled = True
        return True

    def disable_rule(self, name: str) -> bool:
        """
        禁用规则

        Args:
            name: 规则名称

        Returns:
            bool: 是否禁用成功
        """
        rule = self.rules.get(name)
        if not rule:
            return False

        rule.enabled = False
        return True

    def list_rules(self, enabled_only: bool = False) -> List[Dict[str, any]]:
        """
        列出规则信息

        Args:
            enabled_only: 是否只显示已启用的规则

        Returns:
            List[Dict]: 规则信息列表
        """
        rules = self.get_enabled_rules() if enabled_only else self.get_all_rules()

        return [
            {
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "strategy": rule.strategy,
                "priority": rule.priority,
            }
            for rule in rules
        ]

    def reload(self) -> None:
        """重新加载规则"""
        self.rules.clear()
        self.groups.clear()
        self._load_rules()

    def import_rules_from_file(self, file_path: str) -> bool:
        """
        从文件导入规则

        Args:
            file_path: 规则文件路径

        Returns:
            bool: 是否导入成功
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_count = 0
            for rule_data in data.get("rules", []):
                rule = Rule.from_dict(rule_data)
                if self._validate_rule(rule):
                    self.rules[rule.name] = rule
                    imported_count += 1

            logger.info("成功导入 %d 条规则", imported_count)
            return True

        except Exception as e:
            logger.error("导入规则失败 - %s", str(e))
            return False

    def export_rules_to_file(self, file_path: str, enabled_only: bool = False) -> bool:
        """
        导出规则到文件

        Args:
            file_path: 输出文件路径
            enabled_only: 是否只导出已启用的规则

        Returns:
            bool: 是否导出成功
        """
        try:
            rules = self.get_enabled_rules() if enabled_only else self.get_all_rules()

            data = {
                "version": "1.0.0",
                "description": "Dredactor导出的规则",
                "rules": [rule.to_dict() for rule in rules],
                "groups": self.groups,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("成功导出 %d 条规则到 %s", len(rules), file_path)
            return True

        except Exception as e:
            logger.error("导出规则失败 - %s", str(e))
            return False

    def _resolve_dynamic_patterns(self) -> None:
        """解析动态模式占位符，生成实际的正则表达式"""
        DYNAMIC_PATTERN_REGISTRY = {
            "dynamic:company_name": self._generate_company_pattern,
        }

        for name, rule in self.rules.items():
            if rule.pattern in DYNAMIC_PATTERN_REGISTRY:
                generator = DYNAMIC_PATTERN_REGISTRY[rule.pattern]
                generated = generator()
                if generated:
                    rule.pattern = generated
                else:
                    rule.enabled = False
                    logger.warning("动态模式生成失败，已禁用规则 '%s'", name)

    def _get_place_names_path(self) -> str:
        """获取地名数据文件路径"""
        package_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(package_dir, "data", "place_names.json")

    def _load_place_names(self) -> dict:
        """加载地名数据"""
        path = self._get_place_names_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("加载地名数据失败 - %s", str(e))
                return {}
        else:
            logger.warning("地名数据文件不存在 - %s", path)
            return {}

    def _generate_company_pattern(self) -> str:
        """根据地名数据动态生成公司名称匹配的正则表达式。

        模式结构：
        (?P<geo>...)(?P<district>...)?(?P<name>...)(?P<type>...)

        Returns:
            str: 生成的正则表达式字符串
        """
        data = self._load_place_names()
        if not data:
            return ""

        # 构建地理前缀交替列表（按长度从长到短排列，确保正则优先匹配最长的）
        geo_parts = []

        # 自治区全称（最长，优先匹配）
        geo_parts.extend(data.get("autonomous_regions_full", []))

        # 特别行政区全称
        for sar in data.get("sar", []):
            geo_parts.append(sar + "特别行政区")

        # 省份 + "省" 后缀
        for province in data.get("provinces", []):
            geo_parts.append(province + "省")

        # 直辖市 + "市" 后缀
        for municipality in data.get("municipalities", []):
            geo_parts.append(municipality + "市")

        # 地级市 + "市" 后缀
        for city in data.get("prefecture_cities", []):
            geo_parts.append(city + "市")

        # 自治区简称
        geo_parts.extend(data.get("autonomous_regions", []))

        # 特别行政区简称
        geo_parts.extend(data.get("sar", []))

        # 国家级前缀
        geo_parts.extend(data.get("national_prefixes", []))

        # 省份简称（不带后缀）
        geo_parts.extend(data.get("provinces", []))

        # 直辖市简称
        geo_parts.extend(data.get("municipalities", []))

        # 地级市简称（不带后缀）
        geo_parts.extend(data.get("prefecture_cities", []))

        # 按长度降序排列（最长的排在最前面，确保正则交替匹配优先命中长串）
        geo_parts.sort(key=len, reverse=True)

        # 转义并构建交替模式
        geo_pattern = "|".join(re.escape(p) for p in geo_parts)

        # 构建区县交替列表（按长度降序）
        district_parts = data.get("districts", [])
        district_parts_sorted = sorted(district_parts, key=len, reverse=True)
        district_pattern = "|".join(re.escape(d) for d in district_parts_sorted)

        # 构建公司类型交替列表（同样按长度降序）
        type_parts = data.get("company_types", [])
        type_parts_sorted = sorted(type_parts, key=len, reverse=True)
        type_pattern = "|".join(re.escape(t) for t in type_parts_sorted)

        # 组合完整模式
        # district 部分优先匹配已知区县，其次匹配通用区县格式
        pattern = (
            f"(?P<geo>(?:{geo_pattern}))"
            f"(?P<district>(?:{district_pattern})(?:市|区|县|旗|州|盟)?|[\\u4e00-\\u9fa5]{{1,4}}(?:市|区|县|旗|州|盟))?"
            f"(?P<name>[\\u4e00-\\u9fa5]{{2,}}?)"
            f"(?P<type>(?:{type_pattern}))"
        )

        return pattern

    @staticmethod
    def create_rule(
        name: str,
        pattern: str,
        description: str = "",
        enabled: bool = True,
        strategy: str = "replace",
        priority: int = 10,
        replacement: Optional[str] = None,
    ) -> Rule:
        """
        便捷方法：创建规则对象

        Args:
            name: 规则名称
            pattern: 正则表达式（匹配特定数据类型）
            description: 规则描述
            enabled: 是否启用
            strategy: 脱敏策略（replace/mask/partial/company）
            priority: 优先级
            replacement: 替换文本（replace策略使用）

        Returns:
            Rule: 规则对象
        """
        return Rule(
            name=name,
            pattern=pattern,
            description=description,
            enabled=enabled,
            strategy=strategy,
            priority=priority,
            replacement=replacement,
        )


def load_rules(
    default_rules_path: Optional[str] = None,
    custom_rules_path: Optional[str] = None,
) -> RuleManager:
    """
    便捷函数：加载规则管理器

    Args:
        default_rules_path: 默认规则文件路径
        custom_rules_path: 自定义规则文件路径

    Returns:
        RuleManager: 规则管理器实例
    """
    return RuleManager(default_rules_path, custom_rules_path)
