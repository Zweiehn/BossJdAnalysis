"""优先级规则管理 - 用户自定义分组+AI自动评判优先级"""

import os
import json
from config import get_app_dir, Config

RULES_FILE = "priority_rules.json"

# 默认规则（空分组，用户自行添加）
DEFAULT_RULES = {
    "groups": [],
    "default_level": "观望",
}


class PriorityManager:
    """优先级规则管理器"""

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def _get_rules_path(self) -> str:
        return os.path.join(get_app_dir(), RULES_FILE)

    def load_rules(self) -> dict:
        """加载优先级规则"""
        path = self._get_rules_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return dict(DEFAULT_RULES)

    def save_rules(self, rules: dict):
        """保存优先级规则"""
        path = self._get_rules_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)

    def has_rules(self) -> bool:
        """是否有已配置的分组规则"""
        rules = self.load_rules()
        return len(rules.get("groups", [])) > 0

    def get_groups(self) -> list:
        """获取所有优先级分组"""
        return self.load_rules().get("groups", [])

    def build_priority_prompt(self, level_field: str = "优先级") -> str:
        """
        构建优先级评判 Prompt，附加到 AI system prompt 中

        Returns:
            空字符串 = 无规则 / 否则返回评判指令
        """
        groups = self.get_groups()
        if not groups:
            return ""

        lines = [
            f"\n## 优先级评判（字段名: {level_field}）",
            "请根据以下分组规则，判断该JD的优先级级别：",
            "可选值: 优先, 观望, 谨慎, 排除",
            "评分标准：匹配任一分组的所有条件 → 该组的优先级级别",
            "如不匹配任何分组 → 使用「观望」级别",
            "",
            "### 优先级分组定义：",
        ]

        for idx, g in enumerate(groups, 1):
            name = g.get("name", f"分组{idx}")
            level = g.get("level", "观望")
            logic = g.get("logic", "and")
            lines.append(f"\n  [{idx}] {name} → 级别: {level}")
            for rule in g.get("rules", []):
                field = rule.get("field", "")
                op = rule.get("operator", "==")
                val = rule.get("value", "")
                lines.append(f"      条件: {field} {op} {val}")
            lines.append(f"      逻辑: 所有条件需{'全部满足(AND)' if logic == 'and' else '任一满足(OR)'}")

        lines.append(f"\n在输出的JSON中，添加字段 '{level_field}'，填入评判结果。")
        lines.append("同时在「个人备注」中简要说明该JD列入此优先级的原因。")
        return "\n".join(lines)

    def get_summary(self) -> str:
        """获取规则概要（用于界面显示）"""
        groups = self.get_groups()
        if not groups:
            return "未配置优先级分组"
        parts = [f"{len(groups)}个分组"]
        for g in groups:
            parts.append(f"{g.get('name','?')}({g.get('level','?')})")
        return " | ".join(parts)

    def clear_rules(self):
        """清除所有规则"""
        self.save_rules(dict(DEFAULT_RULES))
