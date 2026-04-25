# -*- coding: utf-8 -*-
"""
错别字检查扩展词库

分层结构（按优先级从高到低）：
    1. CURATED_HIGH_FREQUENCY_TYPOS — 本文件中手工筛选的高频错字
    2. CURATED_IDIOM_TYPOS         — 本文件中手工筛选的成语错字
    3. core/data/common_typos.tsv  — 外置的大词库（~500 条，TSV 格式）
    4. core/data/user_typos.tsv    — 用户自定义覆盖（可选，不随项目分发）

所有词条最终通过 `get_all_typos()` 汇总，自动去重、过滤噪声（如
单字条目、建议含 "/" 等会导致 typo_checker 误报的条目）。

如果你想为自己的项目加词，请在 core/data/user_typos.tsv 维护，不要
直接改本文件，以便后续升级时不冲突。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# 高频错别字（手工维护）
# ============================================================
CURATED_HIGH_FREQUENCY_TYPOS: Dict[str, Tuple[str, str]] = {
    "帐号": ("账号", "账户的'账'应是'账'"),
    "帐户": ("账户", "账户的'账'应是'账'"),
    "帐单": ("账单", "账单的'账'应是'账'"),
    "登录帐号": ("登录账号", ""),
    "做为": ("作为", "'做'应为'作'"),
    "既使": ("即使", "'既'应为'即'"),
    "既便": ("即便", "'既'应为'即'"),
    "按装": ("安装", "'按'应为'安'"),
    "报歉": ("抱歉", "'报'应为'抱'"),
    "必竟": ("毕竟", "'必'应为'毕'"),
    "决对": ("绝对", "'决'应为'绝'"),
    "决大部分": ("绝大部分", "'决'应为'绝'"),
    "做业": ("作业", "'做'应为'作'"),
    "象样": ("像样", "'象'应为'像'"),
    "幅射": ("辐射", "'幅'应为'辐'"),
    "象是": ("像是", "'象'应为'像'"),
    "迷语": ("谜语", "'迷'应为'谜'"),
    "兰色": ("蓝色", "'兰'应为'蓝'"),
    "蓝球": ("篮球", "'蓝'应为'篮'"),
    "作饭": ("做饭", "'作'应为'做'"),
    "带帽": ("戴帽", "'带'应为'戴'"),
    "带花": ("戴花", "'带'应为'戴'"),
    "复盖": ("覆盖", "'复'应为'覆'"),
    "简炼": ("简练", "'炼'应为'练'"),
    "锻练": ("锻炼", "'练'应为'炼'"),
    "立生": ("产生", "语境中常见误写，通常应为'产生'"),
    "他门": ("他们", "常见形近误写"),
    "磨厉": ("磨砺", "'厉'应为'砺'"),
    "冒然": ("贸然", "'冒'应为'贸'"),
    "脉博": ("脉搏", "'博'应为'搏'"),
    "膨涨": ("膨胀", "'涨'应为'胀'"),
    "园满": ("圆满", "'园'应为'圆'"),
    "火中取粟": ("火中取栗", "'粟'应为'栗'"),
    "针贬": ("针砭", "'贬'应为'砭'"),
    "频临": ("濒临", "'频'应为'濒'"),
    "座标": ("坐标", "'座'应为'坐'"),
    "赋与": ("赋予", "'与'应为'予'"),
    "密诀": ("秘诀", "'密'应为'秘'"),
}

# ============================================================
# 成语错别字（手工维护）
# ============================================================
CURATED_IDIOM_TYPOS: Dict[str, Tuple[str, str]] = {
    "爱不失手": ("爱不释手", "'失'应为'释'"),
    "按步就班": ("按部就班", "'步'应为'部'"),
    "拔山涉水": ("跋山涉水", "'拔'应为'跋'"),
    "百无聊懒": ("百无聊赖", "'懒'应为'赖'"),
    "搬门弄斧": ("班门弄斧", "'搬'应为'班'"),
    "半途而费": ("半途而废", "'费'应为'废'"),
    "饱经苍桑": ("饱经沧桑", "'苍'应为'沧'"),
    "变本加利": ("变本加厉", "'利'应为'厉'"),
    "不记其数": ("不计其数", "'记'应为'计'"),
    "不径而走": ("不胫而走", "'径'应为'胫'"),
    "不落巢臼": ("不落窠臼", "'巢'应为'窠'"),
    "残无人道": ("惨无人道", "'残'应为'惨'"),
    "操胜卷": ("操胜券", "'卷'应为'券'"),
    "侧隐之心": ("恻隐之心", "'侧'应为'恻'"),
    "察颜观色": ("察言观色", "'颜'应为'言'"),
    "出奇不意": ("出其不意", "'奇'应为'其'"),
    "穿流不息": ("川流不息", "'穿'应为'川'"),
    "粗制烂造": ("粗制滥造", "'烂'应为'滥'"),
    "当人不让": ("当仁不让", "'人'应为'仁'"),
    "鬼计多端": ("诡计多端", "'鬼'应为'诡'"),
    "轰堂大笑": ("哄堂大笑", "'轰'应为'哄'"),
    "记忆尤新": ("记忆犹新", "'尤'应为'犹'"),
    "金壁辉煌": ("金碧辉煌", "'壁'应为'碧'"),
    "刻勤刻俭": ("克勤克俭", "'刻'应为'克'"),
    "烂芋充数": ("滥竽充数", "'烂芋'应为'滥竽'"),
    "厉厉在目": ("历历在目", "'厉'应为'历'"),
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
    "文过是非": ("文过饰非", "'是'应为'饰'"),
    "相儒以沫": ("相濡以沫", "'儒'应为'濡'"),
    "消声匿迹": ("销声匿迹", "'消'应为'销'"),
    "心无旁鹜": ("心无旁骛", "'鹜'应为'骛'"),
    "虚无飘渺": ("虚无缥缈", "'飘'应为'缥'"),
    "再接再励": ("再接再厉", "'励'应为'厉'"),
    "走头无路": ("走投无路", "'头'应为'投'"),
    "自曝自弃": ("自暴自弃", "'曝'应为'暴'"),
}


# ============================================================
# TSV 词库加载器
# ============================================================
_DATA_DIR = Path(__file__).parent / "data"
_COMMON_TSV = _DATA_DIR / "common_typos.tsv"
_USER_TSV = _DATA_DIR / "user_typos.tsv"
_SIGHAN_TXT = _DATA_DIR / "sighan_pairs.txt"


def _is_valid_entry(wrong: str, right: str) -> bool:
    """过滤掉容易误报的条目：

    - 必须至少 2 个字（单字如"的""地""得"需结合语境，不入词典避免刷屏）
    - wrong ≠ right（自映射条目无意义）
    - right 不含"/"（否则 typo_checker 的 `correct in text` 判断会永远失败）
    - wrong 和 right 都是非空字符串
    """
    if not wrong or not right:
        return False
    if wrong == right:
        return False
    if len(wrong) < 2:
        return False
    if "/" in right:
        return False
    return True


def _load_tsv(path: Path) -> Dict[str, Tuple[str, str]]:
    """从 TSV 文件加载 `错字→(正字, 说明)` 词典。格式 `错\\t正\\t说明?`。"""
    if not path.exists():
        return {}

    result: Dict[str, Tuple[str, str]] = {}
    filtered = 0
    try:
        with path.open("r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.rstrip("\n").strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                wrong, right = parts[0].strip(), parts[1].strip()
                note = parts[2].strip() if len(parts) >= 3 else ""
                if not _is_valid_entry(wrong, right):
                    filtered += 1
                    continue
                if not note:
                    note = f"'{wrong}'应为'{right}'"
                result[wrong] = (right, note)
    except OSError as e:
        logger.warning("无法读取 %s: %s", path, e)
        return {}

    logger.debug("从 %s 加载 %d 条（过滤 %d 条无效）", path.name, len(result), filtered)
    return result


def _load_sighan_pairs(min_count: int = 2) -> Dict[str, Tuple[str, str]]:
    """加载 SIGHAN 2015 衍生的 2-gram 错字对（opt-in，低置信度）。

    出现次数低于 min_count 的条目直接跳过，降低噪声。
    """
    if not _SIGHAN_TXT.exists():
        return {}

    result: Dict[str, Tuple[str, str]] = {}
    try:
        with _SIGHAN_TXT.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.rstrip("\n").strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                wrong, right, cnt_s = parts[0], parts[1], parts[2]
                try:
                    cnt = int(cnt_s)
                except ValueError:
                    continue
                if cnt < min_count:
                    continue
                if not _is_valid_entry(wrong, right):
                    continue
                result[wrong] = (right, f"SIGHAN 衍生（出现 {cnt} 次，仅供参考）")
    except OSError as e:
        logger.warning("无法读取 %s: %s", _SIGHAN_TXT, e)
        return {}
    return result


# ============================================================
# 聚合入口
# ============================================================
# 懒加载缓存（首次调用时加载，后续复用）
_CACHED: Optional[Dict[str, Tuple[str, str]]] = None
_CACHED_WITH_SIGHAN: Optional[Dict[str, Tuple[str, str]]] = None


def get_all_typos(
    *,
    include_sighan: bool = False,
    reload: bool = False,
) -> Dict[str, Tuple[str, str]]:
    """获取合并后的错别字词典。

    合并顺序（后者覆盖前者）：
        1. 内置高频错字
        2. 内置成语错字
        3. core/data/common_typos.tsv
        4. core/data/user_typos.tsv（用户自定义，最高优先）
        5. core/data/sighan_pairs.txt（仅在 include_sighan=True 时）

    参数：
        include_sighan: 是否合并 SIGHAN 衍生词条（低置信，仅供参考）
        reload: 是否忽略缓存强制重新加载
    """
    global _CACHED, _CACHED_WITH_SIGHAN
    cache = _CACHED_WITH_SIGHAN if include_sighan else _CACHED
    if cache is not None and not reload:
        return dict(cache)

    merged: Dict[str, Tuple[str, str]] = {}
    for source in (CURATED_HIGH_FREQUENCY_TYPOS, CURATED_IDIOM_TYPOS):
        for k, v in source.items():
            if _is_valid_entry(k, v[0]):
                merged[k] = v

    merged.update(_load_tsv(_COMMON_TSV))
    merged.update(_load_tsv(_USER_TSV))

    if include_sighan:
        sighan = _load_sighan_pairs()
        for k, v in sighan.items():
            merged.setdefault(k, v)
        _CACHED_WITH_SIGHAN = dict(merged)
    else:
        _CACHED = dict(merged)

    return merged


# ============================================================
# 向后兼容（旧 API）
# ============================================================
HIGH_FREQUENCY_TYPOS = CURATED_HIGH_FREQUENCY_TYPOS
IDIOM_TYPOS = CURATED_IDIOM_TYPOS
CONFUSING_WORDS: Dict[str, Tuple[str, str]] = {}  # 已废弃：单字/含"/"会引入噪声


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    base = get_all_typos(include_sighan=False)
    full = get_all_typos(include_sighan=True, reload=True)
    print(f"内置高频错字：{len(CURATED_HIGH_FREQUENCY_TYPOS)} 个")
    print(f"内置成语错字：{len(CURATED_IDIOM_TYPOS)} 个")
    print(f"TSV 外置词库：{len(_load_tsv(_COMMON_TSV))} 个")
    print(f"用户自定义词库：{len(_load_tsv(_USER_TSV))} 个")
    print(f"SIGHAN 衍生词库（min_count=2）：{len(_load_sighan_pairs())} 个")
    print(f"-- 默认合并总计：{len(base)} 个")
    print(f"-- 含 SIGHAN 总计：{len(full)} 个")
    print()
    print("抽样（前 5）：")
    for k, v in list(base.items())[:5]:
        print(f"  {k} -> {v}")
