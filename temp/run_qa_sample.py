#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
样本文档 QA 诊断脚本
用法: python temp/run_qa_sample.py <docx路径> [输出txt路径]
"""
import sys, os, json, textwrap
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    if len(sys.argv) < 2:
        print("用法: python run_qa_sample.py <docx路径> [输出txt路径]")
        sys.exit(1)

    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else src.replace(".docx", "_qa_report.txt").replace(".doc", "_qa_report.txt")

    print(f"[1] 解析文档: {src}")
    from parsers.dispatcher import parse_file
    doc = parse_file(src)
    print(f"    → {len(doc.elements)} 个元素")

    print("[2] 运行 QA 引擎（typo + consistency + format + crossref，含参考文献引用规范）…")
    from core.qa_engine import QAEngine
    engine = QAEngine()
    report = engine.check(doc, categories=["typo", "consistency", "format", "crossref"])
    print(f"    → 共 {report.total} 个问题")

    # xref_citation 已在 QAEngine.check 中随 crossref 一起运行，warning 通过 metadata 传递
    xref_citation_issues = [i for i in report.issues if i.rule_id == "xref.plain_text_citation"]
    xref_warning = report.metadata.get("xref_citation_warning", "")
    print(f"    → 其中参考文献引用规范问题: {len(xref_citation_issues)} 个")
    if xref_warning:
        print(f"    ⚠ {xref_warning}")

    lines = []
    lines.append("=" * 80)
    lines.append(f"QA 诊断报告")
    lines.append(f"文件: {os.path.basename(src)}")
    lines.append(f"元素数: {len(doc.elements)}")
    lines.append(f"QA 问题总数: {report.total}  (error={report.error_count} warn={report.warning_count} info={report.info_count})")
    lines.append(f"  其中参考文献引用规范问题: {len(xref_citation_issues)}")
    if xref_warning:
        lines.append(f"  ⚠ {xref_warning}")
    lines.append("=" * 80)

    # 使用 QAEngine 的统一 issues，不再重复合并
    all_issues = report.issues
    cat_map = {}
    for issue in all_issues:
        cat = issue.category.value if hasattr(issue.category, 'value') else str(issue.category)
        cat_map.setdefault(cat, []).append(issue)

    for cat, issues in sorted(cat_map.items()):
        lines.append(f"\n{'─'*60}")
        lines.append(f"[{cat.upper()}]  共 {len(issues)} 个")
        lines.append(f"{'─'*60}")
        for i, q in enumerate(issues[:50], 1):  # 每类最多显示 50 条
            sev = q.severity.value if hasattr(q.severity, 'value') else str(q.severity)
            loc = (q.location_text or "")[:60]
            fix_tag = ""
            if q.fixable and q.fix_type:
                fix_tag = f"  [可修复:{q.fix_type}]"
            if q.fix_payload:
                attr = q.fix_payload.get('attr','')
                val  = q.fix_payload.get('value','')
                fix_tag += f"  attr={attr} val={val}"
            lines.append(f"  {i:3}. [{sev}] {q.title}")
            lines.append(f"       位置: {loc}")
            lines.append(f"       建议: {(q.suggestion or '')[:80]}")
            lines.append(f"       rule_id: {q.rule_id or ''}{fix_tag}")
        if len(issues) > 50:
            lines.append(f"  ... 还有 {len(issues)-50} 条（已截断）")

    lines.append("\n" + "=" * 80)
    lines.append("fix_payload 详情（前20条可修复问题）")
    lines.append("=" * 80)
    fixable = [q for q in all_issues if q.fixable and q.fix_payload][:20]
    for q in fixable:
        lines.append(f"\n  rule: {q.rule_id}")
        lines.append(f"  fix_payload: {json.dumps(q.fix_payload, ensure_ascii=False)}")

    text = "\n".join(lines)
    os.makedirs(os.path.dirname(out) if os.path.dirname(out) else ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"\n[OK] 报告已写入: {out}")
    # 终端预览前2000字（避免GBK emoji崩溃）
    try:
        print(text[:2000])
    except UnicodeEncodeError:
        print(text[:2000].encode('gbk', errors='replace').decode('gbk'))

if __name__ == "__main__":
    main()
