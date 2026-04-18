#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordCraft Pro Web 应用 Playwright 自动化测试脚本

覆盖场景：
1. 页面加载测试
2. 文件列表测试
3. 文件切换测试
4. 删除文件测试
5. 排版面板测试
6. 质量检查测试
7. 交叉引用测试
8. 导出按钮测试
9. 文档编辑测试
"""

import os
import time
from playwright.sync_api import sync_playwright

# ========== 配置 ==========
BASE_URL = "http://localhost:8080/index.html"
SCREENSHOT_DIR = "/data/user/work/test_screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ========== 测试结果收集 ==========
results = []  # 每项: {"name": str, "status": "pass"|"fail"|"skip", "detail": str}


def run_test(name, func, page):
    """运行单个测试用例，捕获异常并截图"""
    print(f"\n{'='*60}")
    print(f"  测试: {name}")
    print(f"{'='*60}")
    try:
        func(page)
        results.append({"name": name, "status": "pass", "detail": ""})
        print(f"  [PASS] {name}")
    except Exception as e:
        # 失败时截图
        safe_name = name.replace(" ", "_")
        err_screenshot = os.path.join(SCREENSHOT_DIR, f"error_{safe_name}.png")
        try:
            page.screenshot(path=err_screenshot)
            print(f"  错误截图已保存: {err_screenshot}")
        except Exception:
            pass
        results.append({"name": name, "status": "fail", "detail": str(e)})
        print(f"  [FAIL] {name}: {e}")


# ========== 测试用例 ==========

def test_01_page_load(page):
    """1. 页面加载测试 - 导航、等待 networkidle、验证标题、截图"""
    page.goto(BASE_URL, wait_until="networkidle")
    title = page.title()
    assert "WordCraft Pro" in title, f"页面标题不包含 'WordCraft Pro'，实际标题: {title}"
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_page_loaded.png"))
    print(f"  页面标题: {title}")


def test_02_file_list(page):
    """2. 文件列表测试 - 验证 3 个默认文件，点击第一个文件验证预览"""
    # 等待文件树渲染
    page.wait_for_selector("#fileTree .file-item", timeout=5000)

    # 获取所有文件项
    file_items = page.query_selector_all("#fileTree .file-item")
    assert len(file_items) == 3, f"期望 3 个文件，实际 {len(file_items)} 个"

    # 验证文件名
    expected_files = ["毕业论文_终稿.docx", "实验数据统计.xlsx", "参考文献汇总.pdf"]
    for i, item in enumerate(file_items):
        name_el = item.query_selector(".fi-name")
        actual_name = name_el.inner_text() if name_el else ""
        assert actual_name == expected_files[i], f"第 {i+1} 个文件名不匹配: 期望 '{expected_files[i]}'，实际 '{actual_name}'"
        print(f"  文件 {i+1}: {actual_name}")

    # 点击第一个文件
    file_items[0].click()
    page.wait_for_timeout(500)

    # 验证文档预览区显示"第一章 绪论"
    doc_page = page.wait_for_selector("#docPage", timeout=5000)
    doc_text = doc_page.inner_text()
    assert "第一章 绪论" in doc_text, f"文档预览区未显示'第一章 绪论'，实际内容: {doc_text[:100]}"
    print(f"  文档预览区包含'第一章 绪论'")


def test_03_file_switch(page):
    """3. 文件切换测试 - 切换文件验证内容变化"""
    file_items = page.query_selector_all("#fileTree .file-item")
    assert len(file_items) >= 2, "文件数量不足，无法执行切换测试"

    # 点击第二个文件
    file_items[1].click()
    page.wait_for_timeout(500)

    doc_page = page.wait_for_selector("#docPage", timeout=5000)
    doc_text = doc_page.inner_text()
    assert "第一章 绪论" not in doc_text, f"切换到第二个文件后仍显示'第一章 绪论'"
    print(f"  切换到第二个文件后，内容已变化")

    # 重新获取文件列表（DOM 可能已重新渲染）
    file_items = page.query_selector_all("#fileTree .file-item")
    # 点击第一个文件，验证内容恢复
    file_items[0].click()
    page.wait_for_timeout(500)

    doc_page = page.wait_for_selector("#docPage", timeout=5000)
    doc_text = doc_page.inner_text()
    assert "第一章 绪论" in doc_text, f"切回第一个文件后未恢复'第一章 绪论'"
    print(f"  切回第一个文件后，'第一章 绪论'已恢复")


def test_04_delete_file(page):
    """4. 删除文件测试 - 选中第一个文件并删除"""
    file_items = page.query_selector_all("#fileTree .file-item")
    initial_count = len(file_items)
    print(f"  删除前文件数量: {initial_count}")

    # 选中第一个文件
    file_items[0].click()
    page.wait_for_timeout(300)

    # 点击删除按钮（侧边栏中的删除按钮）
    delete_btn = page.query_selector(".sidebar-actions button[title='删除选中']")
    assert delete_btn is not None, "未找到删除按钮"
    delete_btn.click()
    page.wait_for_timeout(500)

    # 验证文件从列表中移除
    file_items_after = page.query_selector_all("#fileTree .file-item")
    assert len(file_items_after) == initial_count - 1, f"删除后文件数量不正确: 期望 {initial_count - 1}，实际 {len(file_items_after)}"
    print(f"  删除后文件数量: {len(file_items_after)}")

    # 截图
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_file_deleted.png"))


def test_05_format_panel(page):
    """5. 排版面板测试 - 点击排版按钮，验证右侧面板显示排版选项"""
    # 点击工具栏中的"排版"按钮
    format_btn = page.wait_for_selector("#btnFormat", timeout=5000)
    format_btn.click()
    page.wait_for_timeout(300)

    # 验证排版面板可见
    format_section = page.wait_for_selector("#rp-format", timeout=5000)
    assert format_section.is_visible(), "排版面板不可见"

    # 验证模板下拉框存在
    template_select = page.wait_for_selector("#templateSelect", timeout=5000)
    assert template_select is not None, "未找到模板下拉框"

    # 验证字号输入框存在（使用一级标题字号输入框作为代表）
    font_size_input = page.wait_for_selector("#fH1Size", timeout=5000)
    assert font_size_input is not None, "未找到字号输入框"

    print(f"  排版面板已显示")
    print(f"  模板下拉框存在: {template_select.get_attribute('id')}")
    print(f"  字号输入框存在: {font_size_input.get_attribute('id')}")


def test_06_quality_check(page):
    """6. 质量检查测试 - 运行质量检查，验证问题列表不为空"""
    # 点击工具栏中的"质量检查"按钮
    qa_btn = page.wait_for_selector("#btnQA", timeout=5000)
    qa_btn.click()
    page.wait_for_timeout(300)

    # 验证质量检查面板可见
    qa_section = page.wait_for_selector("#rp-qa", timeout=5000)
    assert qa_section.is_visible(), "质量检查面板不可见"

    # 点击"运行质量检查"按钮
    run_qa_btn = page.wait_for_selector("button:has-text('运行质量检查')", timeout=5000)
    run_qa_btn.click()

    # 等待检查完成
    time.sleep(1)

    # 验证问题列表不为空
    issue_list = page.wait_for_selector("#qaIssues", timeout=5000)
    issues = issue_list.query_selector_all(".issue")
    assert len(issues) > 0, f"质量检查后问题列表为空，期望至少有 1 个问题"
    print(f"  质量检查发现问题数: {len(issues)}")

    # 截图
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_quality_check.png"))


def test_07_cross_reference(page):
    """7. 交叉引用测试 - 点击交叉引用按钮，验证面板显示引用目标列表"""
    # 点击工具栏中的"交叉引用"按钮
    xref_btn = page.wait_for_selector("#btnXRef", timeout=5000)
    xref_btn.click()
    page.wait_for_timeout(300)

    # 验证交叉引用面板可见
    xref_section = page.wait_for_selector("#rp-xref", timeout=5000)
    assert xref_section.is_visible(), "交叉引用面板不可见"

    # 验证引用目标统计区域存在（stat-bar 中有"目标"计数）
    xref_targets_stat = page.wait_for_selector("#xrefTargets", timeout=5000)
    assert xref_targets_stat is not None, "未找到引用目标统计"

    # 验证引用目标列表区域存在（使用 attached 状态，因为表格可能在面板内）
    targets_body = page.wait_for_selector("#xrefTargetsBody", state="attached", timeout=5000)
    assert targets_body is not None, "未找到引用目标列表"

    print(f"  交叉引用面板已显示")

    # 截图
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_cross_reference.png"))


def test_08_export_button(page):
    """8. 导出按钮测试 - 点击导出按钮，验证没有 JavaScript 错误"""
    # 收集 console 消息
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # 点击导出按钮
    export_btn = page.wait_for_selector("button.tbtn[title='导出']", timeout=5000)
    assert export_btn is not None, "未找到导出按钮"
    export_btn.click()

    # 等待一段时间，让可能的错误出现
    page.wait_for_timeout(1000)

    # 检查是否有 JavaScript 错误
    js_errors = [e for e in console_errors if "export" in e.lower() or "导出" in e]
    assert len(js_errors) == 0, f"导出时出现 JavaScript 错误: {js_errors}"
    print(f"  导出按钮点击后无 JavaScript 错误")


def test_09_document_editing(page):
    """9. 文档编辑测试 - 点击文档预览区中的段落，验证可编辑元素"""
    # 确保文档区域有内容（先点击第一个文件）
    file_items = page.query_selector_all("#fileTree .file-item")
    if len(file_items) > 0:
        file_items[0].click()
        page.wait_for_timeout(500)

    # 点击文档预览区中的段落
    doc_page = page.wait_for_selector("#docPage", timeout=5000)

    # 查找段落元素
    paragraphs = doc_page.query_selector_all("p")
    if len(paragraphs) > 0:
        paragraphs[0].click()
        page.wait_for_timeout(300)
    else:
        # 如果没有 p 标签，直接点击文档区域
        doc_page.click()
        page.wait_for_timeout(300)

    # 验证文档区域是可编辑的
    content_editable = doc_page.get_attribute("contenteditable")
    assert content_editable == "true", f"文档区域不可编辑，contenteditable={content_editable}"

    # 验证可以获取焦点
    focused = doc_page.evaluate("el => document.activeElement === el")
    assert focused, "文档区域未获得焦点"

    print(f"  文档区域可编辑: contenteditable={content_editable}")
    print(f"  文档区域已获得焦点")

    # 截图
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_document_editing.png"))


# ========== 主函数 ==========

def main():
    """运行所有测试用例并输出报告"""
    print("=" * 60)
    print("  WordCraft Pro Web 应用自动化测试")
    print("=" * 60)
    print(f"  测试地址: {BASE_URL}")
    print(f"  截图目录: {SCREENSHOT_DIR}")
    print(f"  测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    with sync_playwright() as p:
        # 启动 headless chromium 浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 收集所有 console 消息用于调试
        page.on("console", lambda msg: print(f"  [CONSOLE {msg.type}] {msg.text}") if msg.type == "error" else None)

        try:
            # 按顺序执行所有测试
            run_test("1. 页面加载测试", test_01_page_load, page)
            run_test("2. 文件列表测试", test_02_file_list, page)
            run_test("3. 文件切换测试", test_03_file_switch, page)
            run_test("4. 删除文件测试", test_04_delete_file, page)
            run_test("5. 排版面板测试", test_05_format_panel, page)
            run_test("6. 质量检查测试", test_06_quality_check, page)
            run_test("7. 交叉引用测试", test_07_cross_reference, page)
            run_test("8. 导出按钮测试", test_08_export_button, page)
            run_test("9. 文档编辑测试", test_09_document_editing, page)
        finally:
            browser.close()

    # ========== 输出测试报告 ==========
    print("\n" + "=" * 60)
    print("  测试报告")
    print("=" * 60)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    total = len(results)

    for r in results:
        status_icon = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[r["status"]]
        detail = f" - {r['detail'][:80]}" if r["detail"] else ""
        print(f"  [{status_icon}] {r['name']}{detail}")

    print(f"\n  总计: {total}  通过: {passed}  失败: {failed}  跳过: {skipped}")
    print("=" * 60)

    # 返回退出码：有失败则返回 1
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    exit(main())
