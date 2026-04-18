# WordCraft Pro

**智能 Word 排版桌面应用** —— 一键解析文档、自动排版、质量检查、交叉引用校验、AI 辅助，全流程桌面工具。

---

## ✨ 核心功能

| 模块 | 功能 |
|------|------|
| **多格式解析** | 支持 `.docx` `.pdf` `.xlsx` `.txt` `.md` `.doc`（需 LibreOffice 转换），统一输出为内部文档模型 |
| **智能排版** | 基于模板规则自动排版：字体、字号、页边距、行距、缩进、页眉页脚、多节配置，一键应用 |
| **自然语言排版** | 用中文描述排版需求（如"一级标题黑体三号居中"），LLM 自动解析为结构化规则 |
| **质量检查（QA）** | 错别字检测（常见错别字词典 + 的地得用法）、数据一致性检查、逻辑合理性检查 |
| **交叉引用校验** | 自动扫描图/表/公式/章节编号，检测悬空引用、未引用目标、重复编号 |
| **AI 辅助** | 内置豆包大模型集成，支持排版规则生成、QA 分析、自然语言交互 |
| **Word 导出** | 排版后导出 `.docx`，保留完整格式（字体、缩进、页眉页脚、页码等） |
| **模板系统** | 内置政府公文、高校论文等排版模板，支持 YAML 自定义模板 |

---

## 📸 界面预览

应用提供两种桌面界面模式：

- **pywebview 模式**（默认）：轻量 WebView，使用系统 Edge/WebView2 渲染
- **PyQt6 模式**：完整 Qt 原生体验，QWebEngineView + QWebChannel 双向桥接

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows / macOS / Linux

### 安装依赖

```bash
pip install -r requirements.txt
```

> **注意**：完整依赖包含 PyTorch（本地模型推理），如果只使用云端 API，可按需安装核心子集：
> ```bash
> pip install python-docx pdfplumber openpyxl pywebview PyYAML pydantic openai
> ```

### 启动应用

```bash
# 默认启动 pywebview 图形界面
python main.py

# PyQt6 模式
python main.py --gui

# 运行功能演示
python main.py --demo

# 运行单元测试
python main.py --test
```

---

## 📁 项目结构

```
wordcraft-pro/
├── main.py                  # 应用入口（CLI 分发）
├── app.py                   # pywebview 桌面应用
├── webview_app.py           # PyQt6 WebView 桌面应用
├── config.yaml              # 全局配置（LLM / 解析 / QA / 交叉引用）
├── requirements.txt         # 依赖清单
├── build.py                 # 跨平台打包脚本（PyInstaller）
├── build_offline.py         # 离线包构建
├── build.bat / build.sh     # 一键打包入口
│
├── core/                    # 核心引擎
│   ├── document_model.py    # 统一文档模型（所有模块的数据核心）
│   ├── formatting_rules.py  # 排版规则定义
│   ├── formatter.py         # 排版引擎：规则 → 文档模型
│   ├── exporter.py          # 导出引擎：文档模型 → .docx
│   ├── template_manager.py  # 模板管理器
│   ├── qa_engine.py         # 质量检查引擎（统一调度）
│   ├── qa_models.py         # QA 数据模型
│   ├── typo_checker.py      # 错别字检查器
│   ├── consistency_checker.py # 数据一致性检查器
│   ├── logic_checker.py     # 逻辑合理性检查器
│   ├── crossref_engine.py   # 交叉引用引擎
│   ├── crossref_executor.py # 交叉引用修复执行器
│   ├── crossref_models.py   # 交叉引用数据模型
│   └── template_parser/     # 模板解析器（docx 样式 / 文本规则）
│
├── llm/                     # LLM 集成
│   ├── client.py            # LLM 客户端抽象层（豆包/OpenAI/ChatGLM）
│   ├── nl_rule_parser.py    # 自然语言 → 排版规则解析
│   └── qa_analyzer.py       # AI 质量分析
│
├── parsers/                 # 文件解析器
│   ├── base.py              # 解析器基类
│   ├── dispatcher.py        # 解析器调度器（自动选择 + .doc 转换）
│   ├── docx_parser.py       # Word 文档解析
│   ├── pdf_parser.py        # PDF 解析
│   ├── xlsx_parser.py       # Excel 解析
│   ├── md_parser.py         # Markdown 解析
│   └── txt_parser.py        # 纯文本解析
│
├── templates/               # 排版模板（YAML）
│   ├── gov_jiancaoping.yaml # 政府公文模板（太原市尖草坪区绩效评价报告）
│   └── thesis_haida.yaml    # 高校论文模板（广东海洋大学本科毕业论文）
│
├── ui/                      # PyQt6 图形界面
│   ├── main_window.py       # 主窗口
│   ├── workflow_engine.py   # 工作流引擎（解析→排版→QA→交叉引用→导出）
│   ├── file_panel.py        # 文件面板
│   ├── format_panel.py      # 排版参数面板
│   ├── preview_panel.py     # 文档预览面板
│   ├── qa_panel.py          # QA 检查结果面板
│   ├── crossref_panel.py    # 交叉引用面板
│   ├── llm_chat_panel.py    # AI 对话面板
│   └── styles.py            # 样式定义
│
├── web/                     # 网页版 UI
│   ├── index.html           # 单页应用
│   └── test_template.docx   # 测试模板文件
│
└── tests/                   # 单元测试
    ├── test_phase1.py ~ test_phase7.py  # 各阶段功能测试
    ├── test_core_functions.py           # 核心功能测试
    └── test_webapp.py                  # Web 应用测试
```

---

## 🔧 配置说明

编辑 `config.yaml` 进行全局配置：

### LLM 配置

```yaml
llm:
  mode: "api"
  api:
    provider: "doubao"          # 豆包 / openai / chatglm
    api_key: "your-api-key"
    base_url: "https://ark.cn-beijing.volces.com/api/v3"
    model: "Doubao-Seed-1.6"
    temperature: 0.3
```

> 未配置 API Key 时，应用使用 `MockLLMClient`（模拟回复），不影响排版和 QA 规则检查功能。

### QA 配置

```yaml
qa:
  typo_check:
    enabled: true
    use_llm: true               # 是否使用 LLM 辅助检测
  consistency_check:
    enabled: true
    check_numbers: true         # 数字格式一致性
    check_dates: true           # 日期格式一致性
    check_names: true           # 专有名词一致性
  logic_check:
    enabled: true
    check_causality: true       # 因果关系检查
    check_conclusion: true      # 结论支撑检查
    check_timeline: true        # 时间线矛盾检查
```

### 中文字号映射

内置中国标准字号与磅值对照表（初号 42pt → 八号 5pt），在 `config.yaml` 的 `formatter.cn_size_map` 中定义，LLM 解析自然语言排版需求时自动引用。

---

## 📐 工作流程

```
  文件输入 ──→ 解析器调度 ──→ 统一文档模型
                                  │
                     ┌────────────┼────────────┐
                     ▼            ▼            ▼
                 排版引擎     QA 引擎     交叉引用引擎
                     │            │            │
                     └────────────┼────────────┘
                                  ▼
                            导出 Word (.docx)
```

1. **解析**：根据文件扩展名自动选择解析器，`.doc` 通过 LibreOffice 转换后解析
2. **排版**：加载模板规则或自然语言解析结果，应用到文档模型
3. **QA**：错别字 → 一致性 → 逻辑，三阶段检查生成报告
4. **交叉引用**：扫描目标 → 扫描引用点 → 匹配校验，检测悬空/未引用/重复
5. **导出**：将排版后的文档模型写入 `.docx`，保留完整格式

---

## 🎯 排版模板

模板以 YAML 格式定义，包含页面设置、各级标题样式、正文样式、页眉页脚、编号规则等。

### 自定义模板

在 `templates/` 目录下创建 YAML 文件：

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

### 自然语言排版

无需手动编写 YAML，直接用中文描述需求：

> "论文用 A4 纸，上下边距 2.5cm，左右边距 3cm 和 2.5cm。一级标题黑体三号居中，正文宋体小四首行缩进2字符，1.5倍行距。"

LLM 自动解析为结构化排版规则并应用。

---

## 🧪 测试

```bash
# 运行全部测试
python main.py --test

# 或直接使用 pytest
python -m pytest tests/ -v
```

---

## 📦 打包分发

```bash
# 使用 PyInstaller 打包为可执行文件
python build.py

# Windows 产出: dist/WordCraft-Pro.exe
# macOS 产出:   dist/WordCraft-Pro.app
```

打包脚本自动安装依赖、收集资源文件、处理平台差异。

---

## 🛠 技术栈

| 类别 | 技术 |
|------|------|
| 核心语言 | Python 3.10+ |
| 文档处理 | python-docx, pdfplumber, PyMuPDF, openpyxl |
| LLM 集成 | OpenAI SDK（兼容豆包 API）, Transformers（ChatGLM 本地） |
| 桌面界面 | pywebview / PyQt6 + QWebEngineView |
| 数据校验 | PyYAML, pydantic |
| 打包 | PyInstaller |
| 云端服务 | Supabase（Auth / PostgreSQL / Storage） |

---

## ⚠️ 注意事项

### 1. Windows 终端中文乱码

管理后台启动时终端可能显示中文乱码，这是因为 PowerShell 默认编码不是 UTF-8。

**解决方法**：在启动前运行：
```powershell
chcp 65001
```

### 2. 微信登录

当前仅支持邮箱/手机号登录，微信 OAuth 登录需要额外配置，功能开发中。

### 3. 管理后台日志

管理后台 `/logs` 页面显示"开发中..."，完整的操作日志功能尚未实现。

### 4. Supabase Free Plan 限制

- 数据库会在 7 天无活跃连接后自动暂停
- 免费计划不含自动备份，建议定期手动导出
- 数据库限制 500MB，文件存储限制 1GB

### 5. API 密钥安全

Supabase Anon Key 在前端可见是 Supabase 的设计模式，数据安全由行级安全策略（RLS）保障。

### 6. 本地数据目录

用户数据存储在 `%APPDATA%\WordCraft-Pro\` 目录下，包含：
- `user.json` - 用户信息
- `settings.json` - 用户设置
- `token_quota.json` - Token 配额
- `token_logs.json` - Token 使用记录
- `templates/` - 模板缓存
- `documents/` - 文档缓存

---

## 📄 许可证

本项目仅供学习和研究使用。
