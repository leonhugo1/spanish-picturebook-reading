# spanish-picturebook-reading

[English](README.md) · **简体中文**

[![CI](https://github.com/leonhugo1/spanish-picturebook-reading/actions/workflows/ci.yml/badge.svg)](https://github.com/leonhugo1/spanish-picturebook-reading/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

把一本**西班牙语绘本**（页面照片、扫描件或 PDF）变成**单文件交互式 HTML 课件**，外加一份**带家长答案页的可打印练习册**。

为**中文母语、正在开始学西语**的孩子做的：界面说中文，绘本保持西语，每一句都配翻译、语法讲解和母语级配音。

```
扫描页  →  逐页插图 + 西语原文 + 中文对照 + 配音
          + 逐句语法讲解
          + 可点击发声单词卡
          + 带家长答案页的练习册
```

---

## 产出物

| 文件 | 说明 |
|---|---|
| `<stem>_Lectura_Lesson.html` | 课件。单文件，离线可用，不需要服务器。 |
| `<stem>_Cuaderno_Worksheet.html` | 练习册。底部带一个折叠的家长答案页。 |
| `<课程库>/index.html` | 课程库导航页：每课一张卡，一键进课件或练习册。 |
| `source/normalized_*.json` | 本次构建用的内容，便于重建或二次编辑。 |

两份成品右上角都有一个 **`🏠 课程库` 返回键**，孩子不用在文件夹里翻找就能换课 ——
见下面的[课程库](#课程库)一节。

### 课件

- **逐页插图**配上旁边的西语原文 —— 绘本的重点是图，所以图保持大。
- **中西双行字幕**：西语大字，中文小字。两边都能单独关掉：隐藏西语练听力，隐藏中文练独立阅读。
- **点任意一句只读那一句**；「整页连读」从头念到尾。
- **逐句语法讲解** —— 阴阳性、动词变位、`ser` 与 `estar`、缩合形式。这是绘本本身教不了的部分。
- **可点击发声单词卡**，名词一律连着冠词写（`el gato`，不是 `gato`），性别跟着词一起记。点卡片读单词，点卡片下方的例句读整句 —— 听这个词在句子里怎么用。
- **精读讲义**自动把每一页的每一句汇总到一起，另附重点词深挖与文化背景。
- **配音是预录的神经语音**，以 base64 内嵌。**绝不使用浏览器自带语音** —— 那种声音机械，而且不同设备差异极大。缺一段就闪红 🔇，不会退回机器人声。

### 练习册

- 词汇配对、选词填空、句子仿写、段落仿写、摘要完形。
- **客观题答案提交后才显示**，孩子偷看不到。
- **家长答案页**折叠在底部。展开后打印 → 答案页**单独另起一页**；不展开打印 → 得到一份干净的纯题目版。

---

## 快速开始

需要 **Node.js 18+**。配音另外需要 **Python 3 + edge-tts**（可选，用 `--no-audio` 可以不配音）。

```bash
git clone https://github.com/leonhugo1/spanish-picturebook-reading
cd spanish-picturebook-reading

# 可选但推荐，用于生成配音
pip install edge-tts

# 先跑内置示例（3 页 A1 绘本，插图由脚本生成）
node scripts/build.js examples/gato-luna/content.json examples/gato-luna/worksheet.json out/

node scripts/validate.js out/
open out/gato-luna_Lectura_Lesson.html
```

整个循环就三步：**写 JSON → 构建 → 校验**。

---

## 从扫描版绘本到课件

市面上流通的分级读物大多是**没有文本层的整页扫描**，还常常盖着盗版商的水印。`scripts/prep_pages.py` 负责机械那一半。

```bash
# ① 先探测这本书的裁剪框
python3 scripts/prep_pages.py book.pdf build/pages --print-bounds

# ② 裁掉白边、抹掉水印，并把每页的正文行拼成一张图供转录
python3 scripts/prep_pages.py book.pdf build/pages \
    --erase-band 196,252 \
    --box 214,196,1466,978 \
    --page-box 1=248,248,1422,1016 \
    --captions
```

- `--print-bounds` 报出每一页的着墨边界 —— 把这些数字抄进 `--box`。
- `--erase-band TOP,BOT` **抹掉水印**：把紧邻下方的干净像素行整行覆盖上去。水印是浅灰、插画是实色，所以填上去看不出痕迹；比直接裁掉更好，因为不会切到画面。
- `--captions` 生成 `_captions.png`：每页的正文行叠成一张图，**一次看完十页**，不用逐页开图。
- 输出统一 1200px 宽 / JPEG q82，单页 30–150 KB。

然后转录西语原文（有了正文条带图这一步很快），再写中文译文、语法讲解和单词卡 —— 这一层是本工具新增的教学内容，要你来写。

> 转录要仔细：读图和 OCR 经常吞掉句首的 `¿` / `¡`，把 `ñ` 认成 `n`。前两个校验器会拦，最后一个只能靠人眼。

---

## 写内容

两份 JSON（或合并成一份 package）。详见：

- [`references/lesson-schema.md`](references/lesson-schema.md) —— `pictureBook` 块
- [`references/worksheet-schema.md`](references/worksheet-schema.md) —— 练习册各题与答案页

结构很小 —— 课件本质上就是一串页面：

```json
{
  "meta": {
    "titleEs": "El gato y la luna",
    "titleZh": "猫与月亮",
    "filenameStem": "gato-luna",
    "lessonType": "spanish_picturebook_reading"
  },
  "pictureBook": {
    "pages": [
      {
        "page": 1,
        "image": "data:image/jpeg;base64,…",
        "textEs": "Es de noche. El gato mira la luna.",
        "textZh": "天黑了。猫看着月亮。",
        "sentences": [
          { "es": "Es de noche.", "zh": "天黑了。",
            "grammar": ["ser 的第三人称单数 es + de noche，固定说法「是夜晚」"] }
        ],
        "note": "先看图再看字：问孩子 ¿Qué ves?"
      }
    ],
    "wordCards": [
      { "es": "el gato", "zh": "猫", "pos": "m.", "emoji": "🐱" }
    ]
  }
}
```

`image` **必须**是内嵌的 `data:image/…;base64,` —— 这是成品能作为单文件离线打开的前提。校验器会拒绝其它形式。

---

## 命令

```bash
# 两个产出一起出
node scripts/build.js content.json worksheet.json out/

# 只出其中一个
node scripts/build.js --lesson-only content.json out/
node scripts/build.js --worksheet-only worksheet.json out/

# 不配音（快，用来调版式）
node scripts/build.js --no-audio content.json worksheet.json out/

# 改完插图或译文后重建：没变的配音全部复用
node scripts/build.js --incremental-audio content.json worksheet.json out/

# 构建前先做内容自审 —— 它抓的是 validate.js 看不见的错：
# 答案不在自己的词库里、西里尔字母混进了拉丁字母里、某页的句子和整页文本不一致
python3 scripts/audit_content.py .

# 静态校验
node scripts/validate.js out/

# 真浏览器检查（可选，需要 puppeteer-core + 任意 Chrome）
npm install --no-save puppeteer-core
node scripts/smoke_lesson.js    out/*_Lectura_Lesson.html    /tmp/shot.png
node scripts/smoke_worksheet.js out/*_Cuaderno_Worksheet.html /tmp/ak

# 给课程库生成导航页：每课一张卡（加完新课后重跑一次即可）
python3 scripts/make_index.py <课程库根目录> --books-dir <原书 PDF 目录>
```

`--incremental-audio` 按每段文本的指纹比对，只重录改动过的句子。一本 10 页绘本大约 50 段配音：改插图、改中文译文**一段都不会重录**，重建从几分钟降到一秒以内。

**只有西语会进扬声器。** 中文是字幕，永远不配音。

---

## 课程库

课一多，孩子就需要一个统一的入口。

```bash
python3 scripts/make_index.py <课程库根目录> --books-dir <原书 PDF 目录>
```

它会扫描根目录下每个 `<编号-书名>/content.json`，生成 `<课程库根目录>/index.html`：
每课一张卡（西语书名、中文书名、页数、单词卡数、第一条教学目标），两个按钮分别进
课件和练习册；顶部是完成进度；底部可折叠列出还没做的书（来自 `--books-dir`）。
幂等 —— 每批做完重跑一次就行。

**返回键。** 当 JSON 里声明了课程库位置时，两份成品右上角都会出现 `🏠 课程库`：

```json
"meta": { "indexHref": "../../index.html" }
```

路径是**相对于成品 HTML 文件**的。按本项目的目录约定
（`<课程库>/<编号-书名>/out/`）一律填 `"../../index.html"`；不填就没有这个按钮。
两套冒烟测试都会断言：JSON 声明了它就一定渲染出来，且指向声明的地址。

因为是相对链接，**单独拷走某一个 HTML 会让返回键失效**（课件本身功能不受影响）。
要整批给孩子用，请把整个课程库目录一起拷。

---

## 配音音色

默认 `es-ES-ElviraNeural`，语速 `-12%` —— 比朗读文章更慢，因为孩子在跟读一句用外语写的、被高亮标出的句子。

| 音色 | 口音 |
|---|---|
| `es-ES-ElviraNeural` | 西班牙，女（默认） |
| `es-ES-AlvaroNeural` | 西班牙，男 |
| `es-MX-DaliaNeural` | 拉美，女 |
| `es-MX-JorgeNeural` | 拉美，男 |
| `es-AR-ElenaNeural` | 阿根廷，女 |
| `es-US-PalomaNeural` | 美国西语，女 |

```bash
EDGE_TTS_VOICE=es-MX-DaliaNeural node scripts/build.js content.json worksheet.json out/
```

---

## 目录结构

```
.
├── SKILL.md                      # 给 AI 编程助手看的执行指令
├── assets/
│   ├── lesson.html.template      # 课件外壳
│   └── worksheet.html.template   # 练习册外壳
├── references/
│   ├── lesson-schema.md
│   ├── worksheet-schema.md
│   └── release-gates.md          # 交付前的验收清单
├── scripts/
│   ├── prep_pages.py             # 扫描 PDF → 网页图片
│   ├── build.js                  # 一条命令两个产出
│   ├── gen_audio.py              # edge-tts 配音（含增量复用）
│   ├── validate.js               # 静态校验
│   ├── smoke_lesson.js           # 浏览器检查：课件
│   ├── smoke_worksheet.js        # 浏览器检查：练习册与答案页
│   └── _browser.js               # 跨平台 Chrome/Chromium 探测
└── examples/gato-luna/           # 生成的 3 页 A1 示例
```

---

## 配合 AI 助手使用

`SKILL.md` 就是为投喂给 agent 写的 —— 里面有完整流程、必须遵守的规则，以及一份「实际会犯的错误」清单。把 Claude Code / Cursor / Codex / WorkBuddy 指向它，然后把书交给它：

> 读 SKILL.md，把 `materials/el-gato.pdf` 这本扫描绘本处理成课件：准备页面、写 `content.json` 和 `worksheet.json`，然后跑 `scripts/build.js` 和 `scripts/validate.js` 输出到 `out/`。

---

## 版权

**本仓库不含任何绘本内容。** 内置示例是脚本生成的 SVG 插图和原创文本，工具本身也只处理**你自己提供**的文件。

你处理的那些书通常是有版权的。这类读物 PDF 大多是盗版商倒卖的，他们同样没有权利。请把成品留给自家使用：不要转发、不要把含扫描页的课件发到网上。`validate.js` 会拒绝包含本机绝对路径的构建产物，这能避免把你的机器信息带进分享文件，但它**挡不住版权问题**——这一块要靠你自己判断。

---

## 许可证

[MIT](LICENSE)
