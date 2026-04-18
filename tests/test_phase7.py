"""
Phase 7 单元测试

测试 LLM 客户端、NL 规则解析器、QA 分析器（使用 MockLLMClient）。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.document_model import DocumentModel, DocElement, ElementType
from core.formatting_rules import FormattingRules, StyleRules, PageRules
from core.qa_models import QAReport, QAIssue, IssueCategory, IssueSeverity
from llm.client import (
    LLMClient, LLMConfig, DoubaoClient, MockLLMClient,
    create_llm_client, ChatMessage,
)
from llm.nl_rule_parser import NLRuleParser
from llm.qa_analyzer import QAAnalyzer


# ============================================================
# 测试 LLM 配置
# ============================================================

class TestLLMConfig:

    def test_default_config(self):
        config = LLMConfig()
        assert config.provider == "doubao"
        assert config.model == "Doubao-Seed-1.6"
        assert config.base_url == "https://ark.cn-beijing.volces.com/api/v3"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096

    def test_config_from_yaml(self):
        config = LLMConfig.from_yaml(
            os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        )
        assert config.provider == "doubao"
        assert config.api_key == "d9523eb2-f741-4122-ab0f-e6ed95ce59f2"
        assert config.model == "Doubao-Seed-1.6"


# ============================================================
# 测试 MockLLMClient
# ============================================================

class TestMockLLMClient:

    def test_chat(self):
        client = MockLLMClient()
        result = client.chat([
            ChatMessage(role="user", content="你好"),
        ])
        assert result == "模拟回复"
        assert client.call_count == 1

    def test_chat_json(self):
        client = MockLLMClient()
        result = client.chat_json([
            ChatMessage(role="system", content="返回JSON"),
            ChatMessage(role="user", content="排版需求：A4纸，黑体三号标题"),
        ])
        assert "page" in result
        assert "heading1" in result

    def test_is_available(self):
        client = MockLLMClient()
        assert client.is_available() is True


# ============================================================
# 测试工厂方法
# ============================================================

class TestCreateLLMClient:

    def test_create_with_api_key(self):
        config = LLMConfig(api_key="test-key")
        client = create_llm_client(config)
        assert isinstance(client, DoubaoClient)

    def test_create_without_api_key(self):
        config = LLMConfig(api_key="")
        client = create_llm_client(config)
        assert isinstance(client, MockLLMClient)

    def test_create_from_config_path(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
        client = create_llm_client(config_path=config_path)
        assert isinstance(client, DoubaoClient)


# ============================================================
# 测试 NL 规则解析器
# ============================================================

class TestNLRuleParser:

    def test_parse_with_mock(self):
        """使用 MockLLMClient 测试解析"""
        client = MockLLMClient()
        parser = NLRuleParser(client)

        rules = parser.parse("论文用A4纸，一级标题黑体三号居中，正文宋体小四号首行缩进2字符。")

        assert isinstance(rules, FormattingRules)
        assert rules.page.paper_size == "A4"
        assert rules.heading1 is not None
        assert rules.heading1.font_name_cn == "黑体"
        assert rules.body is not None
        assert rules.body.font_name_cn == "宋体"

    def test_parse_result_serialization(self):
        """解析结果可以序列化为 YAML"""
        client = MockLLMClient()
        parser = NLRuleParser(client)

        rules = parser.parse("A4纸，上下边距2.5cm。")
        yaml_text = rules.to_yaml()
        assert "A4" in yaml_text
        assert "2.5" in yaml_text

    def test_refine_rules(self):
        """测试规则调整"""
        client = MockLLMClient()
        parser = NLRuleParser(client)

        initial = FormattingRules(
            heading1=StyleRules(font_name_cn="黑体", font_size_pt=16),
        )
        # MockLLMClient 的 refine 不会真正修改，但应该返回 FormattingRules
        result = parser.refine_rules(initial, "标题改为宋体")
        assert isinstance(result, FormattingRules)

    def test_to_formatting_rules(self):
        """测试 JSON → FormattingRules 转换"""
        data = {
            "page": {"paper_size": "A4", "margin_top_cm": 2.5},
            "heading1": {"font_name_cn": "黑体", "font_size_pt": 16, "bold": True},
            "body": {"font_name_cn": "宋体", "font_size_pt": 12, "first_indent_chars": 2},
        }
        rules = NLRuleParser._to_formatting_rules(data)
        assert rules.page.paper_size == "A4"
        assert rules.page.margin_top_cm == 2.5
        assert rules.heading1.font_name_cn == "黑体"
        assert rules.body.first_indent_chars == 2


# ============================================================
# 测试 QA 分析器
# ============================================================

class TestQAAnalyzer:

    def test_analyze_with_mock(self):
        """使用 MockLLMClient 测试 QA 分析"""
        client = MockLLMClient()
        analyzer = QAAnalyzer(client)

        report = QAReport()
        report.add_issue(QAIssue(
            category=IssueCategory.TYPO,
            severity=IssueSeverity.ERROR,
            title='错别字：帐号→账号',
            description='文中使用了"帐号"，应为"账号"',
            location_text="帐号",
        ))

        result = analyzer.analyze(report)
        assert isinstance(result, dict)
        assert "summary" in result

    def test_analyze_crossref(self):
        """测试交叉引用分析"""
        client = MockLLMClient()
        analyzer = QAAnalyzer(client)

        result = analyzer.analyze_crossref(
            "引用目标: 2个 | 引用点: 3个 | 悬空引用: 1个"
        )
        assert isinstance(result, dict)

    def test_suggest_fix(self):
        """测试单问题修复建议"""
        client = MockLLMClient()
        analyzer = QAAnalyzer(client)

        issue = QAIssue(
            category=IssueCategory.TYPO,
            severity=IssueSeverity.WARNING,
            title="的/地/得用法",
            location_text="认真的完成",
        )
        suggestion = analyzer.suggest_fix(issue, "他认真的完成了任务")
        assert isinstance(suggestion, str)
        assert len(suggestion) > 0


# ============================================================
# 测试 ChatMessage
# ============================================================

class TestChatMessage:

    def test_create_message(self):
        msg = ChatMessage(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"

    def test_message_to_dict(self):
        msg = ChatMessage(role="system", content="你是助手")
        assert msg.role == "system"


# ============================================================
# 测试 DoubaoClient 初始化
# ============================================================

class TestDoubaoClient:

    def test_init_with_config(self):
        config = LLMConfig(
            api_key="test-key",
            model="Doubao-Seed-1.6",
        )
        client = DoubaoClient(config)
        assert client.is_available() is True

    def test_init_without_key(self):
        config = LLMConfig(api_key="")
        client = DoubaoClient(config)
        assert client.is_available() is False

    def test_parse_json_with_code_block(self):
        """测试 JSON 解析（含 markdown 代码块）"""
        text = '```json\n{"key": "value"}\n```'
        result = DoubaoClient._parse_json(text)
        assert result["key"] == "value"

    def test_parse_json_with_surrounding_text(self):
        """测试 JSON 解析（含前后文字）"""
        text = '以下是结果：{"page": "A4"}。结束'
        result = DoubaoClient._parse_json(text)
        assert result["page"] == "A4"

    def test_parse_json_invalid(self):
        """测试无效 JSON 解析"""
        text = "这不是JSON"
        result = DoubaoClient._parse_json(text)
        assert "raw" in result


# ============================================================
# 测试端到端（Mock LLM 全流程）
# ============================================================

class TestLLMEndToEnd:

    def test_nl_parse_to_format_to_export(self):
        """NL 解析 → 排版 → 导出"""
        import tempfile

        # 1. NL 解析
        client = MockLLMClient()
        parser = NLRuleParser(client)
        rules = parser.parse("A4纸，标题黑体三号居中，正文宋体小四号。")

        # 2. 创建文档并排版
        from core.document_model import FontStyle, ParagraphStyle, Alignment
        from core.formatter import Formatter

        doc = DocumentModel(title="测试")
        doc.elements.append(DocElement(
            element_type=ElementType.HEADING,
            content="第一章 绪论",
            level=1,
        ))
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="这是正文内容。",
        ))

        formatted = Formatter(rules).apply(doc)
        assert formatted is not None

        # 3. 导出
        from core.exporter import Exporter
        fd, path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        try:
            Exporter().export(formatted, path)
            assert os.path.isfile(path)
            assert os.path.getsize(path) > 500
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_qa_with_llm_analysis(self):
        """QA 检查 + LLM 分析"""
        from core.qa_engine import QAEngine

        doc = DocumentModel(title="测试")
        doc.elements.append(DocElement(
            element_type=ElementType.PARAGRAPH,
            content="请输入正确的帐号进行登录。",
        ))

        # QA 检查
        report = QAEngine().check(doc)
        assert report.total >= 1

        # LLM 分析
        client = MockLLMClient()
        analyzer = QAAnalyzer(client)
        analysis = analyzer.analyze(report)
        assert "summary" in analysis


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
