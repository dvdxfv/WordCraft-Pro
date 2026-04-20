# WordCraft Pro

**智能 Word 排版 Web 应用** —— 多格式文档解析、自动排版、AI 辅助、质量检查、交叉引用校验，一站式文档处理工具。

> 版本：0.7.0 | 架构：Flask API + 单页 Web 应用 | AI：豆包 doubao-seed-1-6-251015

---

## 核心功能

| 模块 | 功能描述 |
|------|---------|
| **多格式解析** | `.docx` `.doc` `.pdf` `.xlsx` `.xls` `.txt` `.md`，统一输出为内部文档模型 |
| **智能排版** | 基于 YAML 模板自动排版：字体、字号、页边距、行距、缩进、对齐，一键应用 |
| **AI 排版解析** | 上传参考模板或用中文描述需求，LLM 自动解析为结构化排版规则并填入设置面板 |
| **质量检查（QA）** | 错别字检测（常见错别字词典 + 的地得）、数据一致性检查、逻辑合理性检查 |
| **交叉引用校验** | 自动扫描图/表/公式/章节编号，检测悬空引用、未引用目标、重复编号 |
| **Word 导出** | 排版后导出 `.docx`，所有 TextRun 正确设置中文字体（`eastAsia`）和西文字体，避免乱码 |
| **模板系统** | 内置政府公文、高校论文 YAML 模板，支持自定义模板 |
| **用户系统** | Supabase Auth 邮箱登录，离线时自动回退到本地 Mock 模式 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux
- `.doc` 格式转换需要 LibreOffice 或 Microsoft Word（可选）

### 安装依赖

```bash
pip install python-docx pdfplumber openpyxl PyYAML pydantic openai flask flask-cors supabase
```

完整依赖（含开发工具）：

```bash
pip install -r requirements.txt
```

### Windows 终端中文乱码修复

启动前在终端运行：

```bash
chcp 65001
```

### 启动应用

**第一步：启动后端 Flask API 服务**

```bash
cd web
python flask_app.py
```

服务运行在 `http://localhost:5000`，提供所有业务 API。

**第二步：启动前端静态服务器**

```bash
cd web
python run_web.py
```

服务运行在 `http://localhost:8081`，自动打开浏览器访问应用。

两个进程需同时运行，前端通过代理将 `/api/*` 请求转发至后端。

---

## 项目结构

```
wordcraft-pro/
├── app.py                   # 核心业务逻辑（Api 类，所有方法的单一来源）
├── config.yaml              # 全局配置（LLM / QA / 格式 / 交叉引用）
├── requirements.txt         # 依赖清单
│
├── core/                    # 核心引擎
│   ├── document_model.py    # 统一文档模型（所有模块的数据核心）
│   ├── formatter.py         # 排版引擎：规则 → 文档模型
│   ├── exporter.py          # 导出引擎：文档模型 → .docx
│   ├── qa_engine.py         # QA 调度：错别字 → 一致性 → 逻辑
│   ├── typo_checker.py      # 错别字检查器（词典 + 的地得）
│   ├── consistency_checker.py # 数据一致性检查
│   ├── logic_checker.py     # 逻辑合理性检查
│   ├── crossref_engine.py   # 交叉引用扫描与校验
│   ├── template_manager.py  # YAML 模板加载与管理
│   └── supabase_client.py   # Supabase Auth / DB / Storage 封装
│
├── llm/                     # LLM 集成
│   ├── client.py            # LLM 客户端（豆包 / OpenAI 兼容 / MockClient）
│   ├── nl_rule_parser.py    # 自然语言 → 排版规则
│   └── qa_analyzer.py       # AI 辅助 QA 分析
│
├── parsers/                 # 文件解析器
│   ├── dispatcher.py        # 调度器：按扩展名选解析器，处理 .doc 转换
│   ├── docx_parser.py       # .docx 解析（含图片提取、对齐、样式）
│   ├── pdf_parser.py        # PDF 解析（pdfplumber）
│   ├── xlsx_parser.py       # Excel 解析（openpyxl）
│   ├── md_parser.py         # Markdown 解析
│   └── txt_parser.py        # 纯文本解析
│
├── templates/               # 排版模板（YAML）
│   ├── gov_jiancaoping.yaml # 太原市尖草坪区政府公文模板
│   ├── thesis_haida.yaml    # 广东海洋大学本科毕业论文模板
│   └── custom/              # 用户自定义模板目录
│
├── samples/                 # 测试样本文件
│   └── 益海嘉里项目综合效益评价（打印最终版）.doc
│
├── web/                     # Web 应用
│   ├── index.html           # 单页应用（~2500 行，无构建步骤）
│   ├── flask_app.py         # Flask 路由（薄包装层，仅转发到 app.py）
│   ├── run_web.py           # 静态服务器 + API 代理（端口 8081）
│   └── wordcraft_landing.html # 登录/欢迎页
│
├── docs/                    # 开发文档
│   └── 问题分析与优化计划.md  # Bug 记录与修复历史
│
└── tests/                   # 单元测试
    ├── test_phase1.py ~ test_phase7.py
    ├── test_core_functions.py
    └── test_webapp.py
```

---

## 架构说明

### 两层 API 设计

`app.py` 是**业务逻辑的唯一来源**，包含 `Api` 类及所有方法（`openFile`、`exportDocx`、`callAI`、`runQA` 等）。`web/flask_app.py` 是薄包装层，仅将 HTTP 请求路由到 `Api` 方法。

### 前端 SPA

`web/index.html` 是完整的单页应用，不需要 Node.js 或构建工具。从 CDN 加载以下库：
- `docx-preview 0.3.5` — .docx 在线预览
- `mammoth.js 1.6.0` — .doc 格式 HTML 提取
- `docx.js 8.5.0` — 客户端 .docx 生成导出
- `PDF.js 2.16` — PDF 渲染
- `SheetJS 0.18` — Excel 渲染
- `FileSaver.js` — 文件下载

前端所有 API 调用统一通过 `window.WC_API`（封装 `fetch('/api/...')`）发出。

### AI 集成

`app.py:callAI` 采用双通道回退：
1. Supabase Edge Function 代理（`/functions/v1/ai-proxy`，豆包 Seed 1.6）
2. 直连豆包 ARK API（`ark.cn-beijing.volces.com`，模型 `doubao-seed-1-6-251015`）

返回格式：`{"content": "...", "usage": {...}}` 成功 / `{"error": "..."}` 失败（无 `success` 字段）。

`config.yaml` 中的 `llm.api` 配置供 Python 端 `llm/client.py` 使用（QA 分析、自然语言规则解析），与前端直调分开管理。

### .doc 文件处理

`parsers/dispatcher.py` 对 `.doc` 文件执行三级转换回退：

| 优先级 | 方法 | 依赖 |
|--------|------|------|
| 1 | python-docx 直接打开（部分 .doc 实为 Open XML） | 仅 python-docx |
| 2 | LibreOffice headless 转换 | LibreOffice 已安装 |
| 3 | Windows PowerShell + Word COM | Microsoft Word 已安装 |

三级均失败时抛出清晰错误，注明安装建议。

### Supabase 集成

`core/supabase_client.py` 封装 Auth / PostgreSQL / Storage。`app.py` 中所有方法检查 `self._supabase`，为 `None` 时自动回退到本地 Mock 响应，应用可在无 Supabase 配置的情况下离线运行。

---

## 配置说明

编辑 `config.yaml`：

### LLM 配置

```yaml
llm:
  mode: "api"
  api:
    provider: "doubao"
    api_key: "your-api-key"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    model: "doubao-seed-1-6-251015"
    temperature: 0.3
    max_tokens: 4096
```

未配置 API Key 时使用 `MockLLMClient`，排版和规则检查功能不受影响。

### QA 配置

```yaml
qa:
  typo_check:
    enabled: true
    use_llm: true
  consistency_check:
    enabled: true
    check_numbers: true
    check_dates: true
    check_names: true
  logic_check:
    enabled: true
    check_causality: true
    check_conclusion: true
    check_timeline: true
```

### 中文字号映射

`config.yaml` 的 `formatter.cn_size_map` 定义初号（42pt）至八号（5pt）的完整对照表，LLM 解析自然语言排版需求时自动引用。

---

## 处理流程

```
文件输入
   │
   ▼
parsers/dispatcher.py
   ├─ .docx/.pdf/.xlsx/.txt/.md → 对应解析器
   └─ .doc → 三级转换 → DocxParser
   │
   ▼
DocumentModel（core/document_model.py）
   │
   ├──────────────────────────────────┐
   ▼                                  ▼
排版引擎（formatter.py）          QA 引擎（qa_engine.py）
   │                                  │
   ▼                                  ├─ 错别字检查
导出引擎（exporter.py）            ├─ 一致性检查
   │                                  └─ 逻辑检查
   ▼
.docx 文件输出                    交叉引用引擎（crossref_engine.py）
```

---

## 自定义排版模板

模板以 YAML 格式定义，放入 `templates/` 或 `templates/custom/` 目录：

```yaml
template_name: "我的论文模板"
template_type: "thesis"

page:
  paper_size: "A4"
  margin_top_cm: 2.5
  margin_bottom_cm: 2.5
  margin_left_cm: 3.0
  margin_right_cm: 2.5

heading1:
  font_name_cn: "黑体"
  font_size_pt: 16
  bold: true
  alignment: "center"

body:
  font_name_cn: "宋体"
  font_name_en: "Times New Roman"
  font_size_pt: 12
  first_indent_chars: 2
  line_spacing_value: 1.5
```

内置模板：
- `gov_jiancaoping.yaml` — 太原市尖草坪区绩效评价政府公文格式
- `thesis_haida.yaml` — 广东海洋大学本科毕业论文格式

---

## 运行测试

```bash
python -m pytest tests/ -v

# 运行单个文件
python -m pytest tests/test_core_functions.py -v

# 运行单个用例
python -m pytest tests/test_phase1.py::TestClassName::test_method_name -v
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| 后端 | Flask 2.x + Flask-CORS |
| 前端 | 原生 HTML5 / CSS / JS，无构建工具 |
| 文档处理 | python-docx, pdfplumber, openpyxl |
| LLM | 豆包 API（OpenAI 兼容），模型 doubao-seed-1-6-251015 |
| 云端 | Supabase（Auth + PostgreSQL + Storage），Free Plan |
| 前端库 | docx-preview 0.3.5, mammoth.js 1.6.0, docx.js 8.5.0, PDF.js 2.16, SheetJS 0.18, FileSaver.js |
| .doc 转换 | python-docx → LibreOffice → Word COM（三级回退） |

---

## 已知限制

| 项目 | 说明 |
|------|------|
| 桌面版 | pywebview 桌面模式已放弃，仅维护 Web 版 |
| `.doc` 转换 | 需要 LibreOffice 或 Microsoft Word；两者均未安装时解析失败 |
| 微信登录 | 微信 OAuth 功能开发中，当前仅支持邮箱密码登录 |
| AI 深度 QA | `runAIQA()` 按钮为桩函数（提示需配置 API Key） |
| PDF 导出 | 前端和后端均未实现 PDF 格式导出 |
| 管理后台日志 | `/logs` 端点返回"开发中..."，功能未实现 |
| Supabase 限制 | Free Plan 数据库在 7 天无连接后自动暂停；存储上限 1 GB |

---

## 许可证

本项目仅供学习和研究使用。
