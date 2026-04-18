"""
交叉引用数据模型 (Cross-Reference Models)

定义交叉引用引擎中的核心数据结构：
- RefTarget: 引用目标（图/表/公式/章节/参考文献）
- RefPoint: 引用点（文中引用某目标的位置）
- CrossRefMatch: 匹配结果
- CrossRefReport: 交叉引用检查报告
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RefTargetType(Enum):
    """引用目标类型"""
    FIGURE = "figure"           # 图
    TABLE = "table"             # 表
    EQUATION = "equation"       # 公式
    CHAPTER = "chapter"         # 章节
    APPENDIX = "appendix"       # 附录
    REFERENCE = "reference"     # 参考文献


class CrossRefStatus(Enum):
    """交叉引用状态"""
    VALID = "valid"             # 有效引用
    DANGLING = "dangling"       # 悬空引用（目标不存在）
    MISMATCH = "mismatch"       # 类型不匹配（如引用"图"但实际是"表"）
    DUPLICATE = "duplicate"     # 重复编号
    UNREFERENCED = "unreferenced"  # 目标未被引用
    NEEDS_CONFIRM = "needs_confirm"  # 需要用户确认


@dataclass
class RefTarget:
    """引用目标 — 文档中可被引用的实体"""
    target_type: RefTargetType
    number: str                 # 编号文本，如 "3-1"、"2.1"、"[5]"
    label: str                  # 完整标签，如 "图3-1"、"表2.1"、"(3-1)"
    title: str = ""             # 标题/描述文本
    element_index: int = -1     # 在 DocumentModel.elements 中的索引
    chapter_num: int = 0        # 所属章节号
    seq_num: int = 0            # 章内序号
    bookmark_name: str = ""     # Word 书签名称（用于域代码引用）

    def to_dict(self) -> dict:
        return {
            "target_type": self.target_type.value,
            "number": self.number,
            "label": self.label,
            "title": self.title,
            "element_index": self.element_index,
            "chapter_num": self.chapter_num,
            "seq_num": self.seq_num,
            "bookmark_name": self.bookmark_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RefTarget:
        data = data.copy()
        data["target_type"] = RefTargetType(data["target_type"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RefPoint:
    """引用点 — 文中引用某目标的位置"""
    ref_text: str               # 引用文本，如 "图3-1"、"如表2.1所示"
    target_type: RefTargetType  # 推断的目标类型
    target_number: str          # 推断的目标编号
    context: str = ""           # 所在段落文本
    element_index: int = -1     # 在 DocumentModel.elements 中的索引
    start_pos: int = 0          # 引用在段落中的起始位置
    end_pos: int = 0            # 引用在段落中的结束位置
    matched_target: Optional[RefTarget] = None  # 匹配到的目标

    def to_dict(self) -> dict:
        d = {
            "ref_text": self.ref_text,
            "target_type": self.target_type.value,
            "target_number": self.target_number,
            "context": self.context,
            "element_index": self.element_index,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
        }
        if self.matched_target:
            d["matched_target"] = self.matched_target.to_dict()
        return d


@dataclass
class CrossRefMatch:
    """匹配结果 — 一个引用点与一个目标的匹配"""
    ref_point: RefPoint
    target: RefTarget
    status: CrossRefStatus = CrossRefStatus.VALID
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "ref_point": self.ref_point.to_dict(),
            "target": self.target.to_dict(),
            "status": self.status.value,
            "message": self.message,
        }


@dataclass
class CrossRefReport:
    """交叉引用检查报告"""

    targets: list[RefTarget] = field(default_factory=list)
    ref_points: list[RefPoint] = field(default_factory=list)
    matches: list[CrossRefMatch] = field(default_factory=list)

    @property
    def target_count(self) -> int:
        return len(self.targets)

    @property
    def ref_point_count(self) -> int:
        return len(self.ref_points)

    @property
    def dangling_count(self) -> int:
        return sum(1 for m in self.matches if m.status == CrossRefStatus.DANGLING)

    @property
    def mismatch_count(self) -> int:
        return sum(1 for m in self.matches if m.status == CrossRefStatus.MISMATCH)

    @property
    def unreferenced_count(self) -> int:
        return sum(1 for m in self.matches if m.status == CrossRefStatus.UNREFERENCED)

    @property
    def valid_count(self) -> int:
        return sum(1 for m in self.matches if m.status == CrossRefStatus.VALID)

    @property
    def has_issues(self) -> bool:
        return any(m.status != CrossRefStatus.VALID for m in self.matches)

    def get_targets_by_type(self, target_type: RefTargetType) -> list[RefTarget]:
        return [t for t in self.targets if t.target_type == target_type]

    def get_ref_points_by_type(self, target_type: RefTargetType) -> list[RefPoint]:
        return [r for r in self.ref_points if r.target_type == target_type]

    def get_dangling_refs(self) -> list[CrossRefMatch]:
        return [m for m in self.matches if m.status == CrossRefStatus.DANGLING]

    def get_unreferenced_targets(self) -> list[CrossRefMatch]:
        return [m for m in self.matches if m.status == CrossRefStatus.UNREFERENCED]

    def summary_text(self) -> str:
        """生成可读的摘要文本"""
        lines = [
            "交叉引用检查报告",
            "=" * 30,
            f"引用目标总数：{self.target_count}",
            f"  图：{len(self.get_targets_by_type(RefTargetType.FIGURE))}",
            f"  表：{len(self.get_targets_by_type(RefTargetType.TABLE))}",
            f"  公式：{len(self.get_targets_by_type(RefTargetType.EQUATION))}",
            f"  章节：{len(self.get_targets_by_type(RefTargetType.CHAPTER))}",
            f"引用点总数：{self.ref_point_count}",
            f"有效引用：{self.valid_count}",
            f"悬空引用：{self.dangling_count}",
            f"类型不匹配：{self.mismatch_count}",
            f"未引用目标：{self.unreferenced_count}",
        ]

        if self.has_issues:
            lines.append("")
            lines.append("问题详情：")
            for m in self.matches:
                if m.status != CrossRefStatus.VALID:
                    lines.append(f"  [{m.status.value}] {m.ref_point.ref_text} — {m.message}")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "targets": [t.to_dict() for t in self.targets],
            "ref_points": [r.to_dict() for r in self.ref_points],
            "matches": [m.to_dict() for m in self.matches],
            "summary": {
                "target_count": self.target_count,
                "ref_point_count": self.ref_point_count,
                "valid_count": self.valid_count,
                "dangling_count": self.dangling_count,
                "mismatch_count": self.mismatch_count,
                "unreferenced_count": self.unreferenced_count,
            },
        }
