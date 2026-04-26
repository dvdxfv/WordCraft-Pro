# Changelog — 修复历史

All major fixes organized by batch (第八批及以后). See [CLAUDE.md](CLAUDE.md) for current status and upcoming work.

**Note**: For complete fix history including batches 1-7 and detailed implementation notes, check the git log:
```bash
git log --all --oneline
git show <commit-hash>:CLAUDE.md  # 查看特定提交时的完整历史
```

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
