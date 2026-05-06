# AI Parse Template Gap Analysis

Compares the two standard-answer files against the current AI Parse schema (the `sys` prompt fields in `runAIParse()`, `web/index.html` ~line 2972).

**Schema fields in scope** (from the `sys` prompt):
`titleFont`, `titleSize`, `titleAlign`,
`h1Font`, `h1Size`, `h1Bold`, `h1NumFormat`,
`h2Font`, `h2Size`, `h2Bold`, `h2NumFormat`,
`h3Font`, `h3Size`, `h3Bold`, `h3NumFormat`,
`h4Font`, `h4Size`, `h4Bold`, `h4NumFormat`,
`bodyFont`, `bodySize`, `westFont`, `westSize`,
`indent`, `lineSpacingMode`, `lineSpacingValue`, `align`,
`marginTop`, `marginBottom`, `marginLeft`, `marginRight`,
`headerFont`, `headerSize`, `headerAlign`,
`footerFont`, `footerSize`, `footerFormat`,
`tableNameFont`, `tableNameSize`, `tableNamePos`, `tableContentFont`, `tableContentSize`, `tableNumFormat`,
`figNameFont`, `figNameSize`, `figNamePos`, `figNumFormat`,
`notes`

---

## Template 1: 海大毕业论文模板

Source: `samples/海大毕业论文模板-格式要求-标准答案.md`

### Section 2 — 封面与前置部分

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 中文标题：方正姚体，小二号（18 pt） | `titleFont`, `titleSize` | ✅ **Parsed** | `titleFont` = 方正姚体，`titleSize` = 18 |
| 英文题目：Times New Roman，小三号（15 pt） | (none) | ❌ **Missing** | No field for a secondary/English title. `titleFont`/`titleSize` can only hold one title style. |
| 题名对齐方式 | `titleAlign` | ⚠️ **Partial** | Schema has `titleAlign` but standard answer does not specify alignment for this template; field is unused. |

### Section 3 — 摘要与关键词

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 中文摘要正文：宋体，五号（10.5 pt），固定值 20 磅 | `bodyFont`, `bodySize`, `lineSpacingMode`, `lineSpacingValue` | ⚠️ **Partial** | Body font/size fields exist and can carry these values, but the schema has a single global body style — there is no per-section (abstract vs. main body) distinction. Line spacing fields (`lineSpacingMode="exact"`, `lineSpacingValue=20`) can represent this correctly. |
| 中文关键词数量 3-5 个，分隔符中文分号 | (none) | ❌ **Missing** | No keyword count or separator field. |
| 英文摘要正文：Times New Roman，五号，固定值 20 磅 | `westFont`, `westSize` | ⚠️ **Partial** | `westFont`/`westSize` can capture Times New Roman + 10.5 pt, but these apply globally, not specifically to the English abstract section. |
| 英文关键词标签 `Keywords:` | (none) | ❌ **Missing** | No field for keyword section label format. |

### Section 4 — 正文标题体系

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 一级编号格式：`1` | `h1NumFormat` | ✅ **Parsed** | Field exists and can hold `"1"`. |
| 二级编号格式：`1.1` | `h2NumFormat` | ✅ **Parsed** | Field exists and can hold `"1.1"`. |
| 三级编号格式：`1.1.1` | `h3NumFormat` | ✅ **Parsed** | Field exists and can hold `"1.1.1"`. |
| 四级编号格式：`1.1.1.1` | `h4NumFormat` | ✅ **Parsed** | Field exists and can hold `"1.1.1.1"`. |
| H1 字体：黑体，12 pt，段前/后 0.5 行，固定值 20 磅 | `h1Font`, `h1Size` | ✅ **Parsed** | Font and size fields exist. |
| H1 段前/段后各 0.5 行 | (none) | ❌ **Missing** | No `h1SpaceBefore` / `h1SpaceAfter` fields. |
| H1 行距：固定值 20 磅 | `lineSpacingMode`, `lineSpacingValue` | ⚠️ **Partial** | Global `lineSpacingMode`/`lineSpacingValue` can represent this value, but the schema applies one line-spacing setting to all elements — there is no per-heading line-spacing field. H1–H4 all share the same 20 pt spec here, so the collision is benign for this template. |
| H2 西文字体：Arial | `h2Font` | ⚠️ **Partial** | `h2Font` is a single string; the schema cannot distinguish Chinese font from western font within the same heading level. The western font would have to be stored in `westFont` globally, losing the per-level distinction. |
| H4 字体：黑体，Arial，12 pt | `h4Font`, `h4Size` | ⚠️ **Partial** | Same single-font-per-level limitation as H2. |

### Section 5 — 正文

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 正文字体：宋体，五号（10.5 pt） | `bodyFont`, `bodySize` | ✅ **Parsed** | Direct field match. |
| 行距：固定值 20 磅 | `lineSpacingMode`, `lineSpacingValue` | ✅ **Parsed** | `lineSpacingMode="exact"`, `lineSpacingValue=20`. |
| 禁止彩色字体和符号 | `notes` | ⚠️ **Partial** | Can be stored in `notes` as free text, but not enforced by any structured field. |

### Section 6 — 题名与作者信息页

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 毕业设计题目：黑体，三号（16 pt），加粗，固定值 20 磅，段前/后各 1 行 | (none) | ❌ **Missing** | This is a specialized title-page section style; no field maps to it. It could overlap with `titleFont`/`titleSize`, but the standard answer already uses those for the cover Chinese title (方正姚体). |
| 专业/学号/姓名行：宋体，五号，居中 | (none) | ❌ **Missing** | No author-info section fields. |

### Section 8 — 参考文献

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 参考文献正文：宋体，小五（9 pt） | (none) | ❌ **Missing** | No `refFont` / `refSize` field. Would fall into `notes` at best. |
| 参考文献行距：固定值 16 磅 | (none) | ❌ **Missing** | No per-section line-spacing. The global `lineSpacingValue` conflicts (body uses 20 pt). |
| 编号格式：`[N]` | (none) | ❌ **Missing** | No reference numbering format field. |

### Section 9 — 附录

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 附录正文：宋体，五号，固定值 20 磅 | (none) | ❌ **Missing** | No `appendixFont` / `appendixSize` field; coincides with body style so could be inferred, but not expressible as a separate rule. |

### Section 10 — 页眉页脚与版面

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 上边距 2.5 cm，下 2.5 cm，左 2.5 cm，右 2.0 cm | `marginTop`, `marginBottom`, `marginLeft`, `marginRight` | ✅ **Parsed** | All four margin fields exist and accept cm values within the valid range. |
| 分节页眉（目录/摘要/正文/鸣谢各不同内容） | `headerFont`, `headerAlign` | ❌ **Missing** | `headerFont`/`headerSize`/`headerAlign` are single global fields. Per-section header content strings (e.g. "广东海洋大学xxxx届本科生毕业设计") have no field. |
| 前置部分使用罗马数字页码 | `footerFormat` | ⚠️ **Partial** | `footerFormat` is a single string (e.g. `"-1-"`). Dual-format pagination (Roman for front matter, numeric for body) cannot be expressed. |
| 正文页码样式：`－ 1 －` | `footerFormat` | ✅ **Parsed** | `footerFormat` can hold `"－1－"`. |

---

## Template 2: 附件7 — 太原市尖草坪区绩效评价报告

Source: `samples/附件7：太原市尖草坪区绩效评价报告基本排版要求-标准答案.md`

### Section 1 — 主标题

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 字体：方正小标宋简体，二号（22 pt），居中 | `titleFont`, `titleSize`, `titleAlign` | ✅ **Parsed** | All three fields exist and map directly. |

### Section 2 — 标题层级与编号

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 一级编号：`一` | `h1NumFormat` | ✅ **Parsed** | Field can hold `"一"`. |
| 二级编号：`（一）` | `h2NumFormat` | ✅ **Parsed** | Field can hold `"（一）"`. |
| 三级编号：`1.` | `h3NumFormat` | ✅ **Parsed** | Field can hold `"1."`. |
| 四级编号：`（1）` | `h4NumFormat` | ✅ **Parsed** | Field can hold `"（1）"`. |
| 一级标题字体：黑体 | `h1Font` | ✅ **Parsed** | Direct field match. |
| 二级标题字体：楷体 | `h2Font` | ✅ **Parsed** | Direct field match. |
| 三级标题字体：仿宋GB2312，加粗 | `h3Font`, `h3Bold` | ✅ **Parsed** | Both fields exist. |
| 四级标题字体：仿宋GB2312 | `h4Font` | ✅ **Parsed** | Field exists. |
| 各级标题字号（未明确指定） | `h1Size`–`h4Size` | ⚠️ **Partial** | Standard answer does not specify pt values for heading levels; fields exist but would be `null`. |
| 最多不超过四级标题 | `notes` | ⚠️ **Partial** | Can go into `notes` as free text; no structured `maxHeadingLevel` field. |
| 禁止使用 `①②` 等自定义格式 | `notes` | ⚠️ **Partial** | Free text in `notes` only; no structured prohibition list. |

### Section 3 — 正文

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 正文字体：仿宋GB2312 | `bodyFont` | ✅ **Parsed** | Direct field match. |
| 正文字号（未明确指定） | `bodySize` | ⚠️ **Partial** | Field exists but standard answer omits body size for this template; would be `null`. |

### Section 4 — 数字、英文与单位

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 数字/英文字体：Times New Roman，三号（16 pt） | `westFont`, `westSize` | ✅ **Parsed** | Both fields exist and map directly. |
| 数字须加千位分隔符 | `notes` | ⚠️ **Partial** | Free text in `notes`; no structured numeric format field. |
| 金额单位统一：万元，保留两位小数 | `notes` | ⚠️ **Partial** | Free text in `notes`; no `currencyUnit` or `decimalPlaces` field. |
| 面积单位全篇统一：m2 | `notes` | ⚠️ **Partial** | Free text in `notes`; no unit-consistency field. |

### Section 5 — 行距与标点

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 行距：1.5 倍 | `lineSpacingMode`, `lineSpacingValue` | ✅ **Parsed** | `lineSpacingMode="multiple"`, `lineSpacingValue=1.5`. |
| 标点符号必须使用中文标点 | `notes` | ⚠️ **Partial** | Free text in `notes`; the existing `PunctuationChecker` handles this at QA time but `runAIParse` has no dedicated field. |

### Section 6 — 文字一致性与表达要求

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 项目名称全篇一致，简称需首次注明 | `notes` | ⚠️ **Partial** | Free text in `notes`; no structured consistency rule field. |
| 表格内容与文字叙述顺序、内容一致 | `notes` | ⚠️ **Partial** | Free text in `notes` at best; this is a semantic QA concern outside the schema's scope. |

### Section 7 — 文件名格式

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 文件名格式：`《文件名》`，双层书名号用 `〈〉` | `notes` | ⚠️ **Partial** | Free text in `notes`; no `fileNameBracketStyle` field. |
| 中括号必须用 `〔〕`，禁用 `【】`/`［］` | `notes` | ⚠️ **Partial** | Free text in `notes`; no bracket-style field. |

### Section 8 — 页眉、页脚与页边距

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 页眉内容：项目名称，居中 | `headerAlign` | ⚠️ **Partial** | `headerAlign` can express "center"; the actual content string (项目名称) has no field. |
| 页眉字体：仿宋GB2312，小五（9 pt） | `headerFont`, `headerSize` | ✅ **Parsed** | Both fields exist and map directly. |
| 页脚位置：页面底端-外侧 | (none) | ❌ **Missing** | No `footerAlign` or `footerPosition` field. |
| 页码格式：`-1-`，仿宋GB2312，四号（14 pt） | `footerFormat`, `footerFont`, `footerSize` | ✅ **Parsed** | All three fields exist and map directly. |
| 上边距 3.7 cm，下 3.5 cm，左 2.7 cm，右 2.7 cm | `marginTop`, `marginBottom`, `marginLeft`, `marginRight` | ✅ **Parsed** | All four fields map directly. |

### Section 9 — 表格规范

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 表名：黑体，四号（14 pt），居中，表上方 | `tableNameFont`, `tableNameSize`, `tableNamePos` | ✅ **Parsed** | All three fields exist. Alignment ("居中") has no `tableNameAlign` field. |
| 表名与前文间距：空一行 | (none) | ❌ **Missing** | No `tableSpaceBefore` field. |
| 表内文字：宋体，10 号 | `tableContentFont`, `tableContentSize` | ✅ **Parsed** | Both fields exist. |
| 表编号格式：`表1-1`，`表2-1` | `tableNumFormat` | ✅ **Parsed** | `tableNumFormat` uses `"表X-X"` pattern; matches. |
| 编号后空一格再写表名 | (none) | ❌ **Missing** | No `tableNumSeparator` field. |
| 表格整体居中排版 | (none) | ❌ **Missing** | No `tableAlign` field. |
| 跨页须设置表头打印 | `notes` | ⚠️ **Partial** | Free text in `notes`; no `tableRepeatHeader` field. |

### Section 10 — 图片规范

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 图名：黑体，四号（14 pt），图下方 | `figNameFont`, `figNameSize`, `figNamePos` | ✅ **Parsed** | All three fields exist. `figNamePos="bottom"` is correct. |
| 图编号格式：`图1-1`，`图1-2` | `figNumFormat` | ✅ **Parsed** | `figNumFormat` uses `"图X-X"` pattern; matches. |
| 图与上方文字空一行；图名与下方文字空一行 | (none) | ❌ **Missing** | No `figSpaceBefore` / `figSpaceAfter` field. |
| 图名对齐方式（居中） | (none) | ❌ **Missing** | No `figNameAlign` field (unlike `tableNamePos`, there is no `figNameAlign`). |

### Section 11 — 附件规范

| Requirement | Field | Status | Notes |
|---|---|---|---|
| 附件标注格式，多附件用阿拉伯数字编号 | `notes` | ⚠️ **Partial** | Free text in `notes`; no structured attachment field. |
| "附件"二字及顺序号：3号黑体，顶格版心左上角 | (none) | ❌ **Missing** | No attachment heading style field. |

### Section 12 — Excel 附件规范

| Requirement | Field | Status | Notes |
|---|---|---|---|
| Excel 标题 18号，表头 11号，内容 10号，宋体 | (none) | ❌ **Missing** | No Excel-attachment style fields at all. |

---

## Cross-template Schema Gaps Summary

| Gap | Affects | Field needed |
|---|---|---|
| Per-section body styles (abstract, appendix, references have different fonts/sizes/line-spacing from main body) | Template 1 | `abstractFont/Size`, `refFont/Size/LineSpacing`, `appendixFont/Size` |
| Per-heading line-spacing and paragraph spacing (spaceBefore/After) | Template 1 | `h1SpaceBefore`, `h1SpaceAfter` (repeated for H2–H4) |
| Per-heading dual font (Chinese vs. western at same level) | Template 1 (H2, H4) | `h2CJKFont` + `h2LatinFont` (vs. current single `h2Font`) |
| Secondary/English title on cover page | Template 1 | `titleAltFont`, `titleAltSize` |
| Section-specific headers (different header content per chapter/section) | Template 1 | Not expressible as a single field; requires array structure |
| Dual page-number format (Roman front matter + Arabic body) | Template 1 | `footerFormatFrontMatter` or similar |
| Footer position / alignment | Template 2 | `footerAlign` or `footerPosition` |
| Table/figure alignment | Template 2 | `tableAlign`, `figNameAlign` |
| Table/figure spacing before/after | Template 2 | `tableSpaceBefore`, `figSpaceBefore`, `figSpaceAfter` |
| Numeric formatting rules (thousand separators, currency unit, decimal places) | Template 2 | `thousandSeparator`, `currencyUnit`, `decimalPlaces` |
| Punctuation / bracket style rules | Template 2 | Not expressible as structured field; currently absorbed by `notes` |
| Attachment heading style | Template 2 | `attachmentFont`, `attachmentSize` |
| Excel attachment styles | Template 2 | `excelTitleSize`, `excelHeaderSize`, `excelBodySize` |
| `notes` field overloaded | Both | Many distinct rule types land in the single 80-char `notes` field |

---

## Test Results

```
python -m pytest tests/test_format_checker.py tests/test_batch_regression.py -v
```

**72 passed, 0 failed** (1.25 s)

- `tests/test_format_checker.py`: 22 tests passed
- `tests/test_batch_regression.py`: 50 tests passed
