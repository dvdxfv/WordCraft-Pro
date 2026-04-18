"""
QA 结果模型 (Quality Assurance Models)

质量检查的结果数据结构，统一表示各类检查发现的问题。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IssueSeverity(Enum):
    """问题严重程度"""
    ERROR = "error"         # 错误（必须修复）
    WARNING = "warning"     # 警告（建议修复）
    INFO = "info"           # 提示（可选修复）


class IssueCategory(Enum):
    """问题类别"""
    TYPO = "typo"                       # 错别字
    GRAMMAR = "grammar"                 # 语法问题
    INCONSISTENCY = "inconsistency"     # 数据不一致
    LOGIC = "logic"                     # 逻辑问题
    FORMAT = "format"                   # 格式问题
    REFERENCE = "reference"             # 引用问题
    STYLE = "style"                     # 表达风格


class IssueStatus(Enum):
    """问题处理状态"""
    PENDING = "pending"       # 待处理
    ACCEPTED = "accepted"     # 已接受（将修复）
    IGNORED = "ignored"       # 已忽略


@dataclass
class QAIssue:
    """质量检查发现的问题"""
    # 基本信息
    issue_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    category: IssueCategory = IssueCategory.TYPO
    severity: IssueSeverity = IssueSeverity.WARNING
    status: IssueStatus = IssueStatus.PENDING

    # 问题描述
    title: str = ""                   # 问题标题（简短）
    description: str = ""             # 详细说明
    suggestion: str = ""              # 修改建议

    # 位置信息
    element_index: int = -1           # 元素索引（在 DocumentModel.elements 中的位置）
    element_type: str = ""            # 元素类型
    location_text: str = ""           # 问题所在的原文片段
    start_pos: int = -1               # 在元素文本中的起始位置
    end_pos: int = -1                 # 在元素文本中的结束位置

    # 关联信息（用于一致性检查）
    related_index: int = -1           # 关联元素的索引
    related_text: str = ""            # 关联元素的文本

    # 置信度
    confidence: float = 0.0           # 0~1，检查结果的置信度

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "status": self.status.value,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "element_index": self.element_index,
            "element_type": self.element_type,
            "location_text": self.location_text,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "related_index": self.related_index,
            "related_text": self.related_text,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> QAIssue:
        d = dict(data)
        d["category"] = IssueCategory(d["category"])
        d["severity"] = IssueSeverity(d["severity"])
        d["status"] = IssueStatus(d["status"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class QAReport:
    """质量检查报告"""
    issues: list[QAIssue] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # 统计
    total: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    # 分类统计
    typo_count: int = 0
    inconsistency_count: int = 0
    logic_count: int = 0

    def add_issue(self, issue: QAIssue):
        """添加问题并更新统计"""
        self.issues.append(issue)
        self.total += 1

        if issue.severity == IssueSeverity.ERROR:
            self.error_count += 1
        elif issue.severity == IssueSeverity.WARNING:
            self.warning_count += 1
        else:
            self.info_count += 1

        if issue.category == IssueCategory.TYPO:
            self.typo_count += 1
        elif issue.category == IssueCategory.INCONSISTENCY:
            self.inconsistency_count += 1
        elif issue.category == IssueCategory.LOGIC:
            self.logic_count += 1

    def get_issues_by_category(self, category: IssueCategory) -> list[QAIssue]:
        return [i for i in self.issues if i.category == category]

    def get_issues_by_severity(self, severity: IssueSeverity) -> list[QAIssue]:
        return [i for i in self.issues if i.severity == severity]

    def get_pending_issues(self) -> list[QAIssue]:
        return [i for i in self.issues if i.status == IssueStatus.PENDING]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "typo_count": self.typo_count,
            "inconsistency_count": self.inconsistency_count,
            "logic_count": self.logic_count,
            "issues": [i.to_dict() for i in self.issues],
        }

    def summary_text(self) -> str:
        """生成摘要文本"""
        lines = [
            f"质量检查报告",
            f"共发现 {self.total} 个问题",
            f"  错误: {self.error_count}  警告: {self.warning_count}  提示: {self.info_count}",
            f"  错别字: {self.typo_count}  数据不一致: {self.inconsistency_count}  逻辑问题: {self.logic_count}",
        ]
        return "\n".join(lines)
