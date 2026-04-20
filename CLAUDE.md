# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
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

# Fix Windows terminal encoding before starting
chcp 65001
```

**Minimal install** (skip PyTorch/ChatGLM if only using cloud AI):
```bash
pip install python-docx pdfplumber openpyxl PyYAML pydantic openai flask flask-cors supabase
```

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
|------|------|
| `app.py` | All business logic; the `Api` class |
| `web/flask_app.py` | Flask routes — thin wrappers only |
| `web/index.html` | Entire frontend SPA |
| `core/document_model.py` | Central data model — read this first |
| `parsers/dispatcher.py` | Parser entry point; `.doc` three-level conversion fallback |
| `parsers/docx_parser.py` | Most complex parser; extracts styles, images, sections |
| `core/qa_engine.py` | QA orchestration: typo → consistency → logic |
| `core/exporter.py` | Converts `DocumentModel` → `.docx` (Python-side, used by `saveTemplateSettings`) |

## Configuration

`config.yaml` configures LLM provider/key/model, QA checker toggles, and Chinese font size mappings. The app runs without it (uses defaults/mocks). Supabase credentials can also be set via env vars `SUPABASE_URL` and `SUPABASE_KEY`.

## Known constraints

- Only Web version is maintained — `pywebview` desktop mode is abandoned
- `.doc` conversion requires LibreOffice **or** Microsoft Word (see three-level fallback above)
- Supabase free tier pauses after 7 days of inactivity
- `web/index.html` uses inline `<style>` and `<script>` — there is no bundler or CSS preprocessor
- Hardcoded Supabase anon key and Doubao API key exist in source — do not rotate without updating both `app.py` and `web/index.html`

## Recent fixes (2026-04-20)

| Issue | Fix location | Detail |
|-------|-------------|--------|
| 导出文件乱码 | `web/index.html:exportDoc` | 补读 h2/h3/wFont；所有 TextRun 加 `font.name` + `font.eastAsia` |
| 模板上传栈溢出 | `web/index.html:handleTemplateUpload` | btoa 改为 8192 字节分块编码 |
| AI 解析排版规则为桩函数 | `web/index.html:runAIParse/applyAIRules` | 实现 AI 文本→JSON 规则解析及一键填入面板 |
| .doc 文件不显示 | `parsers/dispatcher.py` | 三级回退；前端 `_loadDocFile` 同步改为分块编码 |
| LibreOffice 失败不继续 | `parsers/dispatcher.py` | 失败后 warning + fall through，不再 raise |
| 仪表板数据不持久 | `web/index.html` | `tabQAState`/`tabXrefState` 跨 tab 切换保存/恢复 |
| 首页导航 / 在线状态 | `web/index.html` | 工具栏"首页"按钮；状态栏 30s 轮询在线点 |
| 图片对齐 | `parsers/docx_parser.py` + `web/index.html` | 扫描 `<w:drawing>` 提取图片+对齐；前端加对齐 CSS 和浮动工具栏 |
