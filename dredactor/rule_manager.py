"""规则管理器 - 管理脱敏规则"""

import json
import os
import re
from typing import Dict, List, Optional

import yaml

from .models import Rule


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

            except Exception as e:
                print(f"警告：加载默认规则失败 - {str(e)}")
        else:
            print(f"警告：默认规则文件不存在 - {self.default_rules_path}")

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
                print(f"警告：加载自定义规则失败 - {str(e)}")

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
            print("错误：规则名称无效")
            return False

        # 检查正则表达式
        try:
            re.compile(rule.pattern)
        except re.error as e:
            print(f"错误：正则表达式无效 - {str(e)}")
            return False

        # 检查模式
        valid_modes = ["replace", "mask", "partial"]
        if rule.mode not in valid_modes:
            print(f"错误：脱敏模式无效，必须是 {valid_modes} 之一")
            return False

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
            print(f"错误：保存自定义规则失败 - {str(e)}")
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
            print(f"错误：删除规则失败 - {str(e)}")
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
                "mode": rule.mode,
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

            print(f"成功导入 {imported_count} 条规则")
            return True

        except Exception as e:
            print(f"错误：导入规则失败 - {str(e)}")
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

            print(f"成功导出 {len(rules)} 条规则到 {file_path}")
            return True

        except Exception as e:
            print(f"错误：导出规则失败 - {str(e)}")
            return False

    @staticmethod
    def create_rule(
        name: str,
        pattern: str,
        description: str = "",
        enabled: bool = True,
        mode: str = "mask",
        priority: int = 10,
        replacement: Optional[str] = None,
    ) -> Rule:
        """
        便捷方法：创建规则对象

        Args:
            name: 规则名称
            pattern: 正则表达式
            description: 规则描述
            enabled: 是否启用
            mode: 脱敏模式
            priority: 优先级
            replacement: 替换文本

        Returns:
            Rule: 规则对象
        """
        return Rule(
            name=name,
            pattern=pattern,
            description=description,
            enabled=enabled,
            mode=mode,
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
