# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
## 中盘阶段执行策略（gstack + superpowers）

1. 新批次先 `/office-hours`，明确范围、非目标与规则层/AI层边界。
2. 改 `app.py`、`core/qa_engine.py`、`web/index.html` 前必须先 `/plan-eng-review`。
3. 功能完成先 `/qa-only`，收口再 `/qa`。
4. 提交前固定 `/review`，关注行为回归与接口兼容，不做风格争论。
5. 每次改动后必须跑 `tests/test_batch_regression.py` 与 `tests/test_format_checker.py`。
6. 批次合并前跑 `/ship`；合并后用 `/document-release` 同步文档状态。
7. 每周至少一次 `/retro`，追踪返工热点与漏测模式。
## Current status

**第二十批（20A + 20B）已完成（2026-05-07）**

**20A — 自定义排版能力补齐**
- 格式面板补 H4 字体/字号、H1-H4 编号格式字段
- 行距从单值升级为"模式 + 数值"（lineSpacingMode / lineSpacingValue）
- FormatRules 模型接住 H4 和行距模式，QA 链路完整消费
- 计划链接：`PLANS/batch20a_custom_format_editor_upgrade.md`

**20B — AI 解析排版改进 + 行距检查**
- `runAIParse()` 回归修复：inner try-catch、no_thinking、max_tokens:4000
- Primary + Fallback prompt 重写：notes 专用规则、8 条抽取指令
- `_sanitizeAIParseRules()`：lineHeight > 5 映射 exact 模式修复；lineSpacingValue 无 mode 时自动推断
- `_collectFormatRules()`：去掉硬编码默认值（黑体/宋体/16/1.5/multiple），未填字段不再触发误报
- `app.py:callAI()`：支持 `no_thinking` 标志，DeepSeek 可按需关闭推理模式
- `FormatChecker`：新增行距检查（SINGLE/1.0 默认值跳过，上限 5 条）
- 计划链接：`PLANS/batch20b_ai_parse_template_alignment.md`

全量测试通过：`tests/test_format_checker.py`（33）+ `tests/test_batch_regression.py`（50）+ JS `test_ai_parse_normalize.js`（17）= **83 Python + 17 JS passed**

- 完成项细节统一维护在 [CHANGELOG.md](docs/CHANGELOG.md)。

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

## Dev startup checklist (Windows/PowerShell)

### Agent execution rule (Codex / Claude Code)

- When user asks to restart frontend/backend, always run the one-click script first.
- Command (from repo root):
  ```bash
  powershell -ExecutionPolicy Bypass -File .\scripts\dev-start.ps1
  ```
- Do not start `flask_app.py` and `run_web.py` manually unless script fails.
- After running script, confirm:
  - backend is listening on `http://127.0.0.1:5000`
  - frontend is reachable on `http://127.0.0.1:8081/`
- If script fails, report exact error and then fall back to manual restart.
- Token/time optimization rule:
  - For restart requests, do not run multi-round exploratory diagnostics before executing the script.
  - Use at most one verification pass after script execution (ports/HTTP).
  - Only run deep troubleshooting when script returns failure or health check fails.

Use this exact order when restarting services to avoid flaky startup:

1. Open two terminals and go to `G:\开发项目\wordcraft-pro\web`.
2. In terminal A, start backend:
   ```bash
   python flask_app.py
   ```
3. In terminal B, start frontend:
   ```bash
   python run_web.py
   ```
4. Open main page:
   - `http://127.0.0.1:8081/`
   - or `Start-Process "http://127.0.0.1:8081/"`
5. Restart rule: stop old processes with `Ctrl + C` first, then start backend and frontend again.

One-click startup script usage:

```bash
# From repo root
powershell -ExecutionPolicy Bypass -File .\scripts\dev-start.ps1
```

If script execution is blocked by policy, use the command above (temporary bypass for this run).

Quick troubleshooting:

```bash
# Check whether ports are occupied
Get-NetTCPConnection -LocalPort 5000,8081 -State Listen

# If occupied, inspect process IDs
Get-NetTCPConnection -LocalPort 5000,8081 | Select-Object LocalPort,OwningProcess,State
Get-Process -Id <PID>
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

See [CHANGELOG.md](docs/CHANGELOG.md) for detailed fix history（第一至十四批修复记录）. Deployment notes: `DEPLOYMENT.md`（暂未提供）.

## Test Coverage（回归测试）

`tests/test_batch_regression.py` — 50 个测试，覆盖第一至第十八批所有已修复问题。
**每次修改代码后必须运行此文件**，任何已修复问题回退都会在此处失败。

`tests/test_format_checker.py` — 33 个单元测试，覆盖第十四批 Phase 1 Core + 第二十批行距检查（FormatRules + FormatChecker + QAEngine 集成）。

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
| `TestFormatCheckerLineSpacing` | 第二十批 | 行距精确/倍数匹配与误报；SINGLE/1.0 默认跳过；MAX_LINE_SPACING_ISSUES 上限；容差边界 |
