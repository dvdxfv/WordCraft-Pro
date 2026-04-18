"""
QA 智能分析

利用 LLM 对 QA 检查结果进行智能分析和修复建议。
"""

from __future__ import annotations

from typing import Optional

from llm.client import LLMClient, ChatMessage
from core.qa_models import QAReport, QAIssue, IssueCategory, IssueSeverity


QA_ANALYSIS_PROMPT = """你是一个专业的文档质量检查助手。我会给你一份文档的质量检查报告，请你：

1. 总结文档整体质量状况
2. 对每个问题给出具体的修改建议（包括修改后的文本）
3. 按优先级排序（先处理错误，再处理警告）

请用以下 JSON 格式输出：
{
  "summary": "整体质量评价（1-2句话）",
  "score": 85,
  "prioritized_issues": [
    {
      "original": "原文中的问题文本",
      "suggested": "建议修改为的文本",
      "reason": "修改原因"
    }
  ]
}
"""

CROSSREF_ANALYSIS_PROMPT = """你是一个专业的学术文档交叉引用检查助手。我会给你一份交叉引用检查报告，请你：

1. 检查是否有悬空引用（引用了不存在的目标）
2. 检查是否有未被引用的目标
3. 给出修复建议

请用以下 JSON 格式输出：
{
  "summary": "交叉引用状况总结",
  "actions": [
    {
      "type": "fix_dangling|add_reference|remove_duplicate",
      "detail": "具体操作说明"
    }
  ]
}
"""


class QAAnalyzer:
    """QA 智能分析器"""

    def __init__(self, client: LLMClient):
        self._client = client

    def analyze(self, report: QAReport, doc_text: str = "") -> dict:
        """
        对 QA 报告进行智能分析。

        Args:
            report: QA 检查报告
            doc_text: 可选的文档全文（用于上下文）

        Returns:
            分析结果字典
        """
        # 构建问题描述
        issues_desc = []
        for i, issue in enumerate(report.issues):
            issues_desc.append(
                f"{i + 1}. [{issue.severity.value}] {issue.title}\n"
                f"   位置: {issue.location_text or '未知'}\n"
                f"   描述: {issue.description or '无'}\n"
                f"   建议: {issue.suggestion or '无'}"
            )

        issues_text = "\n".join(issues_desc) if issues_desc else "未发现问题。"

        # 限制文档文本长度
        doc_context = ""
        if doc_text:
            doc_context = f"\n\n文档内容（节选）:\n{doc_text[:3000]}"

        user_message = (
            f"质量检查报告：\n"
            f"共 {report.total} 个问题（错误: {report.error_count}, "
            f"警告: {report.warning_count}, 提示: {report.info_count}）\n\n"
            f"问题详情:\n{issues_text}{doc_context}"
        )

        messages = [
            ChatMessage(role="system", content=QA_ANALYSIS_PROMPT),
            ChatMessage(role="user", content=user_message),
        ]

        return self._client.chat_json(messages, temperature=0.3)

    def analyze_crossref(self, crossref_summary: str) -> dict:
        """
        对交叉引用报告进行智能分析。

        Args:
            crossref_summary: 交叉引用报告摘要文本

        Returns:
            分析结果字典
        """
        messages = [
            ChatMessage(role="system", content=CROSSREF_ANALYSIS_PROMPT),
            ChatMessage(role="user", content=f"交叉引用检查报告：\n{crossref_summary}"),
        ]

        return self._client.chat_json(messages, temperature=0.3)

    def suggest_fix(self, issue: QAIssue, context: str = "") -> str:
        """
        对单个问题给出修复建议。

        Args:
            issue: QA 问题
            context: 所在段落上下文

        Returns:
            修复建议文本
        """
        messages = [
            ChatMessage(role="system", content="你是一个文档校对专家。请给出具体的修改建议，直接输出修改后的文本。"),
            ChatMessage(role="user", content=(
                f"问题：{issue.title}\n"
                f"描述：{issue.description}\n"
                f"位置文本：{issue.location_text}\n"
                f"上下文：{context}\n\n"
                f"请给出修改建议。"
            )),
        ]

        return self._client.chat(messages, temperature=0.3)
