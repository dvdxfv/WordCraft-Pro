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
# 包含基础词库 + 扩展词库（总计 500+ 词条）
# ============================================================
COMMON_TYPOS: dict[str, tuple[str, str]] = {
    # 基础错别字
    "的的地得": None,  # 特殊处理
    "帐号": ("账号", "账户的'账'应为'账'"),
    "帐户": ("账户", "账户的'账'应为'账'"),
    "帐单": ("账单", "账单的'账'应为'账'"),
    "登录帐号": ("登录账号", ""),
    "做为": ("作为", "'做'应为'作'"),
    "既使": ("即使", "'既'应为'即'"),
    "既便": ("即便", "'既'应为'即'"),
    "做为": ("作为", ""),
    "按装": ("安装", "'按'应为'安'"),
    "报歉": ("抱歉", "'报'应为'抱'"),
    "必竟": ("毕竟", "'必'应为'毕'"),
    "不径而走": ("不胫而走", "'径'应为'胫'"),
    "残无人道": ("惨无人道", "'残'应为'惨'"),
    "出奇不意": ("出其不意", "'奇'应为'其'"),
    "穿流不息": ("川流不息", "'穿'应为'川'"),
    "当人不让": ("当仁不让", "'人'应为'仁'"),
    "鬼计多端": ("诡计多端", "'鬼'应为'诡'"),
    "好高骛远": ("好高骛远", "正确"),
    "和霭": ("和蔼", "'霭'应为'蔼'"),
    "轰堂大笑": ("哄堂大笑", "'轰'应为'哄'"),
    "记忆尤新": ("记忆犹新", "'尤'应为'犹'"),
    "金壁辉煌": ("金碧辉煌", "'壁'应为'碧'"),
    "决对": ("绝对", "'决'应为'绝'"),
    "刻勤刻俭": ("克勤克俭", "'刻'应为'克'"),
    "烂芋充数": ("滥竽充数", "'烂芋'应为'滥竽'"),
    "厉厉在目": ("历历在目", "'厉'应为'历'"),
    "流恋": ("留恋", "'流'应为'留'"),
    "美仑美奂": ("美轮美奂", "'仑'应为'轮'"),
    "名符其实": ("名副其实", "'符'应为'副'"),
    "默守成规": ("墨守成规", "'默'应为'墨'"),
    "旁证博引": ("旁征博引", "'证'应为'征'"),
    "迫不急待": ("迫不及待", "'急'应为'及'"),
    "披星带月": ("披星戴月", "'带'应为'戴'"),
    "破斧沉舟": ("破釜沉舟", "'斧'应为'釜'"),
    "巧夺天公": ("巧夺天工", "'公'应为'工'"),
    "磬竹难书": ("罄竹难书", "'磬'应为'罄'"),
    "趋之若骛": ("趋之若鹜", "'骛'应为'鹜'"),
    "声名雀起": ("声名鹊起", "'雀'应为'鹊'"),
    "谈笑风声": ("谈笑风生", "'声'应为'生'"),
    "提心掉胆": ("提心吊胆", "'掉'应为'吊'"),
    "挺而走险": ("铤而走险", "'挺'应为'铤'"),
    "枉费心机": ("枉费心机", "正确"),
    "文过是非": ("文过饰非", "'是'应为'饰'"),
    "相儒以沫": ("相濡以沫", "'儒'应为'濡'"),
    "消声匿迹": ("销声匿迹", "'消'应为'销'"),
    "心无旁鹜": ("心无旁骛", "'鹜'应为'骛'"),
    "虚无飘渺": ("虚无缥缈", "'飘'应为'缥'"),
    "一遍": ("一遍", "正确"),
    "再接再励": ("再接再厉", "'励'应为'厉'"),
    "走头无路": ("走投无路", "'头'应为'投'"),
    "自曝自弃": ("自暴自弃", "'曝'应为'暴'"),
    "做业": ("作业", "'做'应为'作'"),
    "一份": ("一份", "正确"),
    "一幅画": ("一幅画", "正确"),
    "副食": ("副食", "正确"),
    "复食": ("副食", "'复'可能是'副'的错别字"),
    "象样": ("像样", "'象'应为'像'"),
    "印象": ("印象", "正确"),
    "反应": ("反应", "正确"),
    "反映": ("反映", "正确"),
    "幅射": ("辐射", "'幅'应为'辐'"),
    "辐射": ("辐射", "正确"),
    "渡过": ("渡过", "正确（渡过难关）"),
    "度过": ("度过", "正确（度过时间）"),
    "过渡": ("过渡", "正确（过渡时期）"),
    "过度": ("过度", "正确（过度疲劳）"),
}

# 合并扩展词库（额外增加 400+ 词条）
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

            if wrong in text:
                # 检查是否本身就是正确词（避免误报）
                if correct_word in text and text.index(correct_word) == text.index(wrong):
                    continue  # 文本中已有正确词，跳过

                pos = text.index(wrong)
                issue = QAIssue(
                    category=IssueCategory.TYPO,
                    severity=IssueSeverity.WARNING,
                    title='疑似错别字："' + wrong + '"',
                    description='建议将"' + wrong + '"修改为"' + correct_word + '"',
                    suggestion=correct_word,  # 直接存储替换后的正确文本
                    element_index=idx,
                    element_type=elem.element_type.value,
                    location_text=wrong,  # 只存储错别字本身，便于高亮定位
                    start_pos=pos,
                    end_pos=pos + len(wrong),
                    confidence=0.8,
                )
                if description:
                    issue.description += "。" + description
                report.add_issue(issue)

    def _check_de_di_de(self, elem: DocElement, idx: int, report: QAReport):
        """检查"的地得"用法"""
        text = elem.content

        # 简单规则：动词前的"的"可能是"地"
        # 匹配模式：XX的 + 动词
        verb_pattern = re.compile(
            r"([\u4e00-\u9fff]{1,4})的([\u4e00-\u9fff]{1,2})"
        )

        for match in verb_pattern.finditer(text):
            before = match.group(1)
            after = match.group(2)

            # 常见动词列表（简化）
            common_verbs = {
                "说", "做", "看", "听", "走", "跑", "写", "读", "学", "想",
                "打", "吃", "喝", "睡", "坐", "站", "来", "去", "给", "让",
                "使", "用", "找", "等", "问", "答", "叫", "帮", "带", "送",
                "发生", "进行", "产生", "出现", "存在", "提高", "增加", "减少",
                "改变", "影响", "推动", "促进", "实现", "完成", "开始", "结束",
                "发展", "建设", "管理", "分析", "研究", "设计", "规划", "组织",
            }

            if after in common_verbs:
                # 检查是否是"XX地+动词"模式
                # 排除一些合法的"的+动词"用法
                skip_patterns = [
                    "目的", "的话", "的确", "的是", "的当",
                    "的人", "的事", "的物", "的地方", "的时候", "的原因",
                ]
                if any(skip in (before + "的") for skip in skip_patterns):
                    continue

                issue = QAIssue(
                    category=IssueCategory.TYPO,
                    severity=IssueSeverity.INFO,
                    title='的地得用法："' + before + '的' + after + '"',
                    description='"' + before + '的' + after + '"中，"的"后面跟动词"' + after + '"，可能应使用"地"',
                    suggestion=before + '地' + after,  # 直接存储替换后的正确文本
                    element_index=idx,
                    element_type=elem.element_type.value,
                    location_text=match.group(0),  # 存储匹配到的完整文本
                    confidence=0.5,  # 低置信度，仅供参考
                )
                report.add_issue(issue)
