# Changelog — 修复历史

All major fixes organized by batch (第八批及以后). See [CLAUDE.md](CLAUDE.md) for current status and upcoming work.

**Note**: For complete fix history including batches 1-7 and detailed implementation notes, check the git log:
```bash
git log --all --oneline
git show <commit-hash>:CLAUDE.md  # 查看特定提交时的完整历史
```

## Recent fixes (2026-04-30) - 第十七批 17A：Free / Pro 分层闭环 + 激活码开通链路

> 依据 `PLANS/batch17_user_segmentation_engineering_plan.md` 对齐记录。本批先完成 17A，不进入 Team 完整协作闭环。

## Recent fixes (2026-05-06) - 第十七批 17B：团队邀请正式发送 + 任务历史面板

- 团队邀请不再只停留在 `mailto` / 文案复制：
  - 后端新增正式邮件发送接口 `sendTeamInviteEmail()`
  - 支持 webhook 邮件通道或 `Resend`（通过环境变量配置）
  - `重新发送` 现在走真实后端发送逻辑，并写入团队活动历史
- 团队工作区从“最小入口”提升为“可运营面板”：
  - 新增最近活动区
  - 新增批量任务历史区
  - 批量检查改为创建任务后轮询收口，而不是前端同步等待
- Supabase 数据层新增：
  - `supabase/migrations/20260506_batch17b_team_ops_history.sql`
  - `team_activity_logs`
  - `team_batch_jobs`
- 自动化验证补齐：
  - `tests/test_plan_gating.py`
  - `tests/test_team_workspace_contract.py`
  - `tests/test_supabase_plan_migration.py`
  - `tests/test_activation_entry_contract.py`
  - `tests/test_batch_regression.py`
  - `tests/test_format_checker.py`

### A. 统一 entitlement 层落地

**新增文件**: `core/entitlements.py`

- 定义统一套餐模型：`free / pro / team / enterprise`
- 统一输出契约：`tier / status / limits / features / usage`
- 提供门禁函数：
  - `check_feature_access()`
  - `check_quota_available()`
  - `check_file_size_allowed()`
- 明确免费版限制：
  - 文件大小 5MB
  - 规则检查 10 次/天
  - AI Parse 3 次/月
  - AI 深度检查 3 次/月

### B. Supabase 计划与用量数据层补齐

**迁移文件**: `supabase/migrations/20260429_batch17_user_plans.sql`

- 扩展 `profiles`：
  - `plan_tier`
  - `plan_status`
  - `plan_source`
  - `current_period_start`
  - `current_period_end`
  - `team_id`
  - `feature_flags`
- 新增表：
  - `usage_counters`
  - `activation_codes`
  - `subscriptions`
  - `teams`
  - `team_members`
- 增加 RLS 基础策略
- 新增 `public.redeem_activation_code(p_code text)` RPC，使用 `security definer`，避免让普通用户直接改写自己的 `profiles.plan_tier`

### C. 后端硬门禁接入

**改动文件**: `app.py`, `core/supabase_client.py`, `web/flask_app.py`

- `app.py` 新增：
  - `getCurrentPlan()`
  - `getUsageAndPlan()`
  - `redeemActivationCode()`
- `openFile()` 接入套餐文件大小限制
- `runQA()` 接入免费版规则检查日额度，并在成功后累计 `rule_check_used_today`
- `callAI()` 接入 `ai_parse` / `ai_qa` 月额度限制
- `callAI()` 新增 `charge_quota` 开关，修复长文 AI QA 分块被重复扣次的风险
- `saveFormatRequirements()` 接入个人规则库权限门禁
- `runXRef()` 保持原基础链路兼容，仅在 `deep=True` 时启用 Pro 门禁，避免破坏既有交叉引用回归
- `core/supabase_client.py` 新增：
  - `get_user_plan()`
  - `get_user_entitlements()`
  - `get_or_create_usage_counter()`
  - `increment_usage_counter()`
  - `redeem_activation_code()`

### D. 前端套餐展示与升级入口

**改动文件**: `web/index.html`

- 顶部状态区增加当前套餐与 AI 剩余额度展示
- 增加激活码输入入口，兑换成功后立即刷新权益状态
- AI Parse、AI 深度、深度 XRef、个人规则库保存都接入前端提示
- 上传前增加文件大小前置提示
- `runXRef()` 改为显式请求 deep 模式，和后端门禁语义对齐

### E. 手工开通工具链

**新增文件**: `tools/generate_activation_code.py`

- 生成可直接粘贴到 Supabase SQL Editor 的 `insert into public.activation_codes ...` 语句
- 支持：
  - 指定套餐
  - 指定有效天数
  - 指定兑换次数
  - 指定过期时间策略
  - 指定备注

### F. 测试与回归

**新增测试**:

- `tests/test_entitlements.py`
- `tests/test_plan_gating.py`
- `tests/test_activation_code_tool.py`
- `tests/test_supabase_plan_migration.py`

**已验证通过**:

- `tests/test_batch_regression.py`
- `tests/test_format_checker.py`
- 上述新增测试

**当前汇总结果**: **85 passed**

### G. 当前状态

- 第十七批 17A：**核心实现完成，自动化回归通过，待真实 Supabase 环境迁移与链路验收**
- 第十七批 17B：**最小闭环已落地，待 UI 收口与真实团队账号验收**（已完成团队工作区基础能力、共享规则与批量检查入口）

## Recent fixes (2026-05-01) - 第十九批：管理员仪表盘闭环验收完成

> 依据 `PLANS/batch19_admin_dashboard_enhancement.md` 对齐记录。本批已完成代码实施、真实 Supabase 迁移应用与管理员实登验收。

### A. 管理后台页面重写完成

**改动文件**: `web/dashboard.html`

- 旧版“后端监控页”已重写为 5 分区管理员后台
- 实现 admin 角色门控与非 admin 全屏占位页
- 增加中文 `LABELS` 映射层，避免套餐/用途/来源英文裸值直出
- 增加分区级 loading / empty / forbidden / error / data 状态
- 增加用户详情抽屉、团队成员抽屉、激活码生成弹窗
- 增加 Token 30 天趋势、日志筛选/分页/CSV 导出、30s polling、表头粘性与排序

### B. Supabase 管理员读策略与运营动作补齐

**新增文件**: `supabase/migrations/20260501_admin_role_read_plan_tables.sql`

- 补齐 admin 对以下对象的全局读取能力：
  - `profiles`
  - `usage_counters`
  - `activation_codes`
  - `subscriptions`
  - `teams`
  - `team_members`
- 额外补齐 `activation_codes` 的 admin `insert` 策略
- 支撑管理后台直接生成激活码，无需再走 SQL 控制台

### C. 自动化验证结果

- `tests/test_batch_regression.py`：46 passed
- `tests/test_format_checker.py`：23 passed
- `tests/test_document_structure.py`：26 passed
- `web/dashboard.html` inline script 语法校验：OK

### D. 真实环境验收结果

- `admin@wordcraft.com` 实登管理页：通过
- Supabase 已应用新增 RLS 迁移：通过
- “生成激活码 → 普通账号兑换 → redeemed_count +1”链路：通过

### E. 当前状态

- 第十九批：**已闭环完成**
- `docs/supabase-现状.md` 中“管理员 UI 还没做最终实登验收”已可标记为完成

## Recent fixes (2026-04-27) - 第十四批 Phase 3：格式规范 E2E 测试 + 后端持久化集成

> 完成 Batch 14 Phase 3 端到端测试与后端集成，确保格式规范可被持久化到 Supabase 并在页面重载后恢复。

### A. web/index.html：格式规范保存流程添加后端 API 调用

| 函数 | 改动 |
| ---- | ---- |
| `saveFormatRequirements()` | 添加异步 `fetch('/api/saveFormatRequirements', {method:'POST'})` 调用，在 localStorage 之外持久化到后端；若后端不可用则 gracefully fallback |
| `saveAIFormatRequirements()` | 添加同样的后端 API 调用逻辑 |

**效果**：规范现在既保存在 localStorage 作为会话缓存，又通过 Supabase 持久化到后端，支持跨设备和跨会话访问。

### B. web/index.html：页面初始化加载格式规范

| 函数 | 改动 |
| ---- | ---- |
| `loadFormatRequirementsFromBackend()` | 新增函数：app 初始化时调用，从后端加载用户已保存的规范；若后端失败则 fallback 到 localStorage |
| `init()` | 在初始化链末尾调用 `loadFormatRequirementsFromBackend()` |

**效果**：用户首次访问页面或重新打开时，已保存的格式规范会自动从后端加载并填充到 `_savedFormatRules`，无需用户手动重新输入。

### C. core/format_checker.py：优化 rate limiting 提示文案

| 文件 | 改动 |
| ---- | ---- |
| `format_checker.py` | 更新 summary issue 的 description，从"共检测到约 X 处"改为"显示 N 个格式错误（共检出 X 个同类问题），为避免过多提示仅显示最严重的 N 个，还有 Y 个类似问题已折叠"，明确说明为何只展示部分问题 |

**效果**：用户看到 rate limiting 提示时能明确理解为何只展示 2 个，以及可以在设置中调整显示数量。

### D. tests/e2e/test_format_qa_workflow.py：E2E 测试覆盖三大场景

| 测试 | 覆盖 |
| ---- | ---- |
| `test_format_qa_happy_path` | 用户设置规范 → 点保存 → 上传文档 → 运行 QA → 格式问题正确检出 |
| `test_format_qa_supabase_fallback` | Supabase 不可用时，app 从 localStorage fallback 恢复规范；页面重载后仍能使用缓存的规范 |
| `test_format_qa_partial_rules` | 上传的模板仅包含部分字段（如仅 h1 font/size），app 不崩溃且仅检查已定义的字段 |

**验证**：
- `tests/e2e/test_format_qa_workflow.py`：3/3 通过（happy path / fallback / partial rules）
- `tests/test_format_checker.py`：23/23 通过
- `tests/test_batch_regression.py`：27/27 通过
- 合计：**53 tests passed**

### E. 第十四批 Phase 3 状态同步

- `PLANS/batch14_format_qa.md` 已同步为 `Phase 3 Testing ✅ Complete (2026-04-27)`。
- 第十四批（Phase 1 + Phase 2 + Phase 3）已完整闭环，后续进入第十五批后的增量优化与稳定性收口。

### F. 交叉引用结果排序与点击定位映射修复（人工回归后续补丁，2026-04-27）

> 触发背景：人工测试 `samples/南海鸢乌贼捕捞量智能反演文献综述.docx` 时，发现“结果顺序”和“点击不同引用却高亮同段”的回归。

| 文件 | 改动 |
| ---- | ---- |
| `web/index.html` | `paraOcc` 计算从“基于 `element_index` 计数”改为“基于排序后 `matches` 序列位置计数”，使前端定位索引与结果列表顺序一致 |
| `web/index.html` | `jumpToXRefInText` 候选排序由“按 `innerText` 长度排序”改为“保持 DOM 原始顺序”，减少错位映射概率 |
| `tests/test_batch_regression.py` | 新增 `TestBatch16XRefLocationMapping`（2 个测试）：验证 `paraOcc` 序列语义与 matches 排序稳定性 |

**验证结果**：
- `tests/test_batch_regression.py`：32/32 通过（含新增 2 项）
- `tests/test_format_checker.py`：23/23 通过
- `tests/e2e/test_format_qa_workflow.py`：3/3 通过
- 合计：**58 tests passed**

**最终结论（✅ DONE，人工验收通过，2026-04-28）**：
- 本次补丁已通过人工确认：排序错乱与点击错位问题均已修复，满足验收标准。
- 后续如需进一步提升定位精度（如同段多引用场景），可在新批次中按需跟进：
  1. 后端返回段落内 offset / 文本片段哈希等强锚点；
  2. 前端点击定位由”候选序号匹配”升级为”锚点精确匹配”。

## Recent fixes (2026-04-26) — 第十五批：AI 智能排版解析改进 + 一键保存检查规范

> 依据 `PLANS/batch15_ai_format_parser_improvement.md` 对齐记录（本批聚焦 AI 解析路径与可用性闭环）。

### A. app.py：模板上传增加 docx 纯文本提取路径

| 文件 | 改动 |
| ---- | ---- |
| `app.py` | 新增 `_extract_docx_text()`；`uploadTemplate()` 在返回中增加 `doc_text` 字段（保留原有 `format_rules` 路径） |

**目的**：把「规范描述文档」交给 AI 理解文本语义，而不是只依赖 Word 样式静态读取，避免行距等字段异常值（如 `383540`）。

### B. web/index.html：模板上传改为“文本→AI 自动解析”

| 函数 | 改动 |
| ---- | ---- |
| `handleTemplateUpload()` | 上传后优先读取 `data.doc_text`，自动写入 `#aiInput`，并自动触发 `runAIParse()` |

**效果**：用户上传模板后无需手工复制内容或重复点击，直接进入 AI 解析。

### C. web/index.html：runAIParse() 提示词增强

- 增加中文字号别名到 pt 的映射约束（如初号/二号/小四等）
- 增加标题对齐字段（`h1Align/h2Align/h3Align`）
- 增加行距与边距值域限制（行距 `1.0-5.0`、边距 `0.5-10cm`）
- 强制“仅返回 JSON、未知字段用 null”

### D. web/index.html：AI tab 新增“保存为检查规范”并复用既有保存链路

| 函数/区域 | 改动 |
| --------- | ---- |
| `#fp-ai` | 增加 `btnSaveAIFormatRules` 和已保存提示 `aiFormatRulesSavedHint` |
| `runAIParse()` | 解析成功后显示“保存为检查规范”按钮 |
| `saveAIFormatRequirements()` | 新增函数：先 `applyAIRules()` 同步到表单，再复用 `saveFormatRequirements()` 保存 |

**设计取舍**：不新造保存协议，直接复用第十四批已完成的 FormatRules 存储与 QA 联动逻辑，降低维护成本。

### E. 第十五批验证状态

- 功能验证清单已在 `PLANS/batch15_ai_format_parser_improvement.md` 给出
- 当前 changelog 记录实现项；逐条勾选结果以该计划清单为准

---

## Recent fixes (2026-04-26) — 第十四批 Phase 1 Core：FormatChecker 后端 + Supabase 存储 + 结构化元素路径

### A. core/format_checker.py（新建）

**新增文件**：`core/format_checker.py`

| 类 | 说明 |
| -- | ---- |
| `FormatRules` | `@dataclass`，字段：`h1Font/Size`, `h2Font/Size`, `h3Font/Size`, `bFont/Size`, `lineSpacing`, `savedAt`；`from_dict()` 容忍 None/字符串数字；`is_empty()` 检测全零 |
| `FormatChecker` | `check(doc: DocumentModel) → QAReport`；`MAX_PER_TYPE=2`，超出时追加汇总 INFO issue；`SIZE_TOL=0.5pt` 容差；`rule_id` 格式 `format_font_h1` / `format_size_body` 等；`checker="FormatChecker"` |

**23 个单元测试** (`tests/test_format_checker.py`)：FormatRulesModel、NoIssues、FontMismatch、SizeMismatch、RateLimiting、QAEngineIntegration — 全部通过。

### B. core/qa_engine.py 集成

`QAEngine.check()` 新增 `format_rules: Optional[FormatRules] = None` 参数；在 `_check_sequential` 的 crossref 之后调用 `FormatChecker(format_rules).check()`，仅在 `"format" in categories and format_rules is not None` 时触发。

### C. Supabase user_format_rules 表

通过 Supabase Management API 创建：

| 列 | 类型 | 说明 |
| -- | ---- | ---- |
| `id` | uuid PK | `gen_random_uuid()` |
| `user_id` | uuid FK | → `auth.users(id)` |
| `rules_json` | jsonb | FormatRules 序列化 |
| `created_at` / `updated_at` | timestamptz | 自动维护 |

- Unique index on `user_id`（每用户一条）
- RLS enabled，策略 `users_own_format_rules`：`auth.uid() = user_id` ALL operations

### D. app.py 双存储策略

| 方法 | 逻辑 |
| ---- | ---- |
| `saveFormatRequirements(rules_json)` | Supabase upsert（有 `self._session["user_id"]`）→ 本地 `web/format_rules.json` fallback；两者均保存（Supabase 主，本地作离线缓存） |
| `loadFormatRequirements()` | Supabase 查询 → 写入本地同步 → 本地 JSON fallback |

### E. runQA 结构化元素路径

`runQA(content, categories_str, elements_json=None)` 新增 `elements_json` 参数：

- 前端传 `docContents[fn]`（含 `runs[]` 的结构化元素数组）
- 后端按字符数加权提取 dominant `font_eastAsia` 和 `font_size_pt`，填入 `DocElement.font_style`
- `FormatChecker` 因此能获取真实字体信息并触发检查（之前 HTML 路径丢失所有字体数据）

### F. @staticmethod 缺失 bug 修复

`app.py:_parse_docx` 补加 `@staticmethod` 装饰器——之前调用 `/api/openLocalFile` 时报 "takes 1 positional argument but 2 were given"。

### G. Supabase MCP 配置

`.claude/settings.local.json` 新增 `mcpServers.supabase`：`@supabase/mcp-server-supabase@latest` + personal access token，下次 Claude Code 重启后生效。

### H. 第十四批 Phase 2 前端联动完成（同日补齐）

`web/index.html` 已完成与后端 FormatRules 路径的前端闭环，对齐 `PLANS/batch14_format_qa.md` 的 Phase 2：

- 新增/启用「保存为检查规范」入口，保存后写入 `_savedFormatRules`（localStorage）
- `runQA()` 合并展示 format 类问题，并区分 `rule_source='format_rule'` 与标点/规范类问题来源
- 规则检查入口 `_checkFormatCompliance()` 与 `WC_API` 包装保持统一调用链，保存即生效

### I. 第十四批测试状态对齐

- 单元测试：`tests/test_format_checker.py` 23 项已通过（见上文 A 节）
- E2E：`tests/e2e/test_format_qa_workflow.py` 仍为待完成（pending）

---

## Recent fixes (2026-04-26) — 第十三批：交叉引用采纳式设计（已完成）

### A. 后端：`runXRef` 增强可采纳问题输出

- 返回新增 `xref_issues` 字段，供前端按“问题卡片”方式展示可采纳引用。
- 字段覆盖 `type/target_label/bookmark_name/element_index` 等关键定位信息。
- 有效文内引用映射为可采纳项（`type="unreferenced"`）；悬空引用为 `type="dangling"`。
- 结果按 `target_label` 去重，减少重复采纳项。

### B. 前端：交叉引用面板改为采纳式工作流

- 新增“可采纳引用”子视图（QA 风格卡片），支持定位、采纳、忽略、撤销。
- 新增状态 `tabXrefAcceptedEdits`，按 tab 维持采纳结果。
- 采纳后对预览区目标文本加 `hl-xref-accepted` 视觉标记，便于复核和撤销。

### C. 导出：采纳结果写回 Word REF 字段

- 导出阶段将采纳的 `target_label` 替换为 Word REF 字段 XML（含 `bookmark_name`）。
- 使“手写引用文本”在导出后可转为可更新的 Word 交叉引用字段。

### D. 第十三批回归与状态

- 回归测试覆盖：`TestBatch13XRefAdoption`（`tests/test_batch_regression.py`）覆盖 `xref_issues` 返回结构、`bookmark_name`、`target_label` 去重等核心行为。
- 第十三批已完成；后续相关修复（如定位精度/UI 清洁）在第十至第十一批条目中持续补齐。

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

**验证结果**：
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

**验证结果**：

| 指标 | 修复前 | 修复后 |
| ---- | ------ | ------ |
| 识别参考文献目标数 | 0 | ✅ 10（`[1]`–`[10]`） |
| 文内引用 VALID | 0 | ✅ 68 |
| 文内引用 DANGLING | 34+ | ✅ 0 |

回归测试：`tests/unit/test_qa_enhancement_regression.py` 9/9 通过。

---

See [CLAUDE.md](CLAUDE.md) for remaining batch history (batch 1-7) and current status.
## Recent fixes (2026-05-01) - 第十七批 17B：团队邀请接受 / 撤销链路补齐

> 同步 `PLANS/batch17_user_segmentation_engineering_plan.md` 当前状态。第十七批目前已完成最小团队工作区、邀请制加入、邀请撤销与前端分层收口；真实团队账号在线验收继续后置。

### A. 团队邀请制加入链路落地

**相关文件**:
- `supabase/migrations/20260502_batch17b_team_invites.sql`
- `app.py`
- `core/supabase_client.py`
- `web/flask_app.py`

- `add_team_member_by_email` 改为写入 `pending` 邀请
- 新增 `accept_team_invite` RPC 和本地 fallback
- 被邀请用户接受后再切换到 `team` 态，而不是被 owner 直接写成已生效成员

### B. owner 侧邀请撤销补齐

**相关文件**:
- `supabase/migrations/20260502_batch17b_cancel_team_invite.sql`
- `app.py`
- `core/supabase_client.py`
- `web/flask_app.py`

- 新增 `cancel_team_invite` RPC
- owner 可撤销 `pending` 邀请，释放误占用的团队名额

### C. 团队工作区前端收口

**相关文件**:
- `web/index.html`

- 团队工作区继续只对 `team / enterprise` 显示
- 被邀请但尚未接受的用户仍可看到待接受邀请入口
- pending 邀请现在提供 `复制文案`、`邮件草稿`、`重新发送`、`撤销邀请`

### D. 验证

- `python -m pytest tests/test_plan_gating.py tests/test_team_workspace_contract.py tests/test_supabase_plan_migration.py -q`
- `python -m pytest tests/test_batch_regression.py -q`
- `python -m pytest tests/test_format_checker.py -q`
