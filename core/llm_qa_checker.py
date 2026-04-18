"""
LLM 辅助质量检测模块

利用大语言模型进行深度语义分析，检测：
1. 上下文相关错别字（同音异形词、语境误用）
2. 语法错误（成分残缺、语序不当、搭配错误）
3. 逻辑问题（语义矛盾、论证不充分、概念混淆）
4. 专业术语和格式规范

技术架构：
- 分层处理：规则引擎 → LLM 增强 → 结果整合
- 分块检测：长文档按语义分块，避免超出上下文窗口
- JSON 结构化输出：便于前端展示和定位
"""

from __future__ import annotations

import json
import re
import time
import traceback
from typing import Optional

from core.document_model import DocumentModel, DocElement, ElementType
from core.qa_models import QAReport, QAIssue, IssueCategory, IssueSeverity
from llm.client import LLMClient, ChatMessage, create_llm_client, LLMConfig


# ============================================================
# Prompt 模板
# 注意：JSON 示例中的花括号需要双写（{{}}）以避免被 format() 解析
# ============================================================

TYPO_CHECK_PROMPT = """你是一个专业的中文文档错别字检测专家。请仔细检查以下文本，找出所有可能的错别字和用词错误。

检测范围：
1. 常见错别字（如"帐号"→"账号"、"按装"→"安装"）
2. 的/地/得误用
3. 同音异形词误用（根据上下文判断正确用词）
4. 成语错字（如"穿流不息"→"川流不息"）
5. 专业术语错字

重要规则：
- 只报告确实有问题的地方，不要误报
- 考虑上下文语义，避免机械匹配
- 对于"的/地/得"，只在明显错误时才报告
- 如果文本本身是正确的（如引用古文），不要报告

请用严格的 JSON 格式输出（不要包含 markdown 代码块标记），格式为：
{{"issues": [{{"text": "错误片段", "suggestion": "建议修改为", "reason": "错误原因", "confidence": 0.9}}]}}

如果没有发现问题，输出：{{"issues": []}}

待检查文本：
{text}
"""

GRAMMAR_CHECK_PROMPT = """你是一个专业的中文语法检查专家。请仔细检查以下文本，找出所有语法错误和表达问题。

检测范围：
1. 成分残缺（缺主语、缺谓语、缺宾语）
2. 搭配不当（主谓搭配、动宾搭配、修饰语搭配）
3. 语序不当（修饰语位置、状语位置）
4. 句式杂糅（两种句式混用）
5. 重复啰嗦（同义反复、冗余表达）
6. 标点符号错误（特别是逗号、句号、顿号的使用）

重要规则：
- 只报告确实有语法问题的地方
- 不要报告风格偏好问题（如"建议改为更简洁的表达"）
- 置信度低于 0.6 的问题不要报告
- 对于口语化表达，如果语法正确则不要报告

请用严格的 JSON 格式输出（不要包含 markdown 代码块标记），格式为：
{{"issues": [{{"text": "问题片段", "suggestion": "建议修改为", "reason": "问题类型和原因", "confidence": 0.8}}]}}

如果没有发现问题，输出：{{"issues": []}}

待检查文本：
{text}
"""

LOGIC_CHECK_PROMPT = """你是一个专业的文档逻辑分析专家。请仔细检查以下文本，找出所有逻辑问题和语义矛盾。

检测范围：
1. 前后矛盾（同一概念的不同表述互相矛盾）
2. 数值矛盾（数据之间的逻辑矛盾）
3. 因果断裂（"因为...所以..."逻辑不成立）
4. 概念混淆（混淆相似概念）
5. 论证跳跃（结论缺乏中间推导）
6. 时间线矛盾（时间顺序不合理）

重要规则：
- 只报告确实有逻辑问题的地方
- 不要报告主观判断（如"这个观点我不认同"）
- 考虑文档类型（公文、论文、报告有不同的逻辑要求）
- 置信度低于 0.6 的问题不要报告

请用严格的 JSON 格式输出（不要包含 markdown 代码块标记），格式为：
{{"issues": [{{"text": "问题片段", "suggestion": "建议修改或补充", "reason": "逻辑问题说明", "confidence": 0.7}}]}}

如果没有发现问题，输出：{{"issues": []}}

待检查文本：
{text}
"""

COMPREHENSIVE_CHECK_PROMPT = """你是一个专业的文档质量检查专家，擅长综合检测各类文档问题。请仔细检查以下文本，找出所有需要修正的地方。

检测范围（按优先级排序）：
1. 【错误】错别字、用词错误、成语错字
2. 【错误】严重语法错误（成分残缺、搭配不当）
3. 【警告】轻度语法问题（语序不当、句式杂糅）
4. 【警告】逻辑问题（前后矛盾、数值矛盾）
5. 【提示】表达优化建议（重复啰嗦、可更精炼）
6. 【提示】标点符号优化

重要规则：
- 每个问题必须标注严重程度：error / warning / info
- 只报告确实有问题的地方，避免误报
- 置信度低于 0.6 的问题不要报告
- 对于每个问题，给出具体的原文片段和修改建议

请用严格的 JSON 格式输出（不要包含 markdown 代码块标记），格式为：
{{"issues": [{{"text": "问题片段", "suggestion": "建议修改为", "reason": "问题说明", "severity": "error", "category": "typo", "confidence": 0.9}}]}}

severity 可选值：error / warning / info
category 可选值：typo / grammar / logic / style / punctuation

如果没有发现问题，输出：{{"issues": []}}

待检查文本：
{text}
"""


class LLMQAChecker:
    """LLM 辅助质量检测器

    利用大语言模型进行深度语义分析，弥补纯规则检测的不足。
    支持错别字、语法、逻辑、综合检测等多个维度。
    """

    def __init__(self, client: Optional[LLMClient] = None, config: Optional[dict] = None):
        """初始化 LLM QA 检测器

        Args:
            client: LLM 客户端实例，如果为 None 则自动创建
            config: 配置字典，包含检测开关和参数
        """
        self._client = client
        self._config = config or {}
        self.enabled = self._config.get("enabled", True)
        self.max_chunk_size = self._config.get("max_chunk_size", 800)
        self.min_confidence = self._config.get("min_confidence", 0.6)
        self.timeout_seconds = self._config.get("timeout_seconds", 30)

    def _ensure_client(self) -> Optional[LLMClient]:
        """确保 LLM 客户端已初始化"""
        if self._client is not None:
            return self._client

        # 尝试从配置文件加载
        config_path = self._config.get("config_path", "config.yaml")
        try:
            llm_config = LLMConfig.from_yaml(config_path)
            self._client = create_llm_client(llm_config)
            return self._client
        except Exception as e:
            print(f"[LLM QA] 初始化 LLM 客户端失败: {e}")
            return None

    def check_typo(self, doc: DocumentModel) -> QAReport:
        """执行 LLM 错别字检测

        Args:
            doc: 文档模型

        Returns:
            QAReport: 检测报告
        """
        report = QAReport()
        client = self._ensure_client()
        if not client or not client.is_available():
            return report

        chunks = self._split_text(doc)
        for chunk_text, start_elem_idx in chunks:
            try:
                issues = self._call_llm(TYPO_CHECK_PROMPT.format(text=chunk_text), client)
                for issue_data in issues:
                    confidence = issue_data.get("confidence", 0.7)
                    if confidence < self.min_confidence:
                        continue

                    issue = QAIssue(
                        category=IssueCategory.TYPO,
                        severity=IssueSeverity.WARNING,
                        title=f"疑似错别字：\"{issue_data['text']}\"",
                        description=issue_data.get("reason", ""),
                        suggestion=issue_data.get("suggestion", ""),
                        element_index=start_elem_idx,
                        element_type="paragraph",
                        location_text=issue_data["text"],
                        confidence=confidence,
                    )
                    report.add_issue(issue)
            except Exception as e:
                print(f"[LLM QA] 错别字检测失败: {e}")
                print(f"[LLM QA] 错误详情: {traceback.format_exc()}")

        return report

    def check_grammar(self, doc: DocumentModel) -> QAReport:
        """执行 LLM 语法检测

        Args:
            doc: 文档模型

        Returns:
            QAReport: 检测报告
        """
        report = QAReport()
        client = self._ensure_client()
        if not client or not client.is_available():
            return report

        chunks = self._split_text(doc)
        for chunk_text, start_elem_idx in chunks:
            try:
                issues = self._call_llm(GRAMMAR_CHECK_PROMPT.format(text=chunk_text), client)
                for issue_data in issues:
                    confidence = issue_data.get("confidence", 0.7)
                    if confidence < self.min_confidence:
                        continue

                    issue = QAIssue(
                        category=IssueCategory.GRAMMAR,
                        severity=IssueSeverity.WARNING,
                        title=f"语法问题：{issue_data.get('reason', '表达欠妥')}",
                        description=f"原文：\"{issue_data['text']}\"",
                        suggestion=issue_data.get("suggestion", ""),
                        element_index=start_elem_idx,
                        element_type="paragraph",
                        location_text=issue_data["text"],
                        confidence=confidence,
                    )
                    report.add_issue(issue)
            except Exception as e:
                print(f"[LLM QA] 语法检测失败: {e}")
                print(f"[LLM QA] 错误详情: {traceback.format_exc()}")

        return report

    def check_logic(self, doc: DocumentModel) -> QAReport:
        """执行 LLM 逻辑检测

        Args:
            doc: 文档模型

        Returns:
            QAReport: 检测报告
        """
        report = QAReport()
        client = self._ensure_client()
        if not client or not client.is_available():
            return report

        chunks = self._split_text(doc, merge_paragraphs=True)
        for chunk_text, start_elem_idx in chunks:
            try:
                issues = self._call_llm(LOGIC_CHECK_PROMPT.format(text=chunk_text), client)
                for issue_data in issues:
                    confidence = issue_data.get("confidence", 0.7)
                    if confidence < self.min_confidence:
                        continue

                    issue = QAIssue(
                        category=IssueCategory.LOGIC,
                        severity=IssueSeverity.WARNING,
                        title=f"逻辑问题：{issue_data.get('reason', '逻辑欠妥')}",
                        description=f"原文：\"{issue_data['text']}\"",
                        suggestion=issue_data.get("suggestion", ""),
                        element_index=start_elem_idx,
                        element_type="paragraph",
                        location_text=issue_data["text"],
                        confidence=confidence,
                    )
                    report.add_issue(issue)
            except Exception as e:
                print(f"[LLM QA] 逻辑检测失败: {e}")
                print(f"[LLM QA] 错误详情: {traceback.format_exc()}")

        return report

    def check_comprehensive(self, doc: DocumentModel) -> QAReport:
        """执行综合检测（一次调用检测所有类型）

        Args:
            doc: 文档模型

        Returns:
            QAReport: 检测报告
        """
        report = QAReport()
        client = self._ensure_client()
        if not client or not client.is_available():
            return report

        chunks = self._split_text(doc)
        severity_map = {
            "error": IssueSeverity.ERROR,
            "warning": IssueSeverity.WARNING,
            "info": IssueSeverity.INFO,
        }
        category_map = {
            "typo": IssueCategory.TYPO,
            "grammar": IssueCategory.GRAMMAR,
            "logic": IssueCategory.LOGIC,
            "style": IssueCategory.STYLE,
            "punctuation": IssueCategory.FORMAT,
        }

        for chunk_text, start_elem_idx in chunks:
            try:
                issues = self._call_llm(
                    COMPREHENSIVE_CHECK_PROMPT.format(text=chunk_text),
                    client,
                )
                for issue_data in issues:
                    confidence = issue_data.get("confidence", 0.7)
                    if confidence < self.min_confidence:
                        continue

                    severity_str = issue_data.get("severity", "warning")
                    severity = severity_map.get(severity_str, IssueSeverity.WARNING)

                    category_str = issue_data.get("category", "typo")
                    category = category_map.get(category_str, IssueCategory.TYPO)

                    issue = QAIssue(
                        category=category,
                        severity=severity,
                        title=f"{category_str}：{issue_data.get('reason', '需要修改')}",
                        description=f"原文：\"{issue_data['text']}\"",
                        suggestion=issue_data.get("suggestion", ""),
                        element_index=start_elem_idx,
                        element_type="paragraph",
                        location_text=issue_data["text"],
                        confidence=confidence,
                    )
                    report.add_issue(issue)
            except Exception as e:
                print(f"[LLM QA] 综合检测失败: {e}")
                print(f"[LLM QA] 错误详情: {traceback.format_exc()}")

        return report

    def check_enhanced(self, doc: DocumentModel, base_report: QAReport) -> QAReport:
        """增强检测：在规则引擎基础上用 LLM 补充检测

        Args:
            doc: 文档模型
            base_report: 规则引擎的检测结果

        Returns:
            QAReport: 合并后的检测报告
        """
        llm_report = self.check_comprehensive(doc)

        merged = QAReport()
        for issue in base_report.issues:
            merged.add_issue(issue)
        for issue in llm_report.issues:
            if not self._is_duplicate(issue, merged):
                merged.add_issue(issue)

        return merged

    def _split_text(
        self,
        doc: DocumentModel,
        merge_paragraphs: bool = False,
    ) -> list[tuple[str, int]]:
        """将文档分块

        Args:
            doc: 文档模型
            merge_paragraphs: 是否合并段落（适合逻辑检测）

        Returns:
            [(文本块, 起始元素索引)]
        """
        if merge_paragraphs:
            text_parts = []
            for elem in doc.elements:
                if elem.content:
                    text_parts.append(elem.content)
            full_text = "\n".join(text_parts)
            chunks = self._chunk_text(full_text, self.max_chunk_size)
            return [(chunk, 0) for chunk in chunks]

        chunks = []
        current_text = ""
        current_start_idx = 0

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue
            if len(current_text) + len(elem.content) > self.max_chunk_size and current_text:
                chunks.append((current_text.strip(), current_start_idx))
                current_text = elem.content
                current_start_idx = idx
            else:
                if not current_text:
                    current_start_idx = idx
                current_text += elem.content + "\n"

        if current_text.strip():
            chunks.append((current_text.strip(), current_start_idx))

        return chunks

    def _chunk_text(self, text: str, max_size: int) -> list[str]:
        """将长文本按语义边界分块

        Args:
            text: 完整文本
            max_size: 最大块大小

        Returns:
            文本块列表
        """
        if len(text) <= max_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + max_size
            if end >= len(text):
                chunks.append(text[start:])
                break

            # 优先在段落边界分割
            best_split = end
            for i in range(min(200, end - start)):
                pos = end - i
                if pos < start + max_size // 2:
                    break
                if text[pos:pos + 2] == "\n\n":
                    best_split = pos + 2
                    break
                elif text[pos] in ("。", "！", "？", "\n"):
                    best_split = pos + 1

            chunks.append(text[start:best_split].strip())
            start = best_split

        return chunks

    def _call_llm(self, prompt: str, client: LLMClient) -> list[dict]:
        """调用 LLM 并解析 JSON 结果

        Args:
            prompt: 完整 prompt
            client: LLM 客户端

        Returns:
            问题列表
        """
        messages = [ChatMessage(role="user", content=prompt)]
        try:
            result_text = client.chat(messages, temperature=0.1)
            # 解析 JSON
            parsed = self._parse_json_result(result_text)
            return parsed.get("issues", [])
        except Exception as e:
            print(f"[LLM QA] LLM 调用失败: {e}")
            return []

    def _parse_json_result(self, text: str) -> dict:
        """从 LLM 返回中提取 JSON

        Args:
            text: LLM 返回文本

        Returns:
            解析后的 JSON 字典
        """
        text = text.strip()

        # 移除 markdown 代码块标记
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text, flags=re.MULTILINE)
            text = re.sub(r"\s*```\s*$", "", text)

        # 尝试直接解析
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass

        # 提取 JSON 对象（支持嵌套花括号）
        brace_count = 0
        start = -1
        for i, char in enumerate(text):
            if char == '{':
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start >= 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except (json.JSONDecodeError, ValueError):
                        pass

        # 解析失败，返回空结果
        return {"issues": []}

    def _is_duplicate(self, new_issue: QAIssue, report: QAReport) -> bool:
        """检查问题是否与已有问题重复

        Args:
            new_issue: 新问题
            report: 已有报告

        Returns:
            是否重复
        """
        new_text = new_issue.location_text or ""
        for existing in report.issues:
            existing_text = existing.location_text or ""
            # 文本相似度检测（简化版）
            if self._text_similarity(new_text, existing_text) > 0.8:
                return True
        return False

    @staticmethod
    def _text_similarity(s1: str, s2: str) -> float:
        """计算两个字符串的相似度

        Args:
            s1: 字符串1
            s2: 字符串2

        Returns:
            相似度（0-1）
        """
        if not s1 or not s2:
            return 0.0

        set1 = set(s1)
        set2 = set(s2)
        intersection = set1 & set2
        union = set1 | set2

        if not union:
            return 0.0

        return len(intersection) / len(union)
