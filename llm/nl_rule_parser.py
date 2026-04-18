"""
NL → 排版规则解析器

利用 LLM 将用户的自然语言排版需求转换为结构化的 FormattingRules。
"""

from __future__ import annotations

import json
from typing import Optional

from llm.client import LLMClient, ChatMessage
from core.formatting_rules import FormattingRules, StyleRules, PageRules


SYSTEM_PROMPT = """你是一个专业的文档排版规则解析助手。用户会用自然语言描述排版需求，你需要将其转换为结构化的 JSON 格式。

输出格式要求：
1. 必须返回合法的 JSON
2. 不要输出任何 JSON 之外的文字
3. 使用以下结构：

{
  "page": {
    "paper_size": "A4",
    "margin_top_cm": 2.5,
    "margin_bottom_cm": 2.5,
    "margin_left_cm": 3.0,
    "margin_right_cm": 2.5
  },
  "heading1": {
    "font_name_cn": "黑体",
    "font_size_pt": 16,
    "bold": true,
    "alignment": "center"
  },
  "heading2": {
    "font_name_cn": "黑体",
    "font_size_pt": 14,
    "bold": true
  },
  "heading3": {
    "font_name_cn": "黑体",
    "font_size_pt": 12,
    "bold": true
  },
  "body": {
    "font_name_cn": "宋体",
    "font_size_pt": 12,
    "first_indent_chars": 2,
    "line_spacing_value": 1.5
  },
  "table_caption": {
    "font_name_cn": "黑体",
    "font_size_pt": 10.5,
    "alignment": "center"
  },
  "figure_caption": {
    "font_name_cn": "黑体",
    "font_size_pt": 10.5,
    "alignment": "center"
  },
  "reference": {
    "font_name_cn": "宋体",
    "font_size_pt": 10.5
  }
}

注意：
- 只输出用户明确提到的字段，未提到的不要输出
- alignment 可选值: left, center, right, justify
- 如果用户提到中文字号（如"三号"），请转换为磅值（三号=16pt）
- paper_size 可选值: A4, A3, B5, Letter
"""

EXAMPLE_PROMPT = """用户示例：
"论文用A4纸，上下左右边距分别是2.5cm、2.5cm、3cm、2.5cm。一级标题黑体三号居中，正文宋体小四号首行缩进2字符，1.5倍行距。"

正确输出：
{"page":{"paper_size":"A4","margin_top_cm":2.5,"margin_bottom_cm":2.5,"margin_left_cm":3.0,"margin_right_cm":2.5},"heading1":{"font_name_cn":"黑体","font_size_pt":16,"bold":true,"alignment":"center"},"body":{"font_name_cn":"宋体","font_size_pt":12,"first_indent_chars":2,"line_spacing_value":1.5}}
"""


class NLRuleParser:
    """自然语言排版规则解析器"""

    def __init__(self, client: LLMClient):
        self._client = client

    def parse(self, user_input: str) -> FormattingRules:
        """
        将自然语言排版需求转换为 FormattingRules。

        Args:
            user_input: 用户的自然语言描述

        Returns:
            FormattingRules 对象
        """
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=EXAMPLE_PROMPT),
            ChatMessage(role="assistant", content='{"page":{"paper_size":"A4","margin_top_cm":2.5,"margin_bottom_cm":2.5,"margin_left_cm":3.0,"margin_right_cm":2.5},"heading1":{"font_name_cn":"黑体","font_size_pt":16,"bold":true,"alignment":"center"},"body":{"font_name_cn":"宋体","font_size_pt":12,"first_indent_chars":2,"line_spacing_value":1.5}}'),
            ChatMessage(role="user", content=user_input),
        ]

        result = self._client.chat_json(messages, temperature=0.1)
        return self._to_formatting_rules(result)

    def refine_rules(self, current_rules: FormattingRules,
                     user_feedback: str) -> FormattingRules:
        """
        根据用户反馈调整排版规则。

        Args:
            current_rules: 当前排版规则
            user_feedback: 用户的修改意见

        Returns:
            调整后的 FormattingRules
        """
        current_json = current_rules.to_dict()

        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"当前规则：{json.dumps(current_json, ensure_ascii=False)}\n\n用户修改意见：{user_feedback}\n\n请输出修改后的完整规则JSON。"),
        ]

        result = self._client.chat_json(messages, temperature=0.1)
        return self._to_formatting_rules(result)

    @staticmethod
    def _to_formatting_rules(data: dict) -> FormattingRules:
        """将 JSON 字典转换为 FormattingRules"""
        rules = FormattingRules()

        # 页面设置
        if "page" in data:
            page_data = data["page"]
            if "paper_size" in page_data:
                rules.page.paper_size = page_data["paper_size"]
            for key in ["margin_top_cm", "margin_bottom_cm", "margin_left_cm",
                        "margin_right_cm", "gutter_cm"]:
                if key in page_data:
                    setattr(rules.page, key, page_data[key])

        # 样式规则映射
        style_map = {
            "heading1": "heading1",
            "heading2": "heading2",
            "heading3": "heading3",
            "heading4": "heading4",
            "body": "body",
            "table_caption": "table_caption",
            "figure_caption": "figure_caption",
            "reference": "reference",
            "title": "title",
        }

        for json_key, rule_attr in style_map.items():
            if json_key in data:
                style_data = data[json_key]
                style = StyleRules.from_dict(style_data)
                setattr(rules, rule_attr, style)

        return rules
