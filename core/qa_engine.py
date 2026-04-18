"""
质量检查引擎 (QA Engine)

统一调度错别字检查、数据一致性检查、逻辑检查、交叉引用检查。
支持长文分块处理和性能优化。
支持 LLM 辅助检测（深度语义分析）。
"""

from __future__ import annotations

import time
from typing import Optional

from core.document_model import DocumentModel
from core.qa_models import QAReport, QAIssue, IssueCategory
from core.typo_checker import TypoChecker
from core.consistency_checker import ConsistencyChecker
from core.logic_checker import LogicChecker
from core.crossref_checker import CrossRefChecker
from core.performance import get_optimizer, get_async_checker


class QAEngine:
    """质量检查引擎"""

    def __init__(self, config: dict = None):
        config = config or {}
        qa_config = config.get("qa", {})

        # 性能优化配置
        perf_config = config.get("performance", {})
        self.enable_chunking = perf_config.get("enable_chunking", True)
        self.chunk_size = perf_config.get("chunk_size", 1000)
        self.enable_cache = perf_config.get("enable_cache", True)
        
        # 初始化优化器
        if self.enable_chunking:
            self.optimizer = get_optimizer(self.chunk_size)
            self.async_checker = get_async_checker()
        else:
            self.optimizer = None
            self.async_checker = None

        # 初始化各检查器
        typo_config = qa_config.get("typo_check", {})
        self.typo_checker = TypoChecker()
        self.typo_checker.enabled = typo_config.get("enabled", True)
        self.typo_checker.use_llm = typo_config.get("use_llm", True)

        consistency_config = qa_config.get("consistency_check", {})
        self.consistency_checker = ConsistencyChecker()
        self.consistency_checker.enabled = consistency_config.get("enabled", True)
        self.consistency_checker.check_numbers = consistency_config.get("check_numbers", True)
        self.consistency_checker.check_dates = consistency_config.get("check_dates", True)
        self.consistency_checker.check_names = consistency_config.get("check_names", True)

        logic_config = qa_config.get("logic_check", {})
        self.logic_checker = LogicChecker()
        self.logic_checker.enabled = logic_config.get("enabled", True)

        crossref_config = qa_config.get("crossref_check", {})
        self.crossref_checker = CrossRefChecker()
        self.crossref_checker.enabled = crossref_config.get("enabled", True)

        # LLM 配置
        self.llm_config = qa_config.get("llm_check", {})
        self.llm_checker = None

    def check(self, doc: DocumentModel, categories: list[str] = None) -> QAReport:
        """
        对文档执行质量检查。

        Args:
            doc: 文档模型
            categories: 要执行的检查类别，None 表示全部。
                       可选值：["typo", "consistency", "logic", "crossref", "grammar"]
            use_llm: 是否启用 LLM 辅助检测

        Returns:
            QAReport: 检查报告
        """
        start_time = time.time()
        
        # 根据文档长度决定是否使用分块处理
        total_elements = len(doc.elements)
        use_chunking = self.enable_chunking and total_elements > self.chunk_size
        
        if use_chunking:
            return self._check_chunked(doc, categories, start_time)
        else:
            return self._check_sequential(doc, categories, start_time)
    
    def _check_sequential(self, doc: DocumentModel, categories: list[str], 
                         start_time: float) -> QAReport:
        """顺序检查（短文档）"""
        report = QAReport()

        if categories is None:
            categories = ["typo", "consistency", "logic", "crossref"]

        if "typo" in categories and self.typo_checker.enabled:
            typo_report = self.typo_checker.check(doc)
            for issue in typo_report.issues:
                report.add_issue(issue)

        if "consistency" in categories and self.consistency_checker.enabled:
            consistency_report = self.consistency_checker.check(doc)
            for issue in consistency_report.issues:
                report.add_issue(issue)

        if "logic" in categories and self.logic_checker.enabled:
            logic_report = self.logic_checker.check(doc)
            for issue in logic_report.issues:
                report.add_issue(issue)

        if "crossref" in categories and self.crossref_checker.enabled:
            crossref_report = self.crossref_checker.check(doc, report)

        # LLM 增强检测（如果启用）
        if self.llm_config.get("enabled", False):
            self._apply_llm_enhancement(doc, report, categories)
        
        elapsed = time.time() - start_time
        report.metadata['check_time_sec'] = round(elapsed, 3)
        report.metadata['chunking_enabled'] = False

        return report
    
    def _apply_llm_enhancement(self, doc: DocumentModel, report: QAReport, 
                               categories: list[str]) -> None:
        """应用 LLM 增强检测"""
        try:
            if self.llm_checker is None:
                from core.llm_qa_checker import LLMQAChecker
                self.llm_checker = LLMQAChecker(config=self.llm_config)
            
            if not self.llm_checker.enabled:
                return

            # 如果有 grammar 类别，执行 LLM 语法检测
            if "grammar" in categories:
                grammar_report = self.llm_checker.check_grammar(doc)
                for issue in grammar_report.issues:
                    if not self._is_duplicate(issue, report):
                        report.add_issue(issue)
            
            # 对 typo 和 logic 执行 LLM 补充检测
            if "typo" in categories:
                typo_llm_report = self.llm_checker.check_typo(doc)
                for issue in typo_llm_report.issues:
                    if not self._is_duplicate(issue, report):
                        report.add_issue(issue)
            
            if "logic" in categories:
                logic_llm_report = self.llm_checker.check_logic(doc)
                for issue in logic_llm_report.issues:
                    if not self._is_duplicate(issue, report):
                        report.add_issue(issue)
        except Exception as e:
            print(f"[QA Engine] LLM 增强检测失败: {e}")
    
    def _is_duplicate(self, new_issue: QAIssue, report: QAReport) -> bool:
        """检查新问题是否与已有问题重复"""
        new_text = (new_issue.location_text or "").strip()
        if len(new_text) < 2:
            return False
            
        for existing in report.issues:
            existing_text = (existing.location_text or "").strip()
            if len(existing_text) < 2:
                continue
            
            # 文本包含关系或高度相似
            if new_text in existing_text or existing_text in new_text:
                return True
            
            # 相似度检查（简化版）
            set1 = set(new_text)
            set2 = set(existing_text)
            if set1 and set2:
                similarity = len(set1 & set2) / len(set1 | set2)
                if similarity > 0.8:
                    return True
        
        return False
    
    def _check_chunked(self, doc: DocumentModel, categories: list[str], 
                      start_time: float) -> QAReport:
        """分块检查（长文档）"""
        report = QAReport()
        
        # 准备分块
        chunks = self.optimizer.prepare_chunks(doc.elements)
        
        # 对每个分块执行检查
        chunk_reports = []
        for chunk in chunks:
            chunk_doc = DocumentModel(
                source_file=doc.source_file,
                source_format=doc.source_format,
            )
            chunk_doc.elements = chunk.elements
            
            chunk_report = self._check_sequential(chunk_doc, categories, time.time())
            chunk_reports.append(chunk_report)
        
        # 合并报告
        for chunk_report in chunk_reports:
            for issue in chunk_report.issues:
                report.add_issue(issue)
        
        elapsed = time.time() - start_time
        report.metadata['check_time_sec'] = round(elapsed, 3)
        report.metadata['chunking_enabled'] = True
        report.metadata['num_chunks'] = len(chunks)
        report.metadata['performance_stats'] = self.optimizer.get_performance_report()

        return report

    def check_typo_only(self, doc: DocumentModel) -> QAReport:
        """仅执行错别字检查"""
        return self.check(doc, ["typo"])

    def check_consistency_only(self, doc: DocumentModel) -> QAReport:
        """仅执行一致性检查"""
        return self.check(doc, ["consistency"])

    def check_logic_only(self, doc: DocumentModel) -> QAReport:
        """仅执行逻辑检查"""
        return self.check(doc, ["logic"])

    def check_crossref_only(self, doc: DocumentModel) -> QAReport:
        """仅执行交叉引用检查"""
        return self.check(doc, ["crossref"])

    def check_grammar_only(self, doc: DocumentModel) -> QAReport:
        """仅执行语法检查（LLM）"""
        report = QAReport()
        try:
            if self.llm_checker is None:
                from core.llm_qa_checker import LLMQAChecker
                self.llm_checker = LLMQAChecker(config=self.llm_config)
            
            if self.llm_checker.enabled:
                report = self.llm_checker.check_grammar(doc)
        except Exception as e:
            print(f"[QA Engine] 语法检查失败: {e}")
        
        return report

    def check_deep(self, doc: DocumentModel) -> QAReport:
        """执行深度检测（综合 LLM 分析，一次调用检测所有类型）"""
        report = QAReport()
        try:
            if self.llm_checker is None:
                from core.llm_qa_checker import LLMQAChecker
                self.llm_checker = LLMQAChecker(config=self.llm_config)
            
            if self.llm_checker.enabled:
                report = self.llm_checker.check_comprehensive(doc)
        except Exception as e:
            print(f"[QA Engine] 深度检测失败: {e}")
        
        return report
