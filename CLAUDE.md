# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current status

All tracked work items completed as of 2026-04-25 (第十二批 + P3/P4修复）. 单位不统一误报消除（ML/L/t在缩写中）+ 采纳后字体保护（无损accept）+ AutoCorrect高亮精确定位 + P3暗色主题修复 + P4选区字体显示 + P5问题记录。QA问题数从38→17（-55%）。

---

## Next batch（第十三批）：交叉引用采纳式设计

**目标**：用户文档中常出现"图1-1"、"[1]"等手写引用文字，但这些只是普通文本而非 Word REF 字段。新设计让用户像处理 QA 问题一样采纳这些文字，点击采纳时自动创建交叉引用。

**核心需求**：
1. 识别正文中未被字段化的引用（"图N"、"[N]"等）
2. 像 QA 问题一样展示，支持采纳/忽略/撤销
3. 采纳时在预览区标记，导出时创建 Word REF 字段

**交付内容**：

### 1. 后端（app.py:runXRef）
- 返回 `xref_issues` 数组，包含：
  - `type`: "unreferenced" | "dangling" （未被引用的目标 | 悬空引用）
  - `target_label`: 目标标签（"图1-1", "[1]"等）
  - `element_index`: 目标在 doc.elements 中的索引
  - `title`: 问题标题（用于 UI 显示）
  - `description`: 详细说明
  - `suggestion`: 建议的引用文字

### 2. 前端 UI（web/index.html）
- 交叉引用面板改为 QA 风格卡片：
  - 每张卡片显示一个"可采纳的交叉引用"
  - 按钮：定位（跳转到文档）、采纳、忽略、撤销
  - 使用现有的 QAIssue 卡片样式和逻辑
- 新增状态变量：`tabXrefAcceptedEdits[tab.name]`，记录已采纳的交叉引用

### 3. 采纳行为
- 采纳时：
  - 在预览区将目标文字标记为 `hl-xref-accepted`（绿色下划线，与 QA 的 `hl-accepted` 风格一致）
  - 保留 `data-xref-id="${targetId}"` 便于撤销定位
  - 推入 `tabXrefAcceptedEdits` 记录 `{target_label, target_type, element_index}`
- 撤销时：
  - 删除 `hl-xref-accepted` 标记，恢复原样式
  - 从 `tabXrefAcceptedEdits` 移除

### 4. 导出时生效
- `exportDocAsDocxClone` 在 XML 替换阶段，对 `xrefAcceptedEdits` 中的每条：
  - 在 `<w:t>` 中找到 `target_label` 文字
  - 替换为 Word REF 字段代码：
    ```xml
    <w:fldChar w:fldCharType="begin"/>
    <w:instrText xml:space="preserve"> REF target_bookmark \h </w:instrText>
    <w:fldChar w:fldCharType="end"/>
    ```
  - `target_bookmark` 来自 RefTarget 的 `bookmark_name`（已在 TargetScanner 中生成）

### 5. 测试验证
- 后端：新 runXRef 返回结构、xref_issues 字段正确
- 前端：采纳/撤销 UI 行为正确、tabXrefAcceptedEdits 状态同步
- 导出：
  - 采纳的引用生成 REF 字段
  - 在 Word 中更新域，编号自动链接到目标
  - 导出前后对比：手写"[1]" vs 字段"[1]"，导出行为不同

---

## 回归测试覆盖（防止重复返工）

`tests/test_batch_regression.py` — 22 个测试，覆盖第一至第十批所有已修复问题。
**每次修改代码后必须运行此文件**，任何已修复问题回退都会在此处失败。

```bash
python -m pytest tests/test_batch_regression.py -v
```

| Class | 批次 | 覆盖内容 |
|-------|------|---------|
| `TestBatch1RunQAChain` | 第一批 | runQA 返回 location_text/rule_id/checker；HTML 内容被真正解析 |
| `TestBatch3PunctuationChecker` | 第三批 | 句间空格/ug-L/摄氏度/中英文空格默认关闭/typo_lib 他门立生 |
| `TestBatch8CrossRefReferenceScan` | 第八批 | TargetScanner 识别参考文献节 [1]-[N]；RefPointScanner 文内引用；CrossRefMatcher 有效匹配 |
| `TestBatch9QAXrefChainFix` | 第九批 | DocElement.content 字段名；runQA 含 crossref；runXRef 返回 element_index；DocumentChunker.content |
| `TestBatch10FalsePositiveReduction` | 第十批 | 南海海表/生物物理不误报；真实重复字仍检出；AutoCorrect 标题；CJK空格关闭无噪音 |
| `TestCrossRefNoDuplicateMatches` | 第九/十批 | matches 含 element_index；app.runXRef 序列化完整 |

---

## Known issues / 待修问题

### P2：顿号缺失检测（并列词组）

**现象**：如"考虑中尺度海洋动力过程及其生物物理机制"，应检出"生物物理"之间或并列词组之间缺少顿号（、）。

**根因**：顿号缺失属于**语义级**错误，需判断哪些词是并列关系，规则层无法覆盖。纯正则无法区分"生物物理"（biophysical，合成形容词）与"生物、物理"（并列名词）。

**修复方向**：
- 需要中文词性标注（POS tagging）或依存句法分析，例如使用 `jieba` 词性标注或 `spacy zh` 模型
- 最小可行方案：维护一张"常见并列关键词对"列表（如 "生物物理" → 提示可能需要 "生物、物理"），但维护成本高且精度有限
- 推荐方案：在 LLM QA 层（`runAIQA`）中增加并列关系检查 prompt，让 AI 判断是否缺顿号

### P5：标题内部字体大小不一致检查

**现象**：标题中的不同字符有不同的字号，如"混合层深度（MLD）"中"M"和"L"是四号（14pt），"D"是小四（12pt）。这样的基础排版问题目前无法检出。

**根因**：现有的 `DocElement` 数据模型只记录**元素级别**的 `font_size_pt`，无法表示同一元素内部不同位置（run 级别）的字体大小差异。

**修复方向**：
- **短期（Quick fix）**：在 consistency_checker.py 中增加启发式检查——当一个标题被解析成多个微小的 DocElement 时（如 docx-preview 的 span 拆分），比较相邻元素的字体大小，如果在视觉上属于同一标题但字号不同则报错
- **长期（正确方案）**：重构数据模型，引入 `DocRun` 类来记录 run 级别的样式（类似 Word 的内部结构），修改 docx_parser.py 从源文件提取 run 级别的字体大小信息。后者工作量较大，但能准确处理各种混合格式文本

---

## Quick commands

```bash
# Fix Windows terminal encoding before starting
chcp 65001

# Start backend API server (port 5000)
cd web && python flask_app.py

# Start frontend static server (port 8081, auto-opens browser)
cd web && python run_web.py

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_core_functions.py -v

# Run a single test by name
python -m pytest tests/test_phase1.py::TestClassName::test_method_name -v

# Phase 5 export regression E2E
python -m pytest tests/e2e/test_export_docx_regression.py -q
```

**Minimal install** (skip PyTorch/ChatGLM if only using cloud AI):

```bash
pip install python-docx pdfplumber openpyxl PyYAML pydantic openai flask flask-cors supabase
```

---

## Architecture

### Two-layer API design

`app.py` is the **single source of truth for business logic** — it contains the `Api` class with all methods (`openFile`, `exportDocx`, `callAI`, `runQA`, etc.). `web/flask_app.py` is a thin Flask wrapper that routes HTTP requests to `Api` methods and nothing else. All actual logic lives in `app.py`.

### Central data model

`core/document_model.py` defines `DocumentModel` — the unified internal representation that every parser produces and every engine consumes. All parsers convert their file format into this model; the formatter, QA engine, exporter, and cross-reference engine all operate on it. When adding new functionality, start here to understand the data contract.

### Frontend is a single HTML file

`web/index.html` (~2500 lines) is a self-contained SPA. It loads docx-preview, mammoth.js, PDF.js, SheetJS, and Supabase JS from CDNs. The frontend communicates with the backend exclusively through `window.WC_API`, which wraps all API calls with `fetch('/api/...')`. There is no build step.

Key frontend state:

- `filesData` / `docContents` / `docxBuffers` — file registry and parsed content per file
- `openTabs` / `activeTabIdx` — tab management
- `tabQAState` / `tabXrefState` — per-tab QA and cross-reference results (persisted across tab switches)
- `window.currentQAData` — live QA issue list for the active tab
- `window._aiParsedRules` — last AI-parsed formatting rules (set by `runAIParse`, consumed by `applyAIRules`)

### Document rendering path

- `.docx` files: rendered using `docx-preview` library (`docxBuffers[name]` → `docxPreview.renderAsync`)
- `.doc` files: converted server-side → stored in `docxBuffers[name]` → same docx-preview path
- `.pdf` files: rendered using PDF.js (`pdfBuffers[name]`)
- `.xlsx` files: rendered using SheetJS
- All other formats: mammoth.js extracts HTML into `rawHtmlContents[name]`, or falls back to `docContents[name]` (simple element array)

### QA 两层分工架构

**规则层（Rule-based, 免费）**：`core/qa_engine.py` 编排的本地检查
- TypoChecker — 错别字（内置词库）
- ConsistencyChecker — 数据一致性（单位、日期、数值范围）
- PunctuationChecker — 标点/空格规范（中英混用、重复标点、括号配对）
- AutoCorrectChecker — 中文规范化（调用 autocorrect CLI）
- CrossRefEngine — 交叉引用检查（参考文献编号、图表链接）
- **不包括逻辑问题**（Logic 层已下沉到 AI）

**AI 深度检查（Premium）**：`runAIQA` 调用 LLM
- 继承规则层的所有检查结果
- 新增 AI 增强：**逻辑问题检查**（论证流畅性、因果关系、结论有效性）
- 语法/表述优化建议
- 需要语义理解的高阶问题

**核心原则**：规则层专注明确的、可自动化的错误，AI 层处理需要理解语境的问题。

### AI integration

`app.py:callAI` uses a two-channel fallback: first tries Supabase Edge Function proxy (`/functions/v1/ai-proxy`), then falls back to direct Doubao API call. The model is configurable per-call via the `config` parameter. `config.yaml` holds the LLM configuration for the Python-side `llm/client.py` (used by `qa_analyzer.py` and `nl_rule_parser.py`), separate from the `app.py` direct calls.

Response shape: `{"content": "...", "usage": {...}}` on success, `{"error": "..."}` on failure. Note: no `success` field — check `data.error` to detect failure.

### .doc file handling

`.doc` files use a three-level fallback in `parsers/dispatcher.py:_convert_doc_to_docx`:

1. **Try as .docx** — some `.doc` files are actually Open XML; python-docx opens them directly (zero dependencies)
2. **LibreOffice** — `soffice --headless --convert-to docx`; if installed but conversion fails, logs a warning and falls through (does not raise)
3. **Windows Word COM via PowerShell** — requires Microsoft Word; uses `New-Object -ComObject Word.Application` without pywin32

If all three fail, a clear error is raised listing the installation options.

### Supabase integration

`core/supabase_client.py` wraps auth, database, and storage. All `Api` methods in `app.py` check `self._supabase` — if `None` (Supabase unavailable), they fall back to local mock responses. This means the app runs offline without Supabase configured.

### Export (.docx) flow

`exportDoc()` in `web/index.html` uses the **docx.js** browser library (not the Python exporter). Every `TextRun` must set both `font.name` (western, e.g. `Times New Roman`) and `font.eastAsia` (Chinese, e.g. `宋体`) — omitting either causes garbled text in Word. Form fields read: `fH1Font/Size`, `fH2Font/Size`, `fH3Font/Size`, `fBFont/Size`, `fWFont`.

### Base64 encoding for large files

All browser → server binary transfers (file open, template upload, `.doc` conversion) use **chunked base64** encoding (8192 bytes/chunk) via `String.fromCharCode(...bytes.subarray(i, i+chunk))`. Never use `btoa(String.fromCharCode(...new Uint8Array(buf)))` with the spread operator — it causes stack overflow for files larger than ~65 KB.

### AI formatting rule parser

The "AI" tab in the format panel:

- `runAIParse()` — calls `callAI` with a system prompt, extracts JSON from the response, stores in `window._aiParsedRules`, renders in `#aiRulesBody`
- `applyAIRules()` — reads `window._aiParsedRules` and populates all format panel fields (`fH1Font`, `fBSize`, `fMT`, etc.)
- AI button uses `id="btnAIParse"` — use this ID in JS, not a CSS class selector

## Key files to know

| File | Role |
| ---- | ---- |
| `app.py` | All business logic; the `Api` class |
| `web/flask_app.py` | Flask routes — thin wrappers only |
| `web/index.html` | Entire frontend SPA |
| `core/document_model.py` | Central data model — read this first |
| `parsers/dispatcher.py` | Parser entry point; `.doc` three-level conversion fallback |
| `parsers/docx_parser.py` | Most complex parser; extracts styles, images, sections |
| `core/qa_engine.py` | QA 规则层编排：typo → consistency → format → crossref（逻辑问题由 AI 层处理） |
| `core/crossref_engine.py` | 交叉引用扫描与匹配：`TargetScanner` + `RefPointScanner` + `CrossRefMatcher` |
| `core/punctuation_checker.py` | Non-AI format/punctuation checks (标点、空格、括号、叠字) |
| `core/typo_lib.py` | 错别字词库聚合器：内置词典 + `common_typos.tsv` + `user_typos.tsv` + 可选 SIGHAN |
| `core/data/common_typos.tsv` | ~550 条手工筛过的常见错别字 TSV |
| `core/exporter.py` | Converts `DocumentModel` → `.docx` (Python-side, used by `saveTemplateSettings`) |

## Configuration

`config.yaml` configures LLM provider/key/model, QA checker toggles, and Chinese font size mappings. The app runs without it (uses defaults/mocks). Supabase credentials can also be set via env vars `SUPABASE_URL` and `SUPABASE_KEY`.

## Known constraints

- Only Web version is maintained — `pywebview` desktop mode is abandoned
- `.doc` conversion requires LibreOffice **or** Microsoft Word (see three-level fallback above)
- Supabase free tier pauses after 7 days of inactivity
- `web/index.html` uses inline `<style>` and `<script>` — there is no bundler or CSS preprocessor
- `exportDocAsPdf()` copies `docPage.innerHTML` directly into `#printTarget` before printing — inline event handlers in the document DOM execute in the current user's context only (no data leaves the browser); acceptable for single-user usage.
- `SUPABASE_ANON_KEY` is hardcoded in `web/index.html` (it is intentionally public; security relies on RLS). Doubao API key is hardcoded as fallback in `app.py:callAI` — set `DOUBAO_API_KEY` env var in production to override it. Do not rotate either key without updating both files.

---

## 商业化策略 / Monetization Plan (2026-04-25)

> **现状**：功能开发基本完成，积累了实际用户样本（南海鸢乌贼论文等）。下一步考虑产品分层与变现。

### 分层方案

**免费版（Free Tier）**
- 文档上传/预览（.docx/.doc/.pdf/.xlsx/.txt/.md）
- 基础规则检查（本地执行，无 API 调用）
  - 标点符号规范（中英文混用、重复标点、句间空格）
  - 错别字检查（内置词库 ~580 条 + 用户自定义）
  - 交叉引用基础扫描（标题识别）
- 导出 .docx（保留源排版）
- 质量仪表盘（基础统计）

**付费版（Premium Tier）— ¥9.9/月 or ¥79/年**
- 所有免费功能
- **AI QA 智能检查**（调用 DeepSeek V4）
  - 错别字/数据一致性/逻辑检查（AI 增强）
  - 智能排版规则解析（从模板自动提取）
  - 语法/表述优化建议
- **交叉引用深度检查**（参考文献编号、图表链接验证）
- 优先技术支持

### API 成本分析

**使用模型**：DeepSeek V4
- 输入价格：¥0.14 / 百万 tokens
- 输出价格：¥0.42 / 百万 tokens

**单次 QA 检查成本估算**：
```
平均输入：3000 tokens（文档片段 + system prompt）
平均输出：2000 tokens（检查结果 + 建议）
单次成本 = (3000 × 0.14 + 2000 × 0.42) / 1,000,000
         = ¥0.0013 ≈ 0.13 分钱
```

**月度成本预测**：
| 付费用户数 | 每用户月调用数 | 月成本 | 备注 |
|-----------|------------|--------|------|
| 5         | 20         | ¥13    | 个人用户 |
| 50        | 20         | ¥130   | 小团队 |
| 500       | 20         | ¥1300  | 快速增长期 |
| 5000      | 20         | ¥13000 | 成熟产品 |

**关键观察**：
- API 成本极低（月成本与付费用户数呈线性关系，且系数很小）
- 即使 1000 用户，月成本也仅 ¥1300，远低于预期收入
- 变现线：付费用户 > 100 人时已覆盖 API 成本

### 上线时机与策略

**阶段 1（待定）：直接分层上线**
- 不做免费期，直接上线两个版本
- 理由：API 成本可控，无需前期大量烧钱验证
- 风险：新产品可能流失用户（但可用免费版降低门槛）

**阶段 2（可选）：免费期验证**
- 如果用户反馈平平，先免费运营 1-2 月
- 收集使用数据后再上线付费版
- 优势：积累初期用户基数 + 口碑

### 定价对标

| 竞品 | 价格 | 核心功能 |
|------|------|---------|
| 本产品 Premium | ¥9.9/月 | AI QA + 交叉引用 + 导出 |
| 稿定设计 | ¥19.9/月 | 模板库 + 素材库（不同赛道） |
| 云梦笔记 | ¥6.99/月 | 笔记 + AI 总结 |
| Grammarly Premium | $12/月 ≈ ¥85/月 | 英文语法检查 + AI 写作 |

**定价合理性**：
- ¥9.9/月 = ¥119/年，属中等消费
- 若用户月使用 > 10 次 AI 检查，ROI > 10:1（¥9.9 vs ¥0.13×100）
- 对标 Grammarly，我们的价格低 8 倍，但功能针对中文学术文档

### 后续步骤

1. **确认上线时机**（立即 vs. 等待更多反馈）
2. **搭建付费体系**（支付接口、订阅管理、试用逻辑）
3. **前端 UI 改造**（版本指示、升级提示、功能限制）
4. **后端 API 改造**（用户订阅检验、使用量计费记录）
5. **运营策略**（首月免费试用 vs. 直接付费 vs. 按次付费）

---

## Recent fixes (2026-04-26) — 第十一批：P1 QA定位修复 + 的地得语法检查修复 + P3暗色主题 + P4选区字体字号

### A. QA卡片"未找到位置"修复（P1）

**三个根因，三处修复**：

| 根因 | 修复 |
| ---- | ---- |
| `locateIssue` fallback 的 `!el.querySelector('p,li,td,span')` 过滤掉所有含 `<span>` 子节点的元素——而 docx-preview 渲染的每个 `<p>` 段落都有 `<span class="run">` 子节点，fallback 永远找不到任何元素 | 删除该过滤条件，改为对 `p,li,td,th` 元素做 `innerText.includes()` 匹配，再按 innerText 长度升序排序取最精确的那个（最小匹配） |
| `applyHighlights` 单文本节点匹配无法处理跨节点情况（如"生物物理"被 docx-preview 拆成两个 `<span class="run">` 节点） | 新增 Pass 2：若 Pass 1 未插入任何 span，找最小 `p/li/td/th` 块元素（innerText 包含 hlText），拼接其所有文本节点的 full 字符串，定位 matchStart/End，用 `Range.deleteContents()+insertNode()` 原子性插入跨节点 span |
| `logic_checker.py` 的 `location_text` 末尾拼接 `"..."` 字面字符串（如 `text[:50] + "..."`），该字符串在 DOM 中不存在 | `app.py:runQRef` 序列化时 `.strip()`；`locateIssue` 搜索前用 `.replace(/\.{3,}$|…$/, '')` 剥离尾部省略号 |

**改动文件**：`web/index.html:applyHighlights`、`web/index.html:locateIssue`、`app.py:runQA`（`location_text` 加 `.strip()`）

### B. "的地得"语法检查修复

**问题**：`_check_de_di_de` 函数因为担心对"名词化动词"（如"涡旋的发生"）误报，直接禁用了整个检查。导致明确错误的模式也检查不出来。

**根因分析**：无法自动区分"名词 + 的 + 名词化动词"（合法，用"的"）vs "状语词 + 的 + 谓语动词"（错误，应用"地"）。前者需要语义理解，纯规则无法可靠实现。

**修复方案**：只检查明确错误的模式——"状语词 + 的 + 动词"。这是100%的错误（状语词必须用"地"修饰动词），不会对合法的"名词 + 的 + 名词化动词"误报。

**实现**（`core/typo_checker.py:_check_de_di_de`）：
- 启用检查（移除早期 `return` 语句）
- 定义 `common_adverbs` 集合：认真、快速、慢慢等18个高频状语词
- 定义 `common_verbs` 集合：说、做、学、发生等40多个常见动词
- 只在 `before in common_adverbs AND after in common_verbs` 时报错
- 置信度设为0.8（高），因为此模式是明确错误
- 严格度改为 WARNING（而非 INFO），优先级提升

**验证**：
- ✅ "认真的学习" → 报错（状语词+的+动词）
- ✅ "涡旋的发生" → 不报错（名词+的+名词化动词）
- ✅ "团队高效地协作" → 不报错（正确用法）
- ✅ 回归测试全部通过（22/22）

**改动文件**：`core/typo_checker.py:_check_de_di_de`

---

## Recent fixes (2026-04-25) — 第十批：交叉引用跳转 + QA误报修复 + 仪表盘修复

### A. 交叉引用匹配结果行点击跳转（上一会话完成）

**功能**：点击交叉引用面板"匹配结果"中的行，滚动到文档对应位置并短暂黄色高亮。

**关键技术点**：
- docx-preview 将 `[1]` 渲染为三个独立文本节点 `"["`+`"1"`+`"]"`，TreeWalker 无法匹配；改用 `element.innerText.includes(searchText)` 在 `<p>/<li>/<td>` 级别搜索
- 高亮用 `box-shadow: inset 0 0 0 1000px rgba(255,220,0,0.55)` 覆盖（CSS `@keyframes` 忽略 `!important`，不能用 `background-color` 动画）
- 滚动容器是 `#docViewport`（`doc-viewport` class），不是 `window`
- `RefPointScanner.scan` + `scan_multi_references` 双重调用导致每个引用在结果中出现两次（9段→18条）；用后端返回的 `element_index` 字段按段去重，确保第17条`[1]` 跳到第9段而非第1段（前言）

**改动文件**：`web/index.html:jumpToXRefInText`、`app.py:runXRef`（增加 `element_index` 字段）

### B. QA卡片点击定位修复

**根因**：`locateIssue(i)` 依赖 `[data-issue-id="${i}"]` span 必须存在于 DOM 中；但若 `applyHighlights` 阶段未能在渲染文档中找到该文本（表格内/docx-preview split节点），span 不存在，函数直接返回无任何动作。

**修复**（`web/index.html:locateIssue`）：增加 fallback 路径：span 不存在时，用 `innerText` 在 `<p>/<li>/<td>/<span>` 中搜索 `q.hlText`，找到后用 `viewport.scrollTop` 滚动并加 `box-shadow` 高亮（与 XRef 跳转同款）。

### C. QA规则误报修复

| 问题 | 修复 |
| ---- | ---- |
| 中英文间缺少空格误报刷屏 | `PunctuationChecker.check_cjk_spacing = False`（学术文档常见合法写法，默认关闭） |
| 疑似重复字：词界碰撞误报（如"生物物理"→"物物"、"南海海表"→"海海"） | 新增 `_BOUNDARY_CHARS` 集合（60+常见科技词素），当重复字在 `_BOUNDARY_CHARS` 中且两侧均为汉字时跳过（词界碰撞模式） |
| "AutoCorrect 文案规范问题"标题不明确 | `autocorrect_checker.py`：有 old/new 时改为 `建议规范化："xxx"`，否则 `文案格式规范` |

### D. 质量仪表盘修复

| 问题 | 修复 |
| ---- | ---- |
| `格式问题`类别未计入任何卡片，导致评分虚低 | `_updateQualityDashboard`：`consist` bycat 增加 `'格式问题'`；HTML 卡片标题改为"规范/格式" |
| 评分公式 `100-pending*2` 过严（INFO级提示也扣分，50条即归零） | 改为 `100-errors*4-warns*2`，INFO级不扣分 |
| 交叉引用卡片"全部正常"硬编码，不随实际修复情况更新 | HTML 改为 `已修复 <span id="crossrefFixed">0</span> 个`；JS 增加 `crossrefFixed` 更新 |

---

## Recent fixes (2026-04-24) — 第九批：预览灰色背景 + QA/交叉引用链路全面修复（已完成）

### A. docx-preview 类名升级导致的灰色背景

**根因**：`docx-preview` 库当前版本实际渲染的类名为 `.docx-rendered-wrapper`（wrapper）和 `section.docx-rendered`（页面），而 `web/index.html` CSS 选择器写的是旧版 `.docx-wrapper` / `section.docx`。所有覆盖规则全部失效，库默认背景色 `rgb(128,128,128)` 未被覆盖，产生明显灰色侧边。

**修复**（`web/index.html` L461-466）：在每条 CSS 规则上追加新类名选择器，同时保留旧版以兼容：
- `.docx-wrapper,.docx-rendered-wrapper` — wrapper 透明背景
- `section.docx,.docx-rendered-wrapper>section.docx-rendered` — 白色背景 + 轻柔阴影
- 暗色主题同步追加 `section.docx-rendered` 选择器

同时将 `.doc-viewport` 背景从 `#fff !important` 改回 `#ececec`，恢复白色页面与浅灰衬底的层次感。

### B. QA 检查链路全面修复

**三个根因**：

| 根因 | 位置 | 修复 |
| ---- | ---- | ---- |
| `DocumentChunker` 访问 `elem.text`，但字段名是 `elem.content` | `core/performance.py:93` | `.text` → `.content` |
| `runQA()` 传 `page.innerHTML`（docx-preview HTML 无 `<h1>`-`<h6>` 标签），所有标题被解析为 `PARAGRAPH`，`in_ref_section` 永不为 `True` | `web/index.html:runQA()` | 改用 `docContents[fn]`（后端 openFile 解析的结构化元素，含正确的 `h1`/`h2`/`h3` 类型）重建 HTML |
| `categories` 列表缺少 `'crossref'` | `web/index.html:runQA()` L2119 | 补入 `'crossref'` |

**验证结果（样本文件 `南海鸢乌贼捕捞量智能反演文献综述.docx`）**：

| 漏检 | 修复后 |
| ---- | ------ |
| `立生` 错别字 | 检出 |
| `他门` 错别字 | 检出（2 条） |
| `Chl-a高于0.18 ug/L` 单位错误 | 检出（2 条） |
| `SST范围主要在27–28 °C之间` 空格 | 检出（4 条） |
| `包括海流速度和涡旋的发生 研究表明，` 句间空格 | 检出 |

### C. 交叉引用检查链路全面修复

**根因 1**：`runXRef()` 同样传 `page.innerHTML`，与 QA 同病。修复同 B：改用 `_buildQAHtml(fn)` 结构化 HTML。

**根因 2**：`app.py:runXRef` 是一个完全独立的旧版简单正则实现，**从未调用 `core/crossref_engine.py`**，只能检测 `<h1>`-`<h3>` 标题和图/表引用，无法识别 `[1]`-`[10]` 参考文献。

**修复**：完全重写 `app.py:runXRef`，改为调用真正的 `crossref_engine.py`：
1. 用与 `runQA` 相同的 HTML→DocumentModel 解析路径
2. 调用 `TargetScanner` + `RefPointScanner` + `CrossRefMatcher`
3. 将 `CrossRefStatus` 映射为前端期望的 `valid/dangling/unreferenced`

**验证结果**：

| 指标 | 修复前 | 修复后 |
| ---- | ------ | ------ |
| 识别 targets 数 | 7（全为标题） | 13（7 标题 + 10 参考文献 [1]-[10]）|
| 有效引用匹配 | 0 | 68 |
| 悬空引用 | 0 | 2 |
| 未引用目标 | 0 | 3 |

**新增全局函数**：`_buildQAHtml(fn)` — 从 `docContents[fn]`（后端 round-trip 格式，`type`/`text` 字段）重建保留标题层级的 HTML，供 `runQA` 和 `runXRef` 共用。

---

## Recent fixes (2026-04-24) — 第八批：预览阴影清洗 + 交叉引用参考文献识别

### A. 预览区侧边阴影修复

**根因**：`.doc-page` 和 `section.docx` 的 `box-shadow` 包含 `0 8px 32px rgba(0,0,0,.08)`，其 x-offset=0、blur=32px，使阴影在左右两侧各扩散 32px（占 48px padding 的 67%），在 `#ececec` 衬底上产生约 `#d9d9d9` 的明显深灰条带，即用户所见"深灰色竖边/阴影框"。

**修复**：`web/index.html` 两处 `box-shadow` 改为 `0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.05)`——blur 从 32px 降至 16px，侧向扩散从 32px 降至 16px，opacity 从 8% 降至 5%，阴影偏向下方，侧边视觉消失。

| 位置 | 改动 |
| ---- | ---- |
| `web/index.html` L422 `.doc-page` | `0 8px 32px rgba(0,0,0,.08)` → `0 4px 16px rgba(0,0,0,.05)` |
| `web/index.html` L463 `.doc-page.is-docx section.docx` | 同上 |

### B. 交叉引用参考文献扫描修复

**根因**：`TargetScanner._try_match_reference` 要求 `ElementType.REFERENCE`，但 docx 解析将 `Normal` 样式的参考文献条目分配为 `ElementType.PARAGRAPH`；同时该方法要求文本以 `[N]` 开头，而实际参考文献以作者姓名开头（编号由 Word 字段隐式维护）。结果：所有文内引用 `[1]`–`[10]` 均被报告为"悬空引用"或被去重静默丢弃。

**修复**：`core/crossref_engine.py` — 在 `TargetScanner` 中增加参考文献节识别：

1. 新增 `REF_SECTION_PATTERN = re.compile(r"参考文献|references?\b|bibliography", re.IGNORECASE)` 类常量。
2. 重写 `scan()` 方法，在遍历时追踪 `in_ref_section` 状态：见到"参考文献"标题后进入参考文献节，对后续非空段落按出现顺序分配序号 `[1]`、`[2]`……并创建 `RefTarget`；若文本本身有显式 `[N]` 前缀则用显式编号。
3. 标题遇到其他非参考文献标题时退出参考文献节，恢复正常章节检测。

**验证结果（样本文件 `南海鸢乌贼捕捞量智能反演文献综述.docx`）**：

| 指标 | 修复前 | 修复后 |
| ---- | ------ | ------ |
| 识别参考文献目标数 | 0 | ✅ 10（`[1]`–`[10]`） |
| 文内引用 VALID | 0 | ✅ 68 |
| 文内引用 DANGLING | 34+ | ✅ 0 |

回归测试：`tests/unit/test_qa_enhancement_regression.py` 9/9 通过。

---

## Recent fixes (2026-04-23) — 第七批：导出改"Clone + 橡皮擦" + 预览 UI 清洗

> 背景：第六批 E2E `mismatch_count=0` 但用户肉眼打开仍发现 1.5 倍行距、首行缩进 2 字、交叉引用全丢。根因：`docx.js` 从零重建 OOXML 无法覆盖完整 Word 特性；而且重建路径的段落签名对比只能抓结构性字段，抓不到 pPr-level 细节与 field / bookmark。结论：**放弃重建，改为"复印原 docx + 在复印件上做文本替换"**。

### A. 导出方案：Clone + 橡皮擦 + 可选 Fields.Update

**核心原则**：导出文件 = 原 `.docx` 整包拷贝 + 在 `word/document.xml` 上把"用户采纳过的原文"替换成"建议"，其余 xml（styles/numbering/theme/rels/media/fontTable/customXml/footnotes/comments…）一字不动。

| 层 | 目的 | 改动位置 | 关键点 |
| -- | ---- | -------- | ------ |
| ① 采纳记录 | 知道要替换哪几处 | `web/index.html` 新增 `tabAcceptedEdits[tab.name]: [{original, suggestion}, ...]`；`_markIssueAccepted(i)` 里 push `{q.hlText, q.suggestion}`，去重、跳空/同值 | 内存状态，不上 Supabase；刷新页面即丢，符合"本次会话"语义 |
| ② Clone 导出 | 保留全部源 Word 特性 | `web/index.html` 重写 `exportDocAsDocx(tab)`：`.docx/.doc` 且有 `docxBuffers[tab.name]` 时走 clone；JSZip 打开 → 扫 `<w:p>` 的 `<w:t>`（跳过 `<w:instrText>` 域代码）→ 对每条 edit 做 `indexOf` → 跨 run 替换 | 跨 run：一个 run 承接 suggestion，其余 run 去掉命中 slice；w:space="preserve" 保留首尾空格 |
| ③ 刷域增强 | 采纳导致"图 1 → 图 2"等编号/TOC 需重算 | `app.py` 新增 `refreshDocxFields`（PowerShell + Word COM 跑 `Fields.Update()` + `TablesOfContents.Update()`；回退 LibreOffice headless 转档）；`web/flask_app.py` 加路由 `/api/refreshDocxFields`；前端导出后 `try` 调，失败静默 fall through | 两端都没有 Office 引擎时返回 `error_code: NO_OFFICE_ENGINE`，前端继续用客户端 blob，不报错 |

**非目标（明确不做）**：
- 不对齐段落数/章节数/样式表——本来就是源文件
- 不清理第六批留下的 `_parse_docx` styles 提取、`_runFont` 回填、styles.xml 后处理——作为死代码保留，降低回滚成本
- 不做"采纳 = 实时改源 buffer"——只在导出时应用，保证 QA panel 可反复撤销/重新运行

**Fallback 链**：
1. `.docx/.doc` + 有 `docxBuffers` → Clone 路径（新）
2. Clone 失败（JSZip 解析错 / `document.xml` 缺失 / 未知异常）→ 自动回到老 `exportDocAsDocxRebuild()`
3. `.txt/.md/纯 HTML` → 一开始就走老 rebuild（没源可 clone）

**匹配失败语义**：edit 在文档里找不到（原文早已被改、或文字被域代码打断切碎）→ 记入 `skipped` 计数，toast 显示"应用 X 处，Y 处未匹配"；不抛错、不阻止导出。

### B. 预览区 UI 清洗（参照截图：纯净白页 + 浅灰衬底 + 四角 Word 文本边界角标）

现状（`web/index.html` ~L400-420）：
- `.doc-viewport` 用 `background: #f2f2f7 + radial-gradient` 点状底纹（显脏）
- `.doc-page` 顶部有 `border-top: 3px solid var(--accent)`（蓝色粗边，侵入感强）
- 没有 Word 文本边界角标

目标（与截图一致）：
- 衬底改成纯色浅灰（`#ececec` 级别），**去掉** `radial-gradient` 点阵
- 去掉顶部 3px 蓝线，边界只留柔和阴影
- 新增 **Word 风四角文本边界角标**：在 `.doc-page` 的文本区内侧四角画 L 形角标（灰色、~20px 臂长、~1.5px 线宽），视觉上等同 Word 的"显示文本边界"
- 角标实现：`::before` + 多段 `background-image`（内嵌 SVG data URI）+ `background-position: top left / top right / bottom left / bottom right` + `no-repeat`；或一次性 4 个绝对定位子 div。倾向前者（零 DOM 侵入）
- 暗色主题：衬底 `#111113` 保持，角标颜色改为 `rgba(255,255,255,.25)`
- `.doc-page.is-docx` 分支同步去掉 border-top、打上同款角标（docx-preview 的 `section.docx` 外层不方便套，这轮只给非-docx-preview 容器加）

**不改**：
- `.doc-page` 的宽度/padding/字体栈（680px / 72 80 80 / SimSun + line-height 1.85）——这些是内容区本身，与纯 UI 装饰无关
- `[data-theme=dark]` 的文字颜色、代码高亮等

### C. 采纳撤销（per-issue + 全部）

**为什么现在可以放心做撤销**：Clone 路径下 `docxBuffers[fn]` 从头到尾不变，`tabAcceptedEdits[fn]` 只是内存里的采纳清单——"撤销"底层等于"从清单里删掉一条"，不涉及还原文件。

**采纳时的改动**（比当前多几步）：
- 高亮 span 的 `data-issue-id` 不删，**加一个** `data-accepted-id`（便于撤销时重新定位）
- span 的 class 从 `hl-error/warn/info` 换成 `hl-accepted`（浅绿下划线，视觉上和"待处理"的黄/红高亮区分开）
- `q.status='accepted'` 的同时把 `{original: q.hlText, suggestion: q.suggestion}` push 进 `tabAcceptedEdits[fn]`
- 右侧卡片加 `.accepted` class（现有），新增"↩ 撤销"按钮

**两处撤销入口**：
1. **右侧面板**：
   - 每张已采纳卡片上 `[↩ 撤销]` 按钮
   - 顶部批量栏在现有的"全部采纳/全部忽略"旁加 `[↩ 撤销所有采纳]`
2. **文章内**：
   - 鼠标悬停"已采纳"高亮（`.hl-accepted`）时弹 tooltip，含 `[↩ 撤销采纳]` 按钮
   - 避免双击冲突（双击在 contenteditable 里会选词，不好占用），用 tooltip 按钮更稳

**单条撤销 `undoAcceptedIssue(i)` 的步骤**：
1. `const span = document.querySelector('[data-accepted-id="${i}"]')`
2. `span.textContent = q.hlText`（恢复原文；`q.hlText` 从头到尾没变，因为采纳时改的是 span 的 textContent，不是 q 对象）
3. span 的 class 换回原来的 `hl-error/warn/info`；删 `data-accepted-id`；保留 `data-issue-id`
4. `q.status = 'pending'`；右侧卡片 `.accepted` → 去掉
5. 从 `tabAcceptedEdits[fn]` 里删除对应 `{original, suggestion}` 项
6. `showToast('已撤销采纳')`；`checkAllDone()` 重算"是否全部处理完"

**全部撤销 `undoAllAcceptedIssues()`**：遍历 `currentQAData.filter(q=>q.status==='accepted')` 逐条调 `undoAcceptedIssue`；或更暴力——清空 `tabAcceptedEdits[fn]` + 按 `docxBuffers[fn]` 重渲染预览（这个更彻底，但会把用户在预览里的手动编辑也一起抹掉，**不选**）。

**边界语义**：
- "撤销采纳"只恢复到"采纳那一刻的原文"，不管之后的手动 contenteditable 编辑——手动编辑用浏览器 `Ctrl+Z`
- 如果用户采纳 → 手动打字又改了一遍那段 → 点撤销，span 还能定位（`data-accepted-id` 仍在），textContent 会覆盖回原文；手动改的内容丢失，属预期
- 如果撤销后用户再次运行 QA，之前那条 issue 可能被重新检出 → 正常 pending 状态，用户再次采纳即可

**非目标**（明确不做）：
- 不做 Ctrl+Z / Ctrl+Y 操作栈（档位 3）
- 不做"撤销"的撤销（redo 采纳）
- 不把采纳历史持久化——刷新页面清空所有状态，符合"每次打开重新 QA"的语义

### 全量改动（第七批）

| 位置 | 修改 | 作用 |
| ---- | ---- | ---- |
| `web/index.html` CSS | `.doc-viewport` 去 radial-gradient 点阵 → 纯色 `#ececec`；`.doc-page` 去 3px 蓝线；新增 `::before` SVG data URI 四角 L 形角标（明/暗色主题） | 预览区 UI 清洗（B） |
| `web/index.html` | `tabAcceptedEdits` 状态变量；`_markIssueAccepted` 推送 edit 对、动态加"↩ 撤销"按钮；`acceptIssue/acceptSuggestion` 改写 span class 为 `hl-accepted` + 保留 `data-issue-id` + 加 `data-accepted-id` | 采纳状态追踪（A-①+C） |
| `web/index.html` CSS | `.hl-accepted`（绿色下划线）；`.btn-undo-all` | 已采纳视觉区分 |
| `web/index.html` HTML | batchBar 新增"↩ 撤销采纳"按钮；issue 卡片渲染模板增加"↩ 撤销"按钮（accepted 状态时显示） | 撤销入口 UI（C） |
| `web/index.html` JS | `undoAcceptedIssue(i)` / `undoAllAcceptedIssues()`：还原 span class、textContent、从 `tabAcceptedEdits` 移除对应项、重置卡片状态 | 撤销逻辑（C） |
| `web/index.html` JS | `_applyAcceptedEditsToDocXml(xmlStr, edits)`：扫 `<w:t>` 节点（跳过 `<w:instrText>`），支持跨 run 匹配替换，未匹配计入 skipped | XML 文本替换核心（A-②） |
| `web/index.html` JS | `exportDocAsDocxClone(tab)`：JSZip clone 源包 → 应用 edits → `_tryServerRefreshFields` → saveAs | Clone 路径导出（A-②） |
| `web/index.html` JS | `exportDocAsDocx(tab)`：docx/doc + 有 buffer → clone 路径；否则 → `exportDocAsDocxRebuild`（原函数改名） | 路由入口（A-②） |
| `web/index.html` JS | `_tryServerRefreshFields(blob)`：blob → base64 → `/api/refreshDocxFields` → 返回刷新后 blob；失败静默返回 null | Fields 刷新前端（A-③） |
| `app.py` | `refreshDocxFields(docx_b64)`：Word COM（PowerShell `Fields.Update()` + `TablesOfContents.Update()`，120s 超时）→ LibreOffice headless 重存 → `error_code: NO_OFFICE_ENGINE` | Fields 刷新后端（A-③） |
| `web/flask_app.py` | `/api/refreshDocxFields` 路由 | A-③ HTTP 接口 |
| `tests/test_batch7_clone_export.py` | 14 个单元测试：XML 替换算法 + 整包 clone + 真实样本（含 "undo=无 edit=原文" 验证） | 算法回归 |
| `tests/test_batch7_refresh_fields.py` | 9 个测试（8 通过 1 跳过）：后端 `refreshDocxFields` + Flask 路由降级行为 | A-③ 回归 |
| `tests/e2e/test_batch7_e2e.py` | 6 个 Playwright E2E：clone 导出（注入 edit / 不存在 edit / 撤销后导出）+ 采纳/撤销 UI 行为 | 浏览器全链路 |
| `tests/e2e/conftest.py` | `_wait_url_ready` 增加捕获 `(OSError, TimeoutError)`，修复 Python 3.14 下 socket.timeout 不再被 URLError 包装的兼容问题 | CI 稳定性 |

### 关键设计点（第七批）

- **Clone 路径不碰源 buffer**：`docxBuffers[fn]` 始终是原始上传字节，`tabAcceptedEdits[fn]` 只是清单，"撤销"等于从清单删除一条，无需还原文件
- **跨 run 替换策略**：找到第一个包含 original 起点的 `<w:t>` 节点，写入 `before + suggestion + afterInNode`；后续属于 match 范围的节点只保留 match 结束后的尾部，其余置空；`xml:space="preserve"` 保留首尾空格
- **instrText 保护**：域代码所在的 `<w:r>` 含 `<w:instrText>` 子节点，整个 run 跳过，避免把"TOC \o 1-3"等域指令文本当做可替换内容
- **Fields.Update PowerShell 脚本**：`$ErrorActionPreference='Stop'` 使任何 COM 错误转为终止异常；`$w.Quit()` 放 `finally` 保证进程不泄漏；120s 超时防 Word 卡死
- **降级语义**：无 Office 引擎 → `NO_OFFICE_ENGINE` → 前端用 clone blob 直接下载，体验无差异；有 Word 时域编号/目录页码自动更新
- **Python 3.14 兼容**：`socket.timeout`/`TimeoutError` 在 3.11+ 已经是 `OSError` 子类但不再被 urllib 包装成 `URLError`；conftest 的 `_wait_url_ready` 必须显式 catch `(OSError, TimeoutError)` 才能在 CI 稳定运行

### 测试覆盖结果

| 测试集 | 数量 | 结果 |
| ------ | ---- | ---- |
| `test_batch7_clone_export.py` | 14 | 全通过 |
| `test_batch7_refresh_fields.py` | 9 | 8 通过 / 1 跳过（无 Office 引擎，预期） |
| `e2e/test_batch7_e2e.py` | 6 | 全通过 |

---

## Recent fixes (2026-04-23) — 第六批：导出排版深度回归

> 起因：用户发现 Web 导出的 `.docx` 排版与源文件明显不一致（段落丢失、页边距变 3cm、标题错位），但旧 E2E `tests/e2e/test_export_docx_regression.py` 却通过。根因：测试对比维度不够 + pipeline 漏关键元数据。最终 E2E `mismatch_count=0` 通过，80 段 / 8 section 全对齐。

### 全量改动

| 位置 | 修改 | 作用 |
| ---- | ---- | ---- |
| `app.py:_parse_docx` | 保留空段、补 `right_indent_twips / line_spacing_twips`，run 级补 `font_ascii / hAnsi / eastAsia / cs`，新增 `section_break` 标记（扫 `w:pPr/w:sectPr`） | 后端 round-trip 元数据覆盖全段落 |
| `app.py:_parse_docx` | 返回值从 `(elements, sections)` 扩展为 `(elements, sections, styles)`，提取 `Normal / Heading 1-3` 的 `font_name / size / bold / italic / rfonts`；`openFile` JSON 响应带 `styles` 字段 | 支撑前端 styles.xml 后处理 |
| `web/index.html` | 新增 `docStyles[fileKey]`，`_fetchRoundTripDocMeta` 捕获 `j.styles` | 前端缓存源文档样式表 |
| `web/index.html:exportDocAsDocx` | 重写：`.docx/.doc` 导出前强制重取 round-trip 元数据；无 `fmt+section` 则阻止导出；`style` 透传（`Normal` 除外）；`first_line/left/right` 显式 0 会写入；空段 `children=[]`；按段落 `section_break` 切 Document `sections` | 输出与源结构对齐 |
| `web/index.html:_runFont` | 只转发源 run 显式存在的 `font_ascii/hAnsi/eastAsia/cs`，**不再**用 `font_name` 回填 `ascii/hAnsi/name`——docx.js 会把 `font.name` 展开到所有四个 rFonts 通道，污染源里留空的字段；只有当源 run 完全没 rFonts 才退回 `font_name` 填 ascii+hAnsi | 修复 eastAsia 被改成 Times New Roman 的 848+127+1=976 条差异 |
| `web/index.html:_buildRun` | `bold/italic` 由 `=== true` 改为 `!= null` 三态转发，让 docx.js 生成 `<w:b w:val="0"/>`（属性名是 `italics` 非 `italic`） | 修复 1146+359=1505 条 `italic/bold: false → null` 差异 |
| `web/index.html` | JSZip 后处理同时处理 `word/document.xml` 和 `word/styles.xml`：前者合并 docx.js 自动追加的"空 sectPr 段"到前一段 `pPr`；后者按 `docStyles` 注入/覆盖 `Normal + Heading 1-3` 的 `rPr`（rFonts + sz + szCs + b/bCs + i/iCs）；`Normal` 缺失时新建 `<w:style w:default="1">` | 让 python-docx round-trip 的 `paragraph.style` 能解回 `Normal`、heading 字号跟源一致 |
| `web/run_web.py` | 所有静态响应加 `Cache-Control: no-store, no-cache, must-revalidate` | 避免浏览器缓存旧 `index.html` |
| `tests/e2e/test_export_docx_regression.py` | 新增 run 级 rFonts、段落 `right_indent`、`non_empty_paragraph_count`、`styles`（Normal/Heading 1-3）签名维度；加 `@pytest.mark.smoke`；上传后加前置断言：必须拿到 `fmt + docSections` | 漏检根因阻断 |
| `tests/e2e/conftest.py` | `DEFAULT_SAMPLE_DOC` 改为候选列表（优先无后缀源文件、回退 `_导出` 兼容旧运行） | 旧 sample 删除后 E2E 仍能自动选到源文件 |
| `tests/test_core_functions.py::TestParseDocx` | 兼容 `_parse_docx` 新的三元组返回 | 保留旧单元测试 |
| `.github/workflows/tests.yml` | PR gate 追加 `pytest tests/e2e/test_export_docx_regression.py` 一步 | 导出回归纳入强制门禁 |

### 比对结果轨迹（`samples/南海鸢乌贼捕捞量智能反演文献综述.docx`）

| 轮次 | paragraphs | non_empty | sections | mismatch_count | 说明 |
| ---- | ---------- | --------- | -------- | -------------- | ---- |
| 初始 | 80 vs 66 | 66 vs 46 | 1 vs 1 | 50 | 页边距被改 3cm、段落断裂、空段全被丢 |
| v3（元数据打通后） | 80=80 | 66=66 | 1 vs 8 | 50 | 多 section、runs 字体不一致 |
| v4（section 切分） | 80 vs 87 | 66=66 | 8=8 | 50 | 每个非末 section 多"sectPr 空段" |
| v5（sectPr 合并） | 80=80 | 66=66 | 8=8 | 50 | 剩 1 × `style_format` + 49 × `paragraph_format`（主因：无 `Normal` 样式） |
| v6（styles.xml 后处理 + `_runFont/_buildRun` 修复） | 80=80 | 66=66 | 8=8 | **0** | 全对齐 |

### 关键设计点速记

- **docx.js `font.name` 是污染源**：传 `font: {name: 'Times New Roman'}`，docx.js 会把 ascii/hAnsi/eastAsia/cs 四个通道全写成该值，覆盖源里刻意留空的通道。只能按源 rFonts 逐通道透传，`font.name` 仅作为"源 run 完全没 rFonts"时的最后兜底（只填 ascii+hAnsi，不碰 eastAsia/cs）。
- **docx.js 样式表不含 `Normal`**：直接生成的 `word/styles.xml` 缺 `<w:style w:styleId="Normal" w:default="1">`，于是 python-docx 读 `paragraph.style.name` 全部返回 `None`，签名对比一把刷 49 条差异。必须用 JSZip 打开 zip 后注入 `Normal`，并覆盖 Heading 1/2/3 的 `rPr`（docx.js 的 Heading 2/3 默认 26/24，源是 30/28）。
- **`bold/italic: false` 是显式信号**：Word 在段落样式带粗/斜时允许 run 级显式关掉（`<w:i w:val="0"/>`），python-docx 读回 `False`（≠ `None`）。旧逻辑只转发 `=== true` 会把这些显式 false 丢失。改为 `!= null` 三态转发后 docx.js 会写 `<w:i w:val="false"/>`。docx.js v8 的 TextRun 属性名是 `italics` 不是 `italic`（坑点）。
- **docx.js Document `sections` 副作用**：每个非末尾 section 会自动追加一个只含 `<w:sectPr>` 的空段，必须在 blob 生成后用 JSZip 打开 `word/document.xml`，把这个 sectPr 合并回前一段的 `pPr` 并删除空段，才能对齐 Word 原生的"段尾携带 sectPr"结构。
- **浏览器缓存是隐形坑**：`Ctrl+F5` 在某些场景（Service Worker/HSTS）仍拿旧文件；所以 `run_web.py` 给所有静态响应显式打 `no-cache`，排障时先确认新代码真的到了浏览器。
- **E2E 必须前置断言 round-trip 元数据**：上传后先校验 `fmt_count === content_count && section_count > 0`，不然后端元数据漏一个字段，整个导出链路会悄悄退回空壳模式，测试看到段落数对上就误报通过（这就是旧 E2E 跑 `_导出.docx` 显示 mismatch=0 但真实源文件差 50 的原因）。

---

## Recent fixes (2026-04-22) — 第五批

| Issue | Fix location | Detail |
| ----- | ------------ | ------ |
| 模板上传后规则全显示 null（问题4） | `app.py` + `web/index.html:handleTemplateUpload` | 后端新增 `_extract_docx_format_rules()` 用 python-docx 直接提取格式参数（从 `w:rFonts[@w:eastAsia]` 读中文字体、扫描前 300 段提取标题/正文/页边距），随 `uploadTemplate` 响应附带 `format_rules`；前端收到后直接设 `_aiParsedRules` 并渲染，跳过 AI 环节 |

### 第五批关键设计点

- 根本原因是 `runAIParse` 把"已上传模板：xxx.docx，请点击…"当描述文本传给 AI，AI 找不到格式信息全返回 null；修复路径是把信息提取下沉到后端，不依赖 AI
- 中文字体必须从 XML `<w:rFonts w:eastAsia="宋体"/>` 读，`run.font.name` 只返回西文字体名（如"Times New Roman"）
- PDF 模板无法用 python-docx 解析，回退到旧提示流程（用户手动输入描述再 AI 解析）

---

## Recent fixes (2026-04-22) — 第四批

| Item | Location | Status |
| ---- | -------- | ------ |
| 问题5 自动化回归测试脚本 | `tests/e2e/test_export_docx_regression.py` | 已完成（可自动起服务→登录→上传→导出→比对） |
| pytest e2e marker | `pytest.ini` | 已新增 |
| 回归产物落盘 | `tests/artifacts/phase5_export_compare_report.json`, `tests/artifacts/phase5_exported.docx` | 已生成 |
| 问题5 二次修复（页边距/首行缩进/段前后距） | `web/index.html:exportDocAsDocx` | 已修复 |
| 回归测试通过 | `tests/e2e/test_export_docx_regression.py` | 通过 |

### 第四批说明

- 测试脚本默认走 `samples/南海鸢乌贼捕捞量智能反演文献综述_导出.docx`，并严格比较导出前后排版签名（section、paragraph、runs）。
- 登录凭据不写入代码：脚本支持通过环境变量注入测试账号：`WC_TEST_EMAIL`、`WC_TEST_PASSWORD`。
- 本轮按 `tests/artifacts/phase5_export_compare_report.json` 中的 mismatch 明细逐项修复，E2E 回归测试已通过。

---

## Recent fixes (2026-04-21) — 第三批

| Issue | Fix location | Detail |
| ----- | ------------ | ------ |
| 某些 docx 打开后预览变成黑底白字（问题 2） | `web/index.html` 预览区 CSS | `.doc-page.is-docx>section.docx` 的 `background` / `color` 改为 `!important`；新增 `[style*="background"]{background:transparent !important}` 规则清理段落级 inline 深色背景 |
| 规则检查按钮不真正查文档（问题 6）| `web/index.html:runQA()` | 从读取硬编码 `fileQaData` mock 改为 `async` 调用 `WC_API.runQA(content, categories)`；按 `severity/category/location_text` 做字段映射；后端失败时回退到本地示例 |
| 本地规则覆盖不足，很多标点/格式错误只能靠 AI 找到（问题 6）| `core/punctuation_checker.py`（新建）| 新增 `PunctuationChecker`：中英文标点混用、连续重复标点、中英文间缺空格、全角数字、括号/引号配对、连续重复汉字（2字低置信 / 3字高置信）|
| QAEngine 未串联新 checker | `core/qa_engine.py` | 导入并注册 `PunctuationChecker`；`_check_sequential` 处理 `"format"` 类别；默认 categories 增加 `"format"` |
| runQA 默认只查 typo/consistency/logic | `app.py:runQA` | 默认 `categories_str` 增加 `"format"` |
| 错别字词库仅 158 条，覆盖面窄（问题 6 追加）| `core/typo_lib.py`（重构）+ `core/data/common_typos.tsv`（新建）| 词库扩充至 **~580 条**：手工整理 550+ 条 TSV（公文/学术写作错别字），重构 typo_lib 为分层加载（curated + tsv + user override + 可选 SIGHAN），自动过滤单字/自映射/含 `/` 等噪声条目，顺带修复旧版"的/地/得"单字误报 |
| 支持项目专有词条扩展 | `core/data/user_typos.tsv`（可选，已 gitignore）| 用户可在此追加或覆盖词条，不影响内置词库升级 |

### 本轮修复的关键设计点（第三批）

- docx-preview 会把文档主题色写入 `section.docx` 的 inline `background-color` 以及通过 scoped `<style>` 注入段落级别样式，特异度可能压过我们的 CSS；所以 `!important` 必须加在 section 和 `[style*="background"]` 两处才能彻底抹平背景
- 设计 `color: var(--text) !important` 只作用在 section.docx 元素本身（不是后代）：`color` 是继承属性，descendants 上 `color:red` 的具名样式会正常胜过继承值，不会破坏文档中合法的局部着色
- 前端 `runQA()` 之前只用 `fileQaData` 做演示数据，这是历史 mock 的遗留；换成真实后端后仍保留它作为 fallback，避免离线 / Flask 没起时点按钮直接崩
- 后端结构 `{severity: 'warning'}` → 前端结构 `{sev: 'warn'}`（三级别名称不同）；`category: 'inconsistency'` → 显示名"数据不一致"；`hlClass` 由 severity 推导（error→hl-error / warn→hl-warn / info→hl-info），无需后端关心
- `PunctuationChecker` 的叠字白名单收录 "爸爸/妈妈/渐渐/慢慢" 等 50+ 合法叠字；三字以上相同汉字必然是输入法连击错误，直接标 ERROR；两字叠字置信度只有 0.35 且白名单外才报，避免刷屏
- 括号配对只在段落内检查（跨段概率极低，避免全文扫描误报）；中英文空格每段最多报 3 条（中文技术文档常大量出现 "用 Python" / "是 AI" 写法，不能每处都弹提示）
- `typo_lib._is_valid_entry` 的过滤规则：单字条目（`的/地/得`等）需上下文才能判断对错，直接进字典会刷屏；`/` 分隔的建议（`象/像`、`的/地/得`）在 TypoChecker 的 `correct_word in text` 判断里永远失败从而永远报错，必须过滤；wrong==right 是自映射无意义。这三条规则让我们在扩展词库时不用担心误报反噬
- TSV 加载顺序：`curated(hardcoded) → common_typos.tsv → user_typos.tsv`，后者覆盖前者。`user_typos.tsv` 不入 git，方便用户给自己项目加专有词而不冲突升级
- SIGHAN 2015 衍生的 347 条 2-gram 对 opt-in：很多"错"形（`回复`、`习惯`、`多有`）本身是合法词，直接纳入会大量误报；默认关闭，通过 `get_all_typos(include_sighan=True)` 显式启用

---

## Recent fixes (2026-04-21) — 第二批

| Issue | Fix location | Detail |
| ----- | ------------ | ------ |
| 导出排版全乱（首行缩进 10 倍过大） | `web/index.html:exportDocAsDocx` | `0.35`（错误系数）→ `0.035`（1pt≈0.035cm）；`firstLineTwips` 独立提取；同步提取 `lineSpacing` |
| 导出缺少页面设置（默认 Letter 纸） | `web/index.html:exportDocAsDocx` | Document sections 加 `page.size`（A4 11906×16838 twips）和 `margin`（上下 2.54cm、左右 3cm） |
| 导出列表项渲染为正文（格式错乱） | `web/index.html:exportDocAsDocx` | 新增 `li` 类型分支，渲染为 `• ` 前缀 + `indent.left:480` 段落 |
| 导出标题无段前/段后间距 | `web/index.html:exportDocAsDocx` | h1/h2/h3 段落加 `spacing.before`/`spacing.after`（h1: 240/120，h2: 200/100，h3: 160/80 twips） |
| 采纳建议文章改了但右侧面板不同步 | `web/index.html:acceptSuggestion` | 读取 `hl.dataset.issueId`，采纳后调用 `_markIssueAccepted(i)` 同步状态和卡片 |
| 右侧面板"采纳"按钮无反应 | `web/index.html:acceptIssue` | 废弃后端 `acceptSuggestion` 往返（text-replace 在已采纳时返回 failure）；改为纯本地 DOM 操作，与文章内采纳逻辑统一 |
| 切标签后高亮 index 错位 | `web/index.html:applyHighlights` | 用 `item.id`（QA 运行时赋值的原始 index）替代循环 `idx`；跳过非 `pending` 状态条目；`restoreTabDashboardState` 改传全量 `qa` 而非过滤后的 `pending` |

### 本轮修复的关键设计点（第二批）

- 导出首行缩进公式：`indent_chars × bSize_pt × 0.035cm/pt ÷ 2.54cm/inch × 1440twips/inch`；旧代码用 `0.35` 导致 3.3 英寸缩进，所有正文段落被推出页面右边
- `acceptIssue` 不应调用后端：后端做 `innerHTML.replace(original, suggestion)`，若文章已在前端采纳，`original === suggestion`，后端检测到无变化返回 `success:false`；且 `page.innerHTML = corrected_content` 会销毁所有 highlight 元素的事件监听，导致后续交互失效
- 新增 `_markIssueAccepted(i)` 共享函数：统一更新 `currentQAData[i].status`、右侧面板卡片 `.accepted` class、toast、`checkAllDone()`，确保两个采纳入口行为一致
- `applyHighlights` 的 `issueId` 必须用 `item.id`：`restoreTabDashboardState` 过去传 `pending`（过滤数组），导致过滤后 idx=0 对应原始 idx=1 的 issue，右侧面板按钮 index 与高亮 `data-issue-id` 不匹配

---

## Recent fixes (2026-04-21) — 第一批

| Issue | Fix location | Detail |
| ----- | ------------ | ------ |
| 导出格式混乱（`<a>` 标签残留） | `web/index.html:exportDocAsDocx` | 新增 `_strip()` 用 DOMParser 剥离 innerHTML HTML 标签，TextRun 只传纯文本；空节点过滤（`.filter(Boolean)`）；rawHtmlContents 兜底 |
| 质量仪表板硬编码假数据 | `web/index.html:openQualityDashboard` | 新增 `_updateQualityDashboard()`，打开弹窗前从 `window.currentQAData` 实时计算各分类问题数、修复数、进度条、质量评分；`refreshQualityData` / `fixAllIssues` 同步对接 |
| AI 测试按钮报 `WC is not defined` | `web/index.html:testAIConnection` | `WC.callAI` → `window.WC_API.callAI` |
| 前端代理转发走系统代理（502/500） | `web/run_web.py` | 新增 `_NO_PROXY_OPENER = ProxyHandler({})` 绕过 Clash/VPN 系统代理，所有 `/api/*` 代理改用该 opener |
| `runQA` categories 序列化错误 | `web/flask_app.py:run_qa` | `categories` list 未 JSON 序列化即传入，改为 `json.dumps(categories)` |
| `runQA` 检查空文档（始终返回 0 issues） | `app.py:runQA` | 解析 HTML/纯文本 content，用 `re.finditer` 逐块提取 h1-h6 / p / li，构建 DocElement 列表填入 DocumentModel |
| `runQA` 序列化字段名错误 | `app.py:runQA` | `i.id` → `i.issue_id`；补充 `location_text` 字段输出 |

### 本轮修复的关键设计点（第一批）

- `_strip(html)` 辅助函数（`index.html`）：`createElement('div').innerHTML = s; return textContent` — 唯一可靠的浏览器端 HTML→纯文本方法，避免正则误删中文
- `run_web.py` 代理必须绕过系统代理：机器如配置了 Clash/VPN 的 `http_proxy`，`urllib.request.urlopen` 会把 localhost 请求路由到代理，导致 502。固定用 `ProxyHandler({})` opener
- `app.py:runQA` HTML 解析用 `re.finditer` 而非按行分割：同一"行"可能含多个块级标签（`<h1>...<p>...`），split 会漏掉后续节点

---

## Recent fixes (2026-04-20)

| Issue | Fix location | Detail |
| ----------------- | ------------------------------------------- | --------------------------------------------------------- |
| 导出文件乱码 | `web/index.html:exportDoc` | 补读 h2/h3/wFont；所有 TextRun 加 `font.name` + `font.eastAsia` |
| 模板上传栈溢出 | `web/index.html:handleTemplateUpload` | btoa 改为 8192 字节分块编码 |
| AI 解析排版规则为桩函数 | `web/index.html:runAIParse/applyAIRules` | 实现 AI 文本→JSON 规则解析及一键填入面板 |
| .doc 文件不显示 | `parsers/dispatcher.py` | 三级回退；前端 `_loadDocFile` 同步改为分块编码 |
| LibreOffice 失败不继续 | `parsers/dispatcher.py` | 失败后 warning + fall through，不再 raise |
| 仪表板数据不持久 | `web/index.html` | `tabQAState`/`tabXrefState` 跨 tab 切换保存/恢复 |
| 首页导航 / 在线状态 | `web/index.html` | 工具栏"首页"按钮；状态栏 30s 轮询在线点 |
| 图片对齐 | `parsers/docx_parser.py` + `web/index.html` | 扫描 `<w:drawing>` 提取图片+对齐；前端加对齐 CSS 和浮动工具栏 |

### Supabase 架构优化 & 导出增强（2026-04-20）

#### Supabase 前端直连

`window.WC_API` 中以下方法现在直接调用 Supabase JS SDK，绕过 Flask：

- `getDocumentList` / `saveDocument` / `loadDocument` / `updateDocument` → `documents` 表
- `getUserSettings` / `saveUserSettings` → `user_settings` 表（upsert on_conflict user_id）
- `getUserTemplates` / `deleteTemplate` → `templates` 表 + Storage
- `getTokenUsage` → `profiles` + `token_logs` 表

新增 `_sbUserId()` 辅助方法（`getSession()` 取当前用户 ID）。未登录或 Supabase 不可用时自动回退到 Flask 路由。

#### Supabase Realtime

`setupRealtimeDocSync()` 订阅 `public.documents` 表变更，加 `filter: user_id=eq.{uid}` 隔离用户，`init()` 启动时调用，文档列表自动刷新。

#### Edge Function — qa-summary

`supabase/functions/qa-summary/index.ts`：Deno 函数，对文档进行四维 AI 质量检查（逻辑/表述/数据/语言），调用豆包 API，`verify_jwt = true`。

部署：
```bash
supabase link --project-ref nzujajuefdsheggulpze
supabase secrets set DOUBAO_API_KEY=<key>
supabase functions deploy qa-summary
```

#### runAIQA() 实现

由桩函数改为真实实现：fetch `qa-summary` Edge Function → 解析逐行建议 → 追加（去重旧条目）到 QA 面板。

#### 导出按格式分流

`exportDoc()` 按 `tab.type` 自动分流：

- `pdf` → `exportDocAsPdf()`：注入 `#printTarget`，`window.print()`，`afterprint` 事件后清理
- 其他 → `exportDocAsDocx()`：原有 docx.js 逻辑

`@media print` CSS：A4 页面，隐藏所有 UI，仅显示 `#printTarget`。

#### 其他

- `app.py`: Doubao key 改为 `os.environ.get("DOUBAO_API_KEY", fallback)`
- `.gitignore` 新建：覆盖 `__pycache__/`、`*.py[cod]`、`.env` 等
- 已追踪的 `.pyc` 文件从 git index 中清除

---

## Deployment notes

### Website deployment progress (2026-04-23)

1. 已明确部署形态：采用纯网页 + 云端后端模式，`pycorrector` / `autocorrect` 均在服务器侧安装与运行，终端用户无需本机安装。
2. 已实现后端 QA 健康检查接口：`/api/qa/health`，可返回 readiness、missing capabilities、自动修复状态等信息。
3. 已实现 QA 硬门禁：`runQA` 在能力未就绪时阻断检查，返回 `QA_CAPABILITY_NOT_READY`，禁止 silently degraded 检查。
4. 已实现服务器侧依赖自动准备（best effort）：未就绪时自动尝试安装 `autocorrect`，并进行重探测。
5. 已加入自动重试与冷却机制：避免频繁重复安装，同时减少"必须手工重启后端"场景。
6. 已完成前端门禁与状态同步：未就绪时禁用 QA 入口，展示缺失能力与服务准备状态。
7. 已上线安装进度 UI（已改文案为服务侧）：展示"QA 服务准备进度"，安装完成提示"刷新页面后继续检查"。
8. 已完成认知对齐：当前服务器环境为 Windows Server（含 nginx + Python 运行中），后续部署 SOP 应按 Windows Server 路线整理，不再按 Ubuntu 假设执行。
9. 当前落地策略：继续沿用已有腾讯云轻量服务器与域名，原地升级项目并续期证书；不在本次文档中展开具体网站操作步骤。
10. **`pycorrector` 已完全移除**（2026-04-24）：因依赖 PyTorch（重量级，不适合服务器自动安装），已从项目中删除。QA 能力层改为仅依赖 `autocorrect`（轻量二进制）+ 规则层。`requirements.txt` 同步移除 `torch/transformers/accelerate/pywebview/PyQt6`。
