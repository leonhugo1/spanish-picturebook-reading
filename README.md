# spanish-picturebook-reading

**English** · [简体中文](README.zh-CN.md)

Turn a **Spanish picture book** — page photos, scans, or a PDF — into a **single-file interactive HTML lesson** plus a **printable worksheet with an answer key for parents**.

Built for a Chinese-speaking child learning Spanish as a foreign language: the interface speaks Chinese, the book stays in Spanish, and every line comes with a translation, a grammar gloss, and a native-sounding recording.

```
scanned pages  →  per-page art + Spanish line + Chinese subtitle + narration
                 + sentence-by-sentence grammar
                 + click-to-hear word cards
                 + worksheet with a parent answer key
```

---

## What you get

| Output | What it is |
|---|---|
| `<stem>_Lectura_Lesson.html` | The lesson. One file, works offline, no server. |
| `<stem>_Cuaderno_Worksheet.html` | The worksheet, with a folded answer key for the parent. |
| `source/normalized_*.json` | The content that was built, so a lesson can be rebuilt or edited. |

### The lesson

- **Per-page illustration** with the Spanish text beside it — the picture is the point, so it stays big.
- **Two-line subtitles**: Spanish in large type, Chinese underneath. Toggle either one off — hide the Spanish to practise listening, hide the Chinese to read unaided.
- **Tap any sentence** to hear just that sentence. "Read the whole page" plays it continuously.
- **Grammar notes per sentence** — gender, verb endings, `ser` vs `estar`, contractions. This is the part a picture book cannot teach by itself.
- **Click-to-hear word cards**, each written with its article (`el gato`, not `gato`, so the gender is learned along with the word).
- **Intensive handout** that automatically gathers every sentence from every page, plus deep vocabulary and cultural notes.
- **Narration is pre-recorded neural TTS**, embedded as base64. The browser's built-in voices are never used — they sound robotic and differ wildly between devices. If a clip is missing you get a red 🔇, never a robot.

### The worksheet

- Matching, cloze, sentence imitation, paragraph imitation, summary cloze.
- **Answers stay hidden until the child submits.**
- **Answer key for the parent**, folded away at the bottom. Expand it and print → it comes out on its own sheet. Leave it folded and print → you get a clean question-only copy.

---

## Quick start

Requires **Node.js 18+**. Narration needs **Python 3 + edge-tts** (optional; you can build a silent lesson with `--no-audio`).

```bash
git clone https://github.com/leonhugo1/spanish-picturebook-reading
cd spanish-picturebook-reading

# optional but recommended, for narration
pip install edge-tts

# try the bundled example (3-page A1 book, generated illustrations)
node scripts/build.js examples/gato-luna/content.json examples/gato-luna/worksheet.json out/

node scripts/validate.js out/
open out/gato-luna_Lectura_Lesson.html
```

That is the whole loop: **write JSON → build → validate**.

---

## From a scanned book to a lesson

Most graded readers in the wild are page-image PDFs with **no text layer**, often stamped with a reseller watermark. `scripts/prep_pages.py` does the mechanical part.

```bash
# 1 · find the crop boxes for this particular book
python3 scripts/prep_pages.py book.pdf build/pages --print-bounds

# 2 · crop the margins, erase the watermark band, and emit a strip of every
#     page's caption line so you can transcribe the whole book in one look
python3 scripts/prep_pages.py book.pdf build/pages \
    --erase-band 196,252 \
    --box 214,196,1466,978 \
    --page-box 1=248,248,1422,1016 \
    --page-box 2=320,205,1110,548 \
    --captions
```

- `--print-bounds` reports the ink bounding box of every page — copy those numbers into `--box`.
- `--erase-band TOP,BOT` **erases a watermark** by copying the clean row just below it up over the band. Because a watermark is light grey and artwork is solid, the fill is invisible. This beats cropping, which would cut into the picture.
- `--captions` writes `_captions.png`: every page's caption line stacked into one image, so you transcribe ten pages in one look instead of opening ten files.
- Output is 1200px-wide progressive JPEG, ~30–150 KB per page.

Then transcribe the Spanish (the caption sheet makes this quick), and write the Chinese translations, grammar notes and word cards — those are the teaching layer, and they are what you author.

> Transcribe carefully: readers and OCR routinely drop the opening `¿` / `¡` and turn `ñ` into `n`. The validator catches the first two; only your eyes catch the third.

---

## Writing the content

Two JSON files (or one combined package). See:

- [`references/lesson-schema.md`](references/lesson-schema.md) — the `pictureBook` block in detail
- [`references/worksheet-schema.md`](references/worksheet-schema.md) — worksheet parts and the answer key

The shape is small — a lesson is a list of pages:

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

`image` must be an inline `data:image/…;base64,` URI — that is what keeps the finished lesson a single offline file. The validator rejects anything else.

---

## Commands

```bash
# build both deliverables
node scripts/build.js content.json worksheet.json out/

# just one
node scripts/build.js --lesson-only content.json out/
node scripts/build.js --worksheet-only worksheet.json out/

# no narration (fast, for checking layout)
node scripts/build.js --no-audio content.json worksheet.json out/

# rebuild after editing a picture or a translation: reuses every unchanged clip
node scripts/build.js --incremental-audio content.json worksheet.json out/

# static checks
node scripts/validate.js out/

# real-browser checks (optional — needs puppeteer-core + any Chrome)
npm install --no-save puppeteer-core
node scripts/smoke_lesson.js    out/*_Lectura_Lesson.html    /tmp/shot.png
node scripts/smoke_worksheet.js out/*_Cuaderno_Worksheet.html /tmp/ak
```

`--incremental-audio` compares each segment's text by hash and only re-records what changed. On a typical 10-page book that is 50-odd clips; editing an illustration or a Chinese gloss re-records **zero** of them, so a rebuild takes under a second instead of minutes.

Only Spanish is ever sent to the speaker. Chinese is a subtitle and is never read aloud.

---

## Narration voices

Default is `es-ES-ElviraNeural` at rate `-12%` — slower than article pace, because the child is decoding a foreign language while following a highlighted line.

| Voice | Accent |
|---|---|
| `es-ES-ElviraNeural` | Castilian, female (default) |
| `es-ES-AlvaroNeural` | Castilian, male |
| `es-MX-DaliaNeural` | Latin American, female |
| `es-MX-JorgeNeural` | Latin American, male |
| `es-AR-ElenaNeural` | Rioplatense, female |
| `es-US-PalomaNeural` | US Spanish, female |

```bash
EDGE_TTS_VOICE=es-MX-DaliaNeural node scripts/build.js content.json worksheet.json out/
```

---

## Layout

```
.
├── SKILL.md                      # instructions for an AI coding agent
├── assets/
│   ├── lesson.html.template      # the lesson shell
│   └── worksheet.html.template   # the worksheet shell
├── references/
│   ├── lesson-schema.md
│   ├── worksheet-schema.md
│   └── release-gates.md          # what to check before calling it done
├── scripts/
│   ├── prep_pages.py             # scanned PDF → web-ready page images
│   ├── build.js                  # one command, two deliverables
│   ├── gen_audio.py              # edge-tts narration (+ incremental reuse)
│   ├── validate.js               # static checks
│   ├── smoke_lesson.js           # browser checks: the lesson
│   ├── smoke_worksheet.js        # browser checks: the worksheet + answer key
│   └── _browser.js               # portable Chrome/Chromium lookup
└── examples/gato-luna/           # generated 3-page A1 example
    ├── content.json
    ├── worksheet.json
    └── make_fixture.py           # regenerates the example (SVG art, no assets)
```

---

## Using it with an AI agent

`SKILL.md` is written to be dropped into an agent's context — it carries the workflow, the rules that matter, and a list of mistakes that actually happen. Point Claude Code / Cursor / Codex / WorkBuddy at it and hand over the book:

> Read SKILL.md. Take the scanned book at `materials/el-gato.pdf`, prepare the pages, write `content.json` and `worksheet.json`, then run `scripts/build.js` and `scripts/validate.js` into `out/`.

---

## Copyright

**This repository contains no picture-book content.** The bundled example is generated SVG art with original text, and the tooling only ever handles files *you* supply.

The books you process are usually somebody's copyrighted work. Reader PDFs are typically sold by resellers who have no right to them either. Keep the output for your own family, do not redistribute a finished lesson, and do not publish a lesson containing scanned pages to the web. `validate.js` refuses to pass a build that embeds a local file path, which keeps accidental machine details out of a shared file — it cannot keep you out of copyright trouble, so use your judgement.

---

## License

[MIT](LICENSE)
