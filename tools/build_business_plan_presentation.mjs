import fs from "node:fs/promises";
import path from "node:path";

const artifactToolPath =
  "file:///C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const {
  Presentation,
  PresentationFile,
  row,
  column,
  grid,
  text,
  rule,
  fill,
  hug,
  fixed,
  wrap,
  grow,
  fr,
  auto,
} = await import(artifactToolPath);

const OUT_DIR = "./artifacts/business-plan-deck-2026-04-29-v2";
await fs.mkdir(OUT_DIR, { recursive: true });

const deck = Presentation.create({
  slideSize: { width: 1920, height: 1080 },
});

const W = 1920;
const H = 1080;
const TOTAL = 9;

const C = {
  navy: "#102433",
  navy2: "#1C3A4C",
  blue: "#2A5B7A",
  sky: "#D9E9F2",
  paper: "#F6F1E8",
  paper2: "#EEE6DA",
  white: "#FFFFFF",
  text: "#173042",
  text2: "#466174",
  text3: "#6D8595",
  orange: "#E8742B",
  orangeSoft: "#F5B285",
  green: "#2A7A60",
  greenSoft: "#D9EEE5",
  line: "#D7C9B9",
  gold: "#EAB75B",
};

function footer(slideNum, dark = false) {
  return row(
    {
      width: fill,
      height: hug,
      gap: 24,
      valign: "middle",
    },
    [
      text("内部对齐版 | Source: BUSINESS.md | 2026-04-29", {
        width: grow(1),
        height: hug,
        style: {
          fontSize: 12,
          color: dark ? "#BCD0DB" : C.text3,
        },
      }),
      text(`${slideNum}/${TOTAL}`, {
        width: hug,
        height: hug,
        style: {
          fontSize: 13,
          bold: true,
          color: dark ? C.orangeSoft : C.orange,
        },
      }),
    ],
  );
}

function bullet(value, size = 24, color = C.text2, width = fill) {
  return text(`• ${value}`, {
    width,
    height: hug,
    style: {
      fontSize: size,
      color,
    },
  });
}

function miniTitle(value, color = C.text) {
  return text(value, {
    width: fill,
    height: hug,
    style: {
      fontSize: 30,
      bold: true,
      color,
    },
  });
}

function cardTitle(value, color = C.text) {
  return text(value, {
    width: fill,
    height: hug,
    style: {
      fontSize: 28,
      bold: true,
      color,
    },
  });
}

function cardText(value, color = C.text2, size = 20, width = fill) {
  return text(value, {
    width,
    height: hug,
    style: {
      fontSize: size,
      color,
    },
  });
}

function thinAccent(color = C.orange, width = 160) {
  return rule({
    width: fixed(width),
    stroke: color,
    weight: 5,
  });
}

function standardSlide({ slideNum, bg, dark = false, title, subtitle, body }) {
  const slide = deck.slides.add();
  slide.background.fill = { type: "solid", color: bg };
  slide.compose(
    grid(
      {
        width: fill,
        height: fill,
        padding: { x: 92, y: 74 },
        columns: [fr(1)],
        rows: [auto, fr(1), auto],
        rowGap: 26,
      },
      [
        column(
          {
            width: fill,
            height: hug,
            gap: 12,
          },
          [
            text(title, {
              width: wrap(1360),
              height: hug,
              style: {
                fontSize: dark ? 54 : 50,
                bold: true,
                color: dark ? C.white : C.navy,
              },
            }),
            thinAccent(dark ? C.gold : C.orange, 210),
            subtitle
              ? text(subtitle, {
                  width: wrap(1320),
                  height: hug,
                  style: {
                    fontSize: 23,
                    color: dark ? "#BED0DB" : C.text2,
                  },
                })
              : text("", {
                  width: fixed(1),
                  height: fixed(1),
                  style: { fontSize: 1, color: bg },
                }),
          ],
        ),
        body,
        footer(slideNum, dark),
      ],
    ),
    {
      frame: { left: 0, top: 0, width: W, height: H },
      baseUnit: 8,
    },
  );
  return slide;
}

function coverSlide() {
  const slide = deck.slides.add();
  slide.background.fill = { type: "solid", color: C.navy };
  slide.compose(
    grid(
      {
        width: fill,
        height: fill,
        padding: { x: 92, y: 78 },
        columns: [fr(1.15), fr(0.85)],
        rows: [auto, fr(1), auto],
        columnGap: 48,
        rowGap: 22,
      },
      [
        text("WORDCRAFT PRO", {
          width: hug,
          height: hug,
          style: {
            fontSize: 18,
            bold: true,
            color: C.orangeSoft,
          },
        }),
        text("商业计划宣讲版", {
          width: hug,
          height: hug,
          style: {
            fontSize: 18,
            color: "#BFD0D9",
          },
        }),
        column(
          {
            width: fill,
            height: fill,
            gap: 20,
          },
          [
            text("先把功能讲清楚\n再把收费讲明白", {
              width: wrap(900),
              height: hug,
              style: {
                fontSize: 74,
                bold: true,
                color: C.white,
              },
            }),
            text("我们不是另一个写作工具。我们要做的是中文文档在“提交前”这一刻最有价值的检查产品。", {
              width: wrap(760),
              height: hug,
              style: {
                fontSize: 28,
                color: "#D3E0E7",
              },
            }),
            row(
              {
                width: fill,
                height: hug,
                gap: 26,
              },
              [
                column({ width: grow(1), height: hug, gap: 8 }, [
                  text("对标产品", {
                    width: fill,
                    height: hug,
                    style: { fontSize: 18, color: C.orangeSoft },
                  }),
                  text("WPS 校对", {
                    width: fill,
                    height: hug,
                    style: { fontSize: 34, bold: true, color: C.white },
                  }),
                ]),
                column({ width: grow(1), height: hug, gap: 8 }, [
                  text("我们的差异", {
                    width: fill,
                    height: hug,
                    style: { fontSize: 18, color: C.orangeSoft },
                  }),
                  text("排版格式 + 交叉引用", {
                    width: fill,
                    height: hug,
                    style: { fontSize: 34, bold: true, color: C.white },
                  }),
                ]),
              ],
            ),
          ],
        ),
        column(
          {
            width: fill,
            height: fill,
            gap: 18,
          },
          [
            miniTitle("这套 PPT 要解决什么", C.white),
            bullet("给团队统一产品理解", 24, "#D3E0E7"),
            bullet("给销售统一讲法", 24, "#D3E0E7"),
            bullet("把创新点放到最前面", 24, "#D3E0E7"),
            rule({ width: fill, stroke: "#466174", weight: 2 }),
            miniTitle("一句话定位", C.orangeSoft),
            text("帮助学生、研究团队和机构在文档提交前，快速发现 WPS 校对发现不了的高成本问题。", {
              width: wrap(520),
              height: hug,
              style: {
                fontSize: 28,
                color: C.white,
              },
            }),
          ],
        ),
        footer(1, true),
      ],
    ),
    {
      frame: { left: 0, top: 0, width: W, height: H },
      baseUnit: 8,
    },
  );
}

coverSlide();

standardSlide({
  slideNum: 2,
  bg: C.paper,
  title: "产品先讲清楚",
  subtitle: "这不是泛 AI 工具，而是“提交前检查”产品。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1.05), fr(0.95)],
      columnGap: 44,
      rowGap: 18,
    },
    [
      column(
        {
          width: fill,
          height: fill,
          gap: 20,
        },
        [
          miniTitle("核心任务"),
          text("检查一份中文文档在正式提交前，是否还有“容易被退回、返工、扣分”的问题。", {
            width: wrap(760),
            height: hug,
            style: {
              fontSize: 32,
              bold: true,
              color: C.navy,
            },
          }),
          thinAccent(C.orange, 180),
          bullet("文档上传与预览：支持 docx / pdf / xlsx", 23),
          bullet("规则层检查：错别字、标点、一致性", 23),
          bullet("格式规范检查：字体、字号、层级、模板规则", 23),
          bullet("交叉引用检查：参考文献、图表、引用跳转", 23),
          bullet("AI 深度检查：逻辑、语义、表述质量", 23),
          bullet("结果导出与复用：模板、规则、文档闭环", 23),
        ],
      ),
      grid(
        {
          width: fill,
          height: fill,
          columns: [fr(1), fr(1)],
          rows: [auto, auto],
          columnGap: 24,
          rowGap: 24,
        },
        [
          column({ width: fill, height: hug, gap: 12 }, [
            cardTitle("不是只查文字"),
            cardText("它查的是“整份文档能不能交”。"),
          ]),
          column({ width: fill, height: hug, gap: 12 }, [
            cardTitle("不是只做 AI"),
            cardText("规则层负责确定性问题，AI 层负责理解性问题。"),
          ]),
          column({ width: fill, height: hug, gap: 12 }, [
            cardTitle("不是只给学生"),
            cardText("学生先起量，研究团队和机构是更高客单的延伸。"),
          ]),
          column({ width: fill, height: hug, gap: 12 }, [
            cardTitle("不是替代编辑器"),
            cardText("WPS / Word 用来写，我们用来提交前验收。"),
          ]),
        ],
      ),
    ],
  ),
});

standardSlide({
  slideNum: 3,
  bg: C.white,
  title: "功能结构要讲得很清楚",
  subtitle: "销售对外讲解时，可以直接按这张图往下走。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1), fr(1), fr(1)],
      rows: [auto, auto],
      columnGap: 30,
      rowGap: 28,
    },
    [
      column({ width: fill, height: hug, gap: 12 }, [
        text("01", {
          width: hug,
          height: hug,
          style: { fontSize: 18, bold: true, color: C.orange },
        }),
        cardTitle("上传与预览"),
        cardText("先把文档真正打开，看到内容，再开始检查。"),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        text("02", {
          width: hug,
          height: hug,
          style: { fontSize: 18, bold: true, color: C.orange },
        }),
        cardTitle("基础规则检查"),
        cardText("错别字、标点、空格、一致性，这些问题先自动扫掉。"),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        text("03", {
          width: hug,
          height: hug,
          style: { fontSize: 18, bold: true, color: C.orange },
        }),
        cardTitle("格式规范检查"),
        cardText("按学校、期刊、单位的模板要求检查格式。"),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        text("04", {
          width: hug,
          height: hug,
          style: { fontSize: 18, bold: true, color: C.orange },
        }),
        cardTitle("交叉引用检查"),
        cardText("查参考文献编号、图表引用、链接是否断裂或错位。"),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        text("05", {
          width: hug,
          height: hug,
          style: { fontSize: 18, bold: true, color: C.orange },
        }),
        cardTitle("AI 深度检查"),
        cardText("查逻辑问题、论证是否通顺、语句是否像人写的。"),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        text("06", {
          width: hug,
          height: hug,
          style: { fontSize: 18, bold: true, color: C.orange },
        }),
        cardTitle("导出与复用"),
        cardText("保存规则、反复复检、形成团队自己的检查流程。"),
      ]),
    ],
  ),
});

standardSlide({
  slideNum: 4,
  bg: C.paper2,
  title: "为什么对标 WPS",
  subtitle: "WPS 教育了用户，但还没有覆盖最痛的提交前问题。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(0.9), fr(1.05), fr(1.05)],
      rows: [auto, auto, auto, auto, auto],
      columnGap: 18,
      rowGap: 18,
    },
    [
      miniTitle("能力项"),
      miniTitle("WPS 校对", C.text2),
      miniTitle("WordCraft Pro", C.navy),
      cardText("错别字 / 标点 / 语病", C.text, 22),
      cardText("能做，但偏文字层", C.text2, 22),
      cardText("能做，而且能和整份文档检查串起来", C.navy, 22),
      cardText("排版格式检查", C.text, 22),
      cardText("基本没有形成模板化能力", C.text2, 22),
      cardText("我们的核心创新点之一", C.orange, 22),
      cardText("交叉引用检查", C.text, 22),
      cardText("基本不解决", C.text2, 22),
      cardText("我们的核心创新点之一", C.orange, 22),
      cardText("使用场景", C.text, 22),
      cardText("写作过程中的文字校对", C.text2, 22),
      cardText("正式提交前的文档验收", C.navy, 22),
    ],
  ),
});

standardSlide({
  slideNum: 5,
  bg: C.navy2,
  dark: true,
  title: "最该强调的 4 个创新点",
  subtitle: "不是“我们也有 AI”，而是“我们能查出别人查不出的提交前问题”。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1), fr(1)],
      rows: [fr(1), fr(1)],
      columnGap: 34,
      rowGap: 28,
    },
    [
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("1. 排版格式检查", C.white),
        cardText("学校、期刊、机构最在意的不是只会不会写，而是交上去是不是规范。", "#CFE0E8", 24),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("2. 交叉引用检查", C.white),
        cardText("参考文献号错、图表引用断、跳转错位，这些都是高返工成本问题。", "#CFE0E8", 24),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("3. 规则层 + AI 层组合", C.white),
        cardText("确定性问题交给规则，理解性问题交给 AI，结果更稳，也更容易收费。", "#CFE0E8", 24),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("4. 模板和规则可以沉淀", C.white),
        cardText("从个人复用，到团队共享，再到机构规则库，这是后续放大客单价的关键。", "#CFE0E8", 24),
      ]),
    ],
  ),
});

standardSlide({
  slideNum: 6,
  bg: C.white,
  title: "谁会最先买单",
  subtitle: "先从最刚需、最容易成交的人群切入，再往上走。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1), fr(1), fr(1)],
      columnGap: 28,
      rowGap: 18,
    },
    [
      column({ width: fill, height: fill, gap: 14 }, [
        cardTitle("学生 / 研究生"),
        cardText("痛点：快提交了，最怕格式不对、引用乱掉、被导师打回。"),
        cardText("触发：毕业季、答辩前、期刊投稿前。"),
        cardText("价值：省返工时间，提升一次过的概率。", C.orange),
      ]),
      column({ width: fill, height: fill, gap: 14 }, [
        cardTitle("研究团队 / 咨询团队"),
        cardText("痛点：多人协作后，文档风格不统一，交付前要人工总检查。"),
        cardText("触发：交项目报告、标书、研究材料前。"),
        cardText("价值：把团队验收流程标准化。", C.orange),
      ]),
      column({ width: fill, height: fill, gap: 14 }, [
        cardTitle("高校 / 机构"),
        cardText("痛点：审稿和格式把关成本高，人工检查不稳定。"),
        cardText("触发：机构要统一规范、统一模板。"),
        cardText("价值：规则库沉淀后，长期成本最低。", C.orange),
      ]),
    ],
  ),
});

standardSlide({
  slideNum: 7,
  bg: C.paper,
  title: "怎么收费，团队和销售要讲一致",
  subtitle: "先让客户用起来，再让客户为“深度”和“效率”付费。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1), fr(1), fr(1)],
      rows: [auto, auto],
      columnGap: 28,
      rowGap: 24,
    },
    [
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("Free"),
        cardText("先体验基础检查能力。"),
        bullet("规则层检查", 20),
        bullet("基础交叉引用", 20),
        bullet("少量 AI 次数", 20),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("Pro"),
        cardText("面向个人高频用户。"),
        bullet("AI 深度检查", 20),
        bullet("AI 规则解析", 20),
        bullet("更多额度与更顺畅体验", 20),
      ]),
      column({ width: fill, height: hug, gap: 12 }, [
        cardTitle("Team"),
        cardText("面向小团队协作。"),
        bullet("团队规则共享", 20),
        bullet("批量检查", 20),
        bullet("更高文件与用量上限", 20),
      ]),
      column({ width: fill, height: hug, gap: 14 }, [
        miniTitle("转化逻辑"),
        cardText("不是先卖会员，而是先让客户看到问题，再让客户为解决更难的问题付费。"),
      ]),
      column({ width: fill, height: hug, gap: 14 }, [
        miniTitle("销售不要怎么讲"),
        cardText("不要上来讲模型、讲技术栈、讲大而全。先讲“为什么它能少返工”。"),
      ]),
      column({ width: fill, height: hug, gap: 14 }, [
        miniTitle("销售应该怎么讲"),
        cardText("免费版先试。需要更深检查、更高效率、更稳定交付，再升级。"),
      ]),
    ],
  ),
});

standardSlide({
  slideNum: 8,
  bg: C.white,
  title: "销售话术可以很简单",
  subtitle: "讲价值，不讲堆料；讲结果，不讲参数。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1.15), fr(0.85)],
      columnGap: 42,
      rowGap: 18,
    },
    [
      column({ width: fill, height: fill, gap: 18 }, [
        miniTitle("三句话讲完"),
        text("第一句：WPS 校对能查文字问题，但查不了排版格式和交叉引用。", {
          width: wrap(860),
          height: hug,
          style: { fontSize: 26, bold: true, color: C.navy },
        }),
        text("第二句：WordCraft Pro 帮你在提交前，把最容易返工的问题提前找出来。", {
          width: wrap(860),
          height: hug,
          style: { fontSize: 26, bold: true, color: C.navy },
        }),
        text("第三句：先免费试，真觉得能省时间、少返工，再付费升级。", {
          width: wrap(860),
          height: hug,
          style: { fontSize: 26, bold: true, color: C.navy },
        }),
      ]),
      column({ width: fill, height: fill, gap: 18 }, [
        miniTitle("适合被反复强调的词"),
        bullet("提交前", 22),
        bullet("少返工", 22),
        bullet("更规范", 22),
        bullet("WPS 查不到", 22),
        bullet("先试再买", 22),
        rule({ width: fill, stroke: C.line, weight: 2 }),
        miniTitle("不要反复强调的词"),
        bullet("大模型多先进", 22, C.text3),
        bullet("技术实现多复杂", 22, C.text3),
        bullet("我们功能很多", 22, C.text3),
      ]),
    ],
  ),
});

standardSlide({
  slideNum: 9,
  bg: C.paper2,
  title: "团队本周先统一三件事",
  subtitle: "先把产品讲法、卖点优先级、执行顺序统一，后面动作才不会散。",
  body: grid(
    {
      width: fill,
      height: fill,
      columns: [fr(1), fr(1), fr(1)],
      columnGap: 28,
      rowGap: 18,
    },
    [
      column({ width: fill, height: fill, gap: 14 }, [
        cardTitle("1. 统一产品讲法"),
        cardText("默认先讲功能，再讲 WPS 对比，再讲收费。"),
        cardText("不再把技术方案放在开场。", C.orange),
      ]),
      column({ width: fill, height: fill, gap: 14 }, [
        cardTitle("2. 统一卖点优先级"),
        cardText("最前面永远讲：排版格式检查、交叉引用检查。"),
        cardText("AI 是增强项，不是第一卖点。", C.orange),
      ]),
      column({ width: fill, height: fill, gap: 14 }, [
        cardTitle("3. 统一执行动作"),
        cardText("销售拿这套话术试讲。"),
        cardText("产品按用户分层计划推进 Free / Pro / Team。", C.orange),
      ]),
    ],
  ),
});

const pptx = await PresentationFile.exportPptx(deck);
const deckPath = path.join(OUT_DIR, "wordcraft-business-plan-alignment-2026-04-29-v2.pptx");
await pptx.save(deckPath);

const previewPaths = [];
for (let i = 0; i < deck.slides.count; i += 1) {
  const slide = deck.slides.getItem(i);
  const png = await slide.export({ format: "png" });
  const pngPath = path.join(OUT_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`);
  await fs.writeFile(pngPath, new Uint8Array(await png.arrayBuffer()));
  previewPaths.push(pngPath);
}

await fs.writeFile(
  path.join(OUT_DIR, "manifest.json"),
  JSON.stringify(
    {
      generatedAt: new Date().toISOString(),
      deckPath,
      previews: previewPaths,
      slideCount: deck.slides.count,
    },
    null,
    2,
  ),
  "utf8",
);

console.log(JSON.stringify({ outDir: OUT_DIR, slides: deck.slides.count, deckPath }, null, 2));
