# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current status

P6（第十四批）+ 第十三批 已完成并修复（2026-04-26）。

**第十四批（P6）完成内容**：排版规范与 QA 联动（完整实现）。
- **Phase 1 Core（后端）**：新建 `core/format_checker.py`（`FormatRules` + `FormatChecker`）；`QAEngine.check()` 集成 `format_rules` 参数；`runQA` 新增 `elements_json` 结构化元素路径（按字符数加权提取 dominant 字体/字号，真正触发格式检查）；Supabase `user_format_rules` 表（RLS + unique per user）；`saveFormatRequirements` / `loadFormatRequirements` 双存储（Supabase 主 + 本地 JSON fallback）；23 个单元测试全通过。
- **Phase 2 Frontend**："保存为检查规范"按钮 + `_savedFormatRules` localStorage 持久化 + `_checkFormatCompliance()` run 级字体/字号校验 + `runQA()` 合并格式问题；WC_API `saveFormatRequirements` / `loadFormatRequirements` 封装。

**第十三批完成内容**：交叉引用采纳式设计。
- 后端 `runXRef` 新增 `xref_issues` 字段：有效文内引用 → `type="unreferenced"` + `bookmark_name`；悬空引用 → `type="dangling"`；按 `target_label` 去重。
- 前端新增"可采纳引用"子标签页（QA 风格卡片），支持采纳/忽略/撤销。
- 采纳时：`hl-xref-accepted` 绿色下划线高亮 + 写入 `tabXrefAcceptedEdits`。
- 导出时：`_applyXrefEditsToDocXml` 将 `target_label` 替换为 Word REF 字段 XML。
- 回归测试：27/27 通过（新增 5 个 TestBatch13XRefAdoption 测试）。

**用户反馈问题修复（2026-04-26）**：
1. ✅ **精确定位** - `jumpToXRefInText()` 改进：使用 TreeWalker 精确定位【1】等数字，而非整段高亮
2. ✅ **标题排除** - `TargetScanner.scan()` 删除 `_try_match_chapter()` 调用，只有图表/公式/参考文献参与交叉引用
3. ✅ **UI 清洁** - 排版面板删除"应用排版规则"和"设为默认格式"按钮，只保留"保存为检查规范"
4. ⚠️ **已字段化检测** - `_parse_docx:_runs()` 新增 `is_in_field` 标记；需进一步集成到 `runXRef` 过滤逻辑

---

## Next batch（第十四批 P6 之后）

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

### P6：排版规范与 QA 联动（第十四批）

**现象**：用户手工设置排版规范后无法复用；排版检查结果与 QA 问题无关联。

**解决方案**：保存用户的排版规范 → 自动检查 → QA 同步显示。详见 [docs/PLANS/batch14_format_qa.md](docs/PLANS/batch14_format_qa.md)。

**核心改动**：
- 新增 `FormatRules` 数据模型 + `FormatChecker` 检查器
- `saveFormatRequirements()` API 保存规范至 Supabase
- `runQA` 自动加载规范，排版问题归入 format 类别

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

See [BUSINESS.md](docs/BUSINESS.md) for monetization strategy and pricing details.

---

See [CHANGELOG.md](docs/CHANGELOG.md) for detailed fix history（第一至十四批修复记录）and [DEPLOYMENT.md](DEPLOYMENT.md) for deployment notes.

## Test Coverage（回归测试）

`tests/test_batch_regression.py` — 27 个测试，覆盖第一至第十三批所有已修复问题。
**每次修改代码后必须运行此文件**，任何已修复问题回退都会在此处失败。

`tests/test_format_checker.py` — 23 个单元测试，覆盖第十四批 Phase 1 Core（FormatRules + FormatChecker + QAEngine 集成）。

```bash
python -m pytest tests/test_batch_regression.py -v
python -m pytest tests/test_format_checker.py -v
```

| Class | 批次 | 覆盖内容 |
|-------|------|---------|
| `TestBatch1RunQAChain` | 第一批 | runQA 返回 location_text/rule_id/checker；HTML 内容被真正解析 |
| `TestBatch3PunctuationChecker` | 第三批 | 句间空格/ug-L/摄氏度/中英文空格默认关闭/typo_lib 他门立生 |
| `TestBatch8CrossRefReferenceScan` | 第八批 | TargetScanner 识别参考文献节 [1]-[N]；RefPointScanner 文内引用；CrossRefMatcher 有效匹配 |
| `TestBatch9QAXrefChainFix` | 第九批 | DocElement.content 字段名；runQA 含 crossref；runXRef 返回 element_index；DocumentChunker.content |
| `TestBatch10FalsePositiveReduction` | 第十批 | 南海海表/生物物理不误报；真实重复字仍检出；AutoCorrect 标题；CJK空格关闭无噪音 |
| `TestCrossRefNoDuplicateMatches` | 第九/十批 | matches 含 element_index；app.runXRef 序列化完整 |
| `TestBatch13XRefAdoption` | 第十三批 | runXRef 返回 xref_issues；字段结构完整；有效引用为 unreferenced 类型；bookmark_name 存在；target_label 去重 |
| `TestFormatRulesModel` / `TestFormatCheckerNoIssues` / `TestFormatCheckerFontMismatch` / `TestFormatCheckerSizeMismatch` / `TestFormatCheckerRateLimiting` / `TestQAEngineFormatRulesIntegration` | 第十四批 | FormatRules 序列化；FormatChecker 字体/字号检测；MAX_PER_TYPE 限速；QAEngine 集成 |
