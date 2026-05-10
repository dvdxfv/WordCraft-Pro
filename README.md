# WordCraft Pro

**Document QA & Formatting Workflow Demo**  
中文文档质量检查与格式自动化工作流 Demo

> 当前版本：`v1.0.0` · 架构：`Flask API + 单页 Web` · AI 模型：`DeepSeek-v4`（OpenAI 兼容接口）

---

## Problem · 问题背景

中文论文、报告、公文、评审材料在提交前，通常面临这些麻烦：

- **格式混乱**：正文/标题字体字号不统一，手动改一遍又一遍
- **编号错位**：图表、章节、参考文献编号在修改后失序
- **引用异常**：正文引用了不存在的图表，或某图表从未被引用
- **错别字和标点**：中英混用标点、重复标点、叠字、常见错字
- **人工通读成本高**：长文档每次修改都要全文重新检查一遍

这些问题本质上是**可以结构化检测的**，但目前缺少一个把"文档解析 + 格式规则 + QA 检查 + 导出"整合在一起的轻量 Web 工具。

---

## Users · 目标用户

- 正在撰写或修改毕业论文、学术报告的**学生和研究者**
- 需要处理规范化公文、评审材料的**机构工作人员**
- 处理长篇结构性文档、希望降低审阅成本的**撰稿人**
- 希望在个人项目中探索文档 AI 工作流的**开发者**

---

## Solution · 解决方案

WordCraft Pro 把以下步骤整合成一个 Web 工作流：

```
上传文档 → 统一解析 → 格式规则配置 → 一键排版 → QA 检查 → 导出 .docx
```

- 规则层（免费）：本地运行，覆盖 90% 可结构化检测的问题
- AI 层（可选）：调用 DeepSeek 做逻辑问题检查和语义增强
- 导出层：中西文字体分别设置，降低 Word 打开后乱码概率

---

## Product Highlights · 项目亮点

| 维度 | 描述 |
|------|------|
| 端到端 AI 工作流 | 从文件上传到结构化导出，完整闭环 |
| 两层 QA 架构 | 规则引擎（本地）+ AI 增强（可选）分工清晰 |
| 多格式文档解析 | 统一解析 `.docx/.doc/.pdf/.xlsx/.txt/.md` |
| 交叉引用引擎 | 检测悬空引用、未引用目标、编号重复 |
| 前后端产品化封装 | 后端 `Api` 类 + 薄路由层 + 无构建单页前端 |
| YAML 模板规则系统 | 配置驱动的格式规则，支持自定义扩展 |
| AI 规则自然语言解析 | 用中文描述格式要求，自动映射到结构化参数 |
| 可离线基础运行 | 未配置 AI Key 时自动降级，不影响规则层功能 |

---

## Demo · 界面演示

### Upload & Workspace · 上传与工作区

上传、排版、检查、导出都在同一条流程里，不需要在多个工具之间切换。

<p align="center">
  <img src="assets/screenshots/qa-workspace.png" alt="主工作区界面" width="900" />
</p>

---

### Formatting Workflow · 排版工作流

在排版面板统一设定字体、字号、行距、缩进、页边距，一次配置，整篇生效。

<p align="center">
  <img src="assets/screenshots/homepage.png" alt="排版配置面板" width="900" />
</p>

---

### QA Review · 质量检查

自动检测错别字、数据一致性、逻辑问题和标点规范，把"人工通读全文"变成"重点复核标记位置"。

<p align="center">
  <img src="assets/screenshots/xref-highlight.png" alt="QA 质量检查界面" width="900" />
</p>

---

### Cross-reference Highlighting · 交叉引用可视化

图表/章节引用异常在界面中直接高亮定位，避免到最终导出后才发现编号错位。

<p align="center">
  <img src="assets/screenshots/typesetting-workspace.png" alt="交叉引用高亮界面" width="900" />
</p>

---

### Export Result · 导出效果

从定位问题、查看修改结果，到导出后在 WPS / Word 中的实际显示效果，全过程可追溯。

<p align="center">
  <img src="assets/screenshots/typo-fix-2.png" alt="错别字定位" width="900" />
  <img src="assets/screenshots/typo-fix-1.png" alt="修复后预览" width="900" />
  <img src="assets/screenshots/typo-fix-3.png" alt="导出在 WPS 打开效果" width="900" />
</p>

---

## Case Study · 项目叙事

### Why I built this

接触到很多同学在提交论文或报告前，会花大量时间手动对照格式规范逐条修改，但这类工作高度重复、容易出错、又没有工具帮忙记录改了哪里。我想探索：**能否把这些可结构化描述的检查任务，用规则引擎 + 轻量 AI 做成一个真实可用的 Web 工作流？**

### What problem it explores

中文文档的格式问题大部分是可以自动检测的（字体、字号、编号、引用、标点），但逻辑问题（论证是否自洽、结论是否有支撑）需要语义理解。这个项目探索的是**两层分工**：规则层做确定性检测，AI 层做语义增强——各司其职，不混用。

### What product decisions I made

- **不做富文本编辑器**：用户在原有工具写文档，WordCraft Pro 只做检查和格式化，导出后回到原工具使用
- **规则层和 AI 层解耦**：没有 API Key 时规则层照常运行，降低使用门槛
- **YAML 模板驱动**：格式规则配置化，不写死在代码里，便于扩展和自定义
- **单 HTML 文件前端**：无构建步骤，降低环境依赖，方便快速部署和演示

### What I learned

- 中文文档处理的复杂性远超预期：`.doc` 格式兼容、中西文字体分离、交叉引用的各种异常形态，每一项都是独立的工程问题
- 规则引擎的维护成本不低：词库、标点规则、编号正则的边界情况很多，需要持续补充测试用例
- "可解释的检查结果"比"自动修复"更重要：用户需要知道为什么这里有问题，而不只是让 AI 悄悄改掉

### Next steps

见下方 Roadmap。

---

## Architecture · 架构速览

```
用户浏览器
    │
    ▼
web/index.html（单页前端，无构建）
    │  fetch('/api/...')
    ▼
web/flask_app.py（薄路由层，只做 HTTP → Api 转发）
    │
    ▼
app.py · Api 类（业务逻辑单一来源）
    ├── parsers/dispatcher.py → core/document_model.py（统一数据模型）
    ├── core/qa_engine.py（规则层 QA 编排）
    ├── core/crossref_engine.py（交叉引用扫描与匹配）
    └── llm/client.py（AI 层调用）
              │
              ├── Supabase Edge Function 代理（优先）
              └── DeepSeek / OpenAI 兼容接口（回退）
```

**AI 调用返回约定：**

- 成功：`{"content": "...", "usage": {...}}`
- 失败：`{"error": "..."}`（无 `success` 字段，检查 `data.error`）

---

## Capabilities · 能力表

| 能力 | 说明 |
|------|------|
| 多格式解析 | 统一读取 `.docx/.doc/.pdf/.xlsx/.xls/.txt/.md` |
| `.doc` 支持 | 上传后端自动转换（LibreOffice / Word COM / 直接解析，三级回退） |
| 智能排版 | YAML 模板驱动：字体、字号、间距、缩进、页边距批量设定 |
| AI 规则解析 | 自然语言描述格式要求，自动映射到结构化参数 |
| 错别字检测 | 内置词库 + `common_typos.tsv` + 用户自定义词库 + 可选 SIGHAN |
| 数据一致性检查 | 数值、日期、单位前后矛盾检测 |
| 标点规范检查 | 中英混用标点、重复标点、括号配对、叠字 |
| 交叉引用检查 | 悬空引用、未引用目标、重复编号可视化定位 |
| AI 深度 QA | 逻辑问题、论证流畅性、因果关系（需配置 API Key） |
| `.docx` 导出 | 中西文字体分别设置（`font.name` + `font.eastAsia`） |

---

## Quick Start · 快速上手

### 环境要求

- Python `3.10+`
- Windows / macOS / Linux

### 安装依赖

```bash
pip install -r requirements.txt
```

最小安装（跳过 PyTorch / ChatGLM）：

```bash
pip install python-docx pdfplumber openpyxl PyYAML pydantic openai flask flask-cors supabase
```

### 启动后端

```bash
cd web
python flask_app.py
# 后端：http://127.0.0.1:5000
```

### 启动前端

```bash
cd web
python run_web.py
# 前端：http://127.0.0.1:8081
```

> Windows 终端乱码时先执行：`chcp 65001`

一键启动脚本（Windows PowerShell）：

```bash
powershell -ExecutionPolicy Bypass -File .\scripts\dev-start.ps1
```

---

## Configuration · 配置示例

`config.yaml`（DeepSeek）：

```yaml
llm:
  mode: "api"
  api:
    provider: "deepseek"
    api_key: "your-api-key"
    base_url: "https://api.deepseek.com"
    model: "DeepSeek-v4"
    temperature: 0.3
    max_tokens: 4096
```

未配置 API Key 时自动进入 `MockLLMClient`，规则层功能正常运行，不影响基础文档处理流程。

YAML 格式模板示例：

```yaml
template_name: "论文模板示例"
template_type: "thesis"

body:
  font_name_cn: "宋体"
  font_name_en: "Times New Roman"
  font_size_pt: 12
  first_indent_chars: 2
  line_spacing_value: 1.5
```

内置模板位于 `templates/`，自定义模板建议放 `templates/custom/`。

---

## Tests · 测试命令

```bash
# 核心回归测试（每次改动后必跑）
python -m pytest tests/test_batch_regression.py -v
python -m pytest tests/test_format_checker.py -v

# E2E 测试
python -m pytest tests/e2e/test_batch7_e2e.py -m "e2e and no_login" -v
```

---

## Tech Stack · 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Flask + Flask-CORS |
| 前端 | 原生 HTML / CSS / JS（无构建步骤） |
| 文档处理 | python-docx / pdfplumber / openpyxl |
| AI | DeepSeek（OpenAI 兼容接口） |
| 云服务 | Supabase（Auth / DB / Storage） |
| 配置 | YAML 模板规则 |

---

## Project Structure · 项目结构

```text
wordcraft-pro/
├── app.py                  # 业务逻辑总入口（Api 类）
├── core/
│   ├── document_model.py   # 统一数据模型
│   ├── qa_engine.py        # QA 规则层编排
│   ├── crossref_engine.py  # 交叉引用扫描与匹配
│   ├── punctuation_checker.py
│   └── typo_lib.py
├── llm/
│   └── client.py           # AI 调用封装
├── parsers/
│   └── dispatcher.py       # 格式分发与 .doc 转换
├── templates/              # YAML 格式模板
├── web/
│   ├── flask_app.py        # Flask 薄路由层
│   └── index.html          # 单页前端
└── tests/
```

---

## Privacy & Safety Boundary · 隐私与安全边界

**请在使用前阅读本节。**

### 项目定位

本项目是**学习、研究和作品集 Demo**，旨在探索中文文档 QA 与格式自动化工作流的技术实现路径。它不是商业化 SaaS 产品，也不提供任何形式的数据安全承诺。

### 不适合的使用场景

以下场景**不建议**使用本工具处理文档：

- 涉及国家秘密、商业机密或个人敏感信息的文件
- 医疗、法律、金融等强监管领域的正式文档
- 对数据安全和隐私有合规要求的机构业务场景

### 使用建议

- 在上传前请先对文档做**脱敏处理**，移除姓名、身份证号、账户信息等个人数据
- 本工具目前**不提供**文件自动删除机制、加密存储、细粒度权限控制或日志审计
- 如需在生产环境使用，请自行补充上述安全机制

### 功能边界

本项目专注于：

- **格式检查**：字体、字号、间距、编号等结构性问题
- **质量检查**：错别字、标点、引用、数据一致性等可结构化描述的问题
- **工作流自动化**：解析 → 检查 → 导出的流程整合

本项目**不提供**：

- 论文代写、改写或润色服务
- 伪造数据、生成虚假内容
- 规避查重、反检测或学术不端辅助
- 替代专业审稿人或编辑的判断

AI 层的检查结果（逻辑问题、论证质量）仅供参考，不构成专业意见，最终判断责任由用户自行承担。

### 如果未来产品化

需要补充的安全机制包括但不限于：

- 上传文件的定时自动删除
- 传输和存储加密（TLS + 静态加密）
- 用户级权限隔离
- 操作日志审计
- 正式隐私协议和用户授权流程

---

## Roadmap · 后续计划

以下是计划中的改进方向，当前版本尚未实现：

- [ ] **隐私与安全机制**：文件定时删除、存储加密、权限控制
- [ ] **本地化处理模式**：支持完全离线运行，不依赖云服务
- [ ] **用户自定义模板**：可视化模板编辑器，免手写 YAML
- [ ] **更完整的模板规则系统**：覆盖更多国标/校标格式场景
- [ ] **文档对比**：修改前后版本差异可视化
- [ ] **批量处理**：多文档同时检查和导出
- [ ] **更细的 QA 检查项**：段落结构、引用格式、图表标题规范
- [ ] **导出稳定性提升**：复杂样式、嵌套结构的兼容性改善
- [ ] **微信登录**：当前主路径为邮箱登录，微信登录尚在开发中
- [ ] **PDF 导出**：当前重点是 `.docx` 导出，PDF 导出路径待实现

---

## Known Limitations · 已知边界

- 当前仅维护 **Web 版**（pywebview 桌面版已停止维护）
- `.doc` 转换依赖 LibreOffice **或** Microsoft Word，未安装时无法处理 `.doc` 文件
- Supabase 免费套餐 7 天无活跃后会自动暂停
- `web/index.html` 是单文件 SPA，无打包/构建流程，样式和脚本均为内联
- `SUPABASE_ANON_KEY` 明文写在前端（设计上公开，安全依赖 RLS）；Doubao API Key 作为回退写在 `app.py`，生产环境请通过环境变量 `DOUBAO_API_KEY` 覆盖
- QA 检查结果和 AI 建议仅供参考，存在漏检和误报，不构成最终审阅结论

---

## License · 许可证

本项目仅供学习与研究使用，不提供任何明示或暗示的商业保证。  
如需在其他场景使用，请先阅读 [Privacy & Safety Boundary](#privacy--safety-boundary--隐私与安全边界) 一节。
