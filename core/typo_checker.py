"""
错别字检查器 (Typo Checker)

基于规则匹配和拼音辅助的中文错别字检测。
支持：常见错别字词典、同音字检测、形近字检测。
"""

from __future__ import annotations

import re
from typing import Optional

from core.document_model import DocumentModel, DocElement, ElementType
from core.qa_models import QAIssue, QAReport, IssueCategory, IssueSeverity
from core.typo_lib import get_all_typos


# ============================================================
# 常见错别字词典：{错误：(正确，说明)}
#
# 完全由 core/typo_lib.py 维护。该模块从以下来源合并：
#   - 手工内置高频错字与成语错字
#   - core/data/common_typos.tsv（~500 条）
#   - core/data/user_typos.tsv（用户可选自定义，优先覆盖）
#
# 词库已自动过滤掉单字、自映射、建议含"/"等容易误报的噪声条目。
# ============================================================
COMMON_TYPOS: dict[str, tuple[str, str] | None] = {
    "的的地得": None,  # 占位：由 _check_de_di_de 处理，不在此报告
}
COMMON_TYPOS.update(get_all_typos())

# 的地得用法规则
DE_DI_DE_RULES = [
    (r"([\u4e00-\u9fff])\s*的\s+(动词|形容词)", "的", "地",
     "'的'后面是动词/形容词时，可能应使用'地'（状语修饰）"),
    (r"(动词|形容词)\s*的\s+([\u4e00-\u9fff])", "的", "得",
     "'的'在动词/形容词后可能应使用'得'（补语标记）"),
]


class TypoChecker:
    """错别字检查器"""

    def __init__(self):
        self.enabled = True

    def check(self, doc: DocumentModel) -> QAReport:
        """对文档执行错别字检查"""
        report = QAReport()

        for idx, elem in enumerate(doc.elements):
            if not elem.content:
                continue

            # 检查常见错别字
            self._check_common_typos(elem, idx, report)

            # 检查"的地得"用法
            self._check_de_di_de(elem, idx, report)

        return report

    def _check_common_typos(self, elem: DocElement, idx: int, report: QAReport):
        """检查常见错别字"""
        text = elem.content

        for wrong, correction in COMMON_TYPOS.items():
            if correction is None:
                continue  # 跳过特殊处理项

            correct_word, description = correction

            for m in re.finditer(re.escape(wrong), text):
                pos = m.start()
                issue = QAIssue(
                    category=IssueCategory.TYPO,
                    severity=IssueSeverity.WARNING,
                    title='疑似错别字："' + wrong + '"',
                    description='建议将"' + wrong + '"修改为"' + correct_word + '"',
                    suggestion=correct_word,  # 直接存储替换后的正确文本
                    rule_id="typo.common_dict",
                    checker="typo_checker",
                    element_index=idx,
                    element_type=elem.element_type.value,
                    location_text=wrong,  # 只存储错别字本身，便于高亮定位
                    start_pos=pos,
                    end_pos=pos + len(wrong),
                    confidence=0.8,
                    fixable=True,
                    fix_type="text_replace",
                )
                if description:
                    issue.description += "。" + description
                report.add_issue(issue)

    def _check_de_di_de(self, elem: DocElement, idx: int, report: QAReport):
        """检查"的地得"用法 - 重点检查状语词+的+动词的错误模式

        根据规范：
        - "的" 用在修饰语和名词之间（包括名词化动词，如"涡旋的发生"）
        - "地" 用在修饰语和谓语动词之间（如"频繁地发生"）
        - 错误模式：状语词 + 的 + 动词（如"认真的学习"→"认真地学习"）

        为避免对"名词化动词"的误报，只报告明确错误的模式：
        当修饰词是状语词时，用"的"是明确错误的。
        """
        text = elem.content

        # 常见状语词（必须用"地"与动词搭配的词）
        common_adverbs = {
            "认真", "快速", "慢慢", "悄悄", "飞快", "高效", "精准", "频繁", "持续",
            "仔细", "仓促", "温和", "激烈", "平静", "急速", "缓慢", "小心", "大胆",
            "直接", "间接", "主动", "被动", "自愿", "被迫", "努力", "懒散",
        }

        pattern = re.compile(
            r"([\u4e00-\u9fff]{1,4})的([\u4e00-\u9fff]{1,2})"
        )

        for match in pattern.finditer(text):
            before = match.group(1)
            after = match.group(2)

            # 常见谓语动词（作为谓语时的动词）
            common_verbs = {
                "说", "做", "看", "听", "走", "跑", "写", "读", "学", "想",
                "打", "吃", "喝", "睡", "坐", "站", "来", "去", "给", "让",
                "使", "用", "找", "等", "问", "答", "叫", "帮", "带", "送",
                "发生", "进行", "产生", "出现", "存在", "提高", "增加", "减少",
                "改变", "影响", "推动", "促进", "实现", "完成", "开始", "结束",
                "发展", "建设", "管理", "分析", "研究", "设计", "规划", "组织",
                "影响", "匹配", "拟合", "计算", "流动", "循环", "变化", "上升", "下降",
            }

            # 只在"状语词+的+谓语动词"时报错
            # 这是明确的语法错误：状语词必须用"地"修饰动词，不能用"的"
            # 例："认真的学习" ❌ → "认真地学习" ✅
            if before in common_adverbs and after in common_verbs:

                issue = QAIssue(
                    category=IssueCategory.TYPO,
                    severity=IssueSeverity.WARNING,
                    title='的地得用法："' + before + '的' + after + '"',
                    description='"' + before + '的' + after + '"中，状语词"' + before + '"应使用"地"而非"的"',
                    suggestion=before + '地' + after,
                    rule_id="typo.de_di_de",
                    checker="typo_checker",
                    element_index=idx,
                    element_type=elem.element_type.value,
                    location_text=match.group(0),
                    confidence=0.8,
                    fixable=True,
                    fix_type="text_replace",
                )
                report.add_issue(issue)
