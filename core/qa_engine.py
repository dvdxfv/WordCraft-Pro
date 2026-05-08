"""
质量检查引擎 (QA Engine)

规则层（Rule-based）检查：错别字、数据一致性、标点/格式、交叉引用。
AI 深度检查（LLM）：逻辑问题、语法优化、高阶语义问题。
支持长文分块处理和性能优化。
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from core.document_model import DocumentModel
from core.qa_models import QAReport, QAIssue, IssueCategory
from core.typo_checker import TypoChecker
from core.consistency_checker import ConsistencyChecker
from core.crossref_checker import CrossRefChecker
from core.punctuation_checker import PunctuationChecker
from core.autocorrect_checker import AutoCorrectChecker
from core.xref_citation_checker import XRefCitationStyleChecker
from core.performance import get_optimizer, get_async_checker


class QAEngine:
    """质量检查引擎"""

    def __init__(self, config: dict = None):
        config = config or {}
        qa_config = config.get("qa", {})
        self._ignore_rule_ids = set(qa_config.get("ignore_rule_ids", []))
        self._ignore_text_patterns = [p for p in qa_config.get("ignore_text_patterns", []) if p]

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

        crossref_config = qa_config.get("crossref_check", {})
        self.crossref_checker = CrossRefChecker()
        self.crossref_checker.enabled = crossref_config.get("enabled", True)

        xref_citation_config = qa_config.get("xref_citation_check", {})
        self.xref_citation_checker = XRefCitationStyleChecker()
        self.xref_citation_checker.enabled = xref_citation_config.get("enabled", True)

        punct_config = qa_config.get("punctuation_check", {})
        self.punct_checker = PunctuationChecker()
        self.punct_checker.enabled = punct_config.get("enabled", True)
        ac_config = qa_config.get("autocorrect_check", {})
        self.autocorrect_checker = AutoCorrectChecker()
        self.autocorrect_checker.enabled = ac_config.get("enabled", True)
        self.autocorrect_checker.min_confidence = ac_config.get("min_confidence", 0.7)
        self.autocorrect_checker.command = ac_config.get("command", "autocorrect")

        # LLM 配置
        self.llm_config = qa_config.get("llm_check", {})
        self.llm_checker = None

    def check(self, doc: DocumentModel, categories: list[str] = None,
              format_rules=None) -> QAReport:
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
            return self._check_chunked(doc, categories, start_time, format_rules)
        else:
            return self._check_sequential(doc, categories, start_time, format_rules)
    
    def _check_sequential(self, doc: DocumentModel, categories: list[str],
                         start_time: float, format_rules=None) -> QAReport:
        """顺序检查（短文档）"""
        report = QAReport()
        seen_fingerprints: set[tuple[str, str, str, str]] = set()

        if categories is None:
            categories = ["typo", "consistency", "crossref", "format"]

        self._run_checker(
            enabled=("typo" in categories and self.typo_checker.enabled),
            runner=self.typo_checker.check,
            doc=doc,
            report=report,
            seen_fingerprints=seen_fingerprints,
        )
        self._run_checker(
            enabled=("consistency" in categories and self.consistency_checker.enabled),
            runner=self.consistency_checker.check,
            doc=doc,
            report=report,
            seen_fingerprints=seen_fingerprints,
        )
        self._run_checker(
            enabled=("format" in categories and self.punct_checker.enabled),
            runner=self.punct_checker.check,
            doc=doc,
            report=report,
            seen_fingerprints=seen_fingerprints,
        )
        self._run_checker(
            enabled=("format" in categories and self.autocorrect_checker.enabled),
            runner=self.autocorrect_checker.check,
            doc=doc,
            report=report,
            seen_fingerprints=seen_fingerprints,
        )
        self._run_checker(
            enabled=("crossref" in categories and self.crossref_checker.enabled),
            runner=self.crossref_checker.check,
            doc=doc,
            report=report,
            seen_fingerprints=seen_fingerprints,
        )
        self._run_checker(
            enabled=("crossref" in categories and self.xref_citation_checker.enabled),
            runner=self.xref_citation_checker.check,
            doc=doc,
            report=report,
            seen_fingerprints=seen_fingerprints,
        )

        # 格式规范检查（需要保存的 FormatRules）
        if "format" in categories and format_rules is not None:
            try:
                from core.format_checker import FormatChecker
                self._run_checker(
                    enabled=True,
                    runner=FormatChecker(format_rules).check,
                    doc=doc,
                    report=report,
                    seen_fingerprints=seen_fingerprints,
                )
            except Exception as e:
                print(f"[QA Engine] FormatChecker 失败: {e}")

        # LLM 增强检测（如果启用）
        if self.llm_config.get("enabled", False):
            self._apply_llm_enhancement(doc, report, categories)
        
        elapsed = time.time() - start_time
        report.metadata['check_time_sec'] = round(elapsed, 3)
        report.metadata['chunking_enabled'] = False

        return report

    def _run_checker(
        self,
        *,
        enabled: bool,
        runner: Callable[[DocumentModel], QAReport | None],
        doc: DocumentModel,
        report: QAReport,
        seen_fingerprints: set[tuple[str, str, str, str]],
    ) -> None:
        """运行单个 checker，并按统一规则去重合并。"""
        if not enabled:
            return
        checker_report = runner(doc)
        if not checker_report:
            return
        # 将子 checker 的 metadata 合并到主 report（不覆盖已有键）
        for k, v in checker_report.metadata.items():
            report.metadata.setdefault(k, v)
        for issue in checker_report.issues:
            if self._should_ignore(issue):
                continue
            fp = self._issue_fingerprint(issue)
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)
            report.add_issue(issue)

    @staticmethod
    def _issue_fingerprint(issue: QAIssue) -> tuple[str, str, str, str]:
        """用于跨 checker 去重的稳定指纹。"""
        return (
            issue.category.value if hasattr(issue.category, "value") else str(issue.category),
            (issue.rule_id or "").strip(),
            (issue.location_text or "").strip(),
            (issue.suggestion or "").strip(),
        )

    def _should_ignore(self, issue: QAIssue) -> bool:
        if issue.rule_id and issue.rule_id in self._ignore_rule_ids:
            return True
        if not self._ignore_text_patterns:
            return False
        haystack = ((issue.location_text or "") + " " + (issue.title or "")).strip()
        return any(p in haystack for p in self._ignore_text_patterns)
    
    def _apply_llm_enhancement(self, doc: DocumentModel, report: QAReport, 
                               categories: list[str]) -> None:
        """应用 LLM 增强检测"""
        try:
            if self.llm_checker is None:
                from core.llm_qa_checker import LLMQAChecker
                self.llm_checker = LLMQAChecker(config=self.llm_config)
            
            if not self.llm_checker.enabled:
                return

            pipeline_cfg = self.llm_config.get("pipeline", {})
            if pipeline_cfg.get("enabled", False):
                # 二级：DeepSeek Flash 全量语义任务
                flash_model = pipeline_cfg.get("flash_model", "deepseek-v4-flash")
                flash_report, review_candidates = self.llm_checker.check_semantic_flash(
                    doc, model=flash_model
                )
                for issue in flash_report.issues:
                    if not self._is_duplicate(issue, report):
                        report.add_issue(issue)

                # 三级：DeepSeek Pro 疑难项 + 核心段落复核
                pro_model = pipeline_cfg.get("pro_model", "deepseek-v4-pro")
                pro_report = self.llm_checker.check_pro_review(
                    doc,
                    review_candidates=review_candidates,
                    model=pro_model,
                )
                for issue in pro_report.issues:
                    if not self._is_duplicate(issue, report):
                        report.add_issue(issue)
                report.metadata["llm_pipeline"] = {
                    "enabled": True,
                    "flash_model": flash_model,
                    "pro_model": pro_model,
                    "review_candidates": len(review_candidates),
                }
                return

            # 兼容旧逻辑（未启用新 pipeline 时）
            if "grammar" in categories:
                grammar_report = self.llm_checker.check_grammar(doc)
                for issue in grammar_report.issues:
                    if not self._is_duplicate(issue, report):
                        report.add_issue(issue)
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
                      start_time: float, format_rules=None) -> QAReport:
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
            
            chunk_report = self._check_sequential(chunk_doc, categories, time.time(), format_rules)
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
