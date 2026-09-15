---
name: spanish-picturebook-reading
description: Turn a Spanish picture book (page photos, scans, or a PDF) into a single-file interactive HTML reading lesson — per-page illustration, Spanish text with Chinese subtitles, neural-voice narration, sentence-level grammar glosses and click-to-hear word cards — plus a printable worksheet with a parent answer key. Use when the user wants a Spanish picture-book lesson, 西语绘本精读, 绘本精读课件, or a matching worksheet.
metadata:
  version: "1.0.0"
---

# Spanish picture-book reading

A picture book is driven by images, so the work here is not "article comprehension".
It is **one page → one Spanish line → one Chinese line → the grammar behind it**.

The audience is a Chinese-speaking child starting Spanish: the interface speaks
Chinese, the book stays in Spanish, and Chinese is never spoken aloud.

## Deliverables — one command, two files

| File | What it is |
|---|---|
| `<stem>_Lectura_Lesson.html` | The lesson: picture-book viewer + intensive handout + pre/post frame |
| `<stem>_Cuaderno_Worksheet.html` | The worksheet, with a folded answer key for the parent |
| `source/normalized_*.json` | What was built, so it can be rebuilt |

Content lives in JSON; layout lives in locked templates. **Never hand-edit a
built HTML file** — edit the JSON and rebuild.

## What the lesson looks like

```
┌ Página 2 / 12 ──────────  hide Spanish · hide Chinese ┐
│ ┌──────────────┐  ┌──────────────────────────────┐   │
│ │              │  │ ▶ read the page              │   │
│ │ illustration │  │ La luna es muy grande.  🔊   │   │  ← Spanish, large
│ │  (base64)    │  │ 月亮很大。                     │   │  ← Chinese, small
│ │              │  │ ┌ grammar · ser + adjective ┐│   │
│ └──────────────┘  └──────────────────────────────┘   │
│              ‹ prev   ●●○  next ›                     │
└───────────────────────────────────────────────────────┘
   word cards · Palabras clave   [🐱 el gato] [🌙 la luna] …
```

## Rules

1. **Only Spanish reaches the speaker.** Chinese is a subtitle. All narration is
   pre-recorded neural audio embedded as base64; browser system voices are never
   used. A missing clip shows a red 🔇 instead.
2. **Picture first, then text.** Every page is "look, then read". Pre-reading
   questions should point at the illustration.
3. **Explain in Chinese, name forms in Spanish.** Grammar notes are Chinese prose
   that names the actual form (`ser`, `estar`, `el/la`, `-ar` verbs).
4. **Teach nouns with their article.** `el gato`, never `gato` — gender is half the
   word. The validator enforces this for cards tagged `m.` / `f.`.
5. **Page numbers are unique.** Use `caption` to tell the halves of a spread apart.
6. **Do not redistribute the book.** A finished lesson holds scanned pages of
   someone else's copyrighted work. Keep it in the family; never publish it.
7. **Two layers of answers.** The child's answers appear only after Submit. The
   parent gets a separate answer key, folded away, that prints on its own sheet.

## Step 1 · Input and page preparation

You need the book (photos, scans, or a PDF) and an output directory.

Scanned readers usually have **no text layer** and often carry a reseller
watermark across the top of every spread. Do the mechanical part with the script:

```bash
# 1 · find the crop boxes for this book
python3 scripts/prep_pages.py book.pdf build/pages --print-bounds

# 2 · crop the margins, erase the watermark band, and emit a caption strip
python3 scripts/prep_pages.py book.pdf build/pages \
    --erase-band 196,252 \
    --box 214,196,1466,978 \
    --page-box 1=248,248,1422,1016 \
    --captions
```

- `--erase-band TOP,BOT` **erases a watermark** by copying the clean row just below
  the band up over it. Watermarks are light grey and artwork is solid, so the fill
  is invisible — and unlike cropping it does not cut into the picture.
- `--box` / `--page-box` crop the margins and footer. Coordinates are in *rendered*
  pixels, so always run `--print-bounds` first and copy what it reports.
- `--captions` writes `_captions.png`: every page's caption line stacked into one
  image, so you transcribe the whole book in one look instead of opening ten files.
- Output is 1200px wide, JPEG q82, 30–150 KB per page.

Then transcribe the Spanish. **Check 2–3 pages against the originals** — reading a
scan drops the opening `¿` / `¡` and confuses `ñ` with `n`. The validator catches
the first two; only your eyes catch the third.

The original text is transcribed. The Chinese translation, grammar notes and word
cards are **yours to write**.

## Step 2 · Write the JSON

Read [references/lesson-schema.md](references/lesson-schema.md) and
[references/worksheet-schema.md](references/worksheet-schema.md).

The lesson is essentially a list of pages:

```json
{
  "meta": { "titleEs": "El gato y la luna", "titleZh": "猫与月亮",
            "filenameStem": "gato-luna", "lessonType": "spanish_picturebook_reading",
            "objectives": ["…"], "timeEstimate": "读前 3 分钟 · 精读 10 分钟" },
  "pictureBook": {
    "pages": [{
      "page": 1,
      "image": "data:image/jpeg;base64,…",
      "textEs": "Es de noche. El gato mira la luna.",
      "textZh": "天黑了。猫看着月亮。",
      "sentences": [
        { "es": "Es de noche.", "zh": "天黑了。",
          "grammar": ["ser 的第三人称单数 es + de noche，固定说法「是夜晚」"] }
      ],
      "note": "先看图再看字：问孩子 ¿Qué ves?"
    }],
    "wordCards": [{ "es": "el gato", "zh": "猫", "pos": "m.", "emoji": "🐱" }]
  },
  "preReading": { "leadIn": {}, "prediction": {}, "keyWords": [] },
  "whileReading": { "intensiveReading": { "deepVocabulary": [], "culturalNotes": [] } },
  "postReading": { "predictionCheck": {}, "speaking": {}, "textToSelf": {},
                   "textToWorld": {}, "exitTicket": {} }
}
```

Notes:

- `image` **must** be an inline `data:image/…;base64,` URI — that is what keeps the
  lesson a single offline file. Anything else fails validation.
- `grammar` is where the lesson earns its keep. One point per string, naming the
  form and the rule. `["这是动词"]` is not a grammar note.
- The intensive handout is **generated from the page sentences** — never retype them
  into `intensiveReading`. That block only holds `deepVocabulary` and `culturalNotes`.
- The pre/post frame is optional; the template renders whatever is present.
- The worksheet accepts 4–10 matching items, 3–8 cloze, 2–4 imitation, and an
  optional `paragraphImitation`. **Write `sampleAnswer` on open-ended items** —
  otherwise the answer key can only say "open-ended", which is no help to a parent.

## Step 3 · Build

```bash
# both deliverables
node scripts/build.js content.json worksheet.json out/

# one of them
node scripts/build.js --lesson-only content.json out/

# fast pass while iterating on layout
node scripts/build.js --no-audio --lesson-only content.json out/

# after editing an illustration or a translation: reuses every unchanged clip
node scripts/build.js --incremental-audio content.json worksheet.json out/
```

Narration needs **Python 3 + edge-tts**; point `PYTHON` at the interpreter if it is
not on `PATH`. Without edge-tts the lesson builds silently — fine for a layout
pass, not for delivery.

Default voice is `es-ES-ElviraNeural` at rate `-12%` — slower than article pace,
because the child is following a highlighted line in a foreign language. Override
with `EDGE_TTS_VOICE` (`es-ES-AlvaroNeural`, `es-MX-DaliaNeural`, `es-AR-ElenaNeural`…).

A `--incremental-audio` rebuild on a ten-page book takes under a second instead of
minutes: only segments whose Spanish text changed are re-recorded.

## Step 4 · Verify — required

```bash
node scripts/validate.js out/
npm install --no-save puppeteer-core        # once; the smoke tests are optional
node scripts/smoke_lesson.js    out/*_Lectura_Lesson.html    /tmp/shot.png
node scripts/smoke_worksheet.js out/*_Cuaderno_Worksheet.html /tmp/ak
```

Both smoke tests must print `SMOKE OK`. They drive a real browser (any
Chrome/Chromium; set `CHROME_PATH` to point at one) and check the things a static
read cannot: that the book actually renders, that paging works, that the answer
key is folded until expanded, that printing behaves.

Then finish with [references/release-gates.md](references/release-gates.md) —
including the items only a human can judge: does the narration sound right, is
there a watermark left on a page, does the finished file fit on a tablet.

## Mistakes that actually happen

| Symptom | Cause | Fix |
|---|---|---|
| Lesson is 30 MB and will not open on a tablet | page images embedded raw | run them through `prep_pages.py` (or `sips -Z 1200`) first |
| A reseller watermark sits on the artwork | cropped, not erased | `--erase-band TOP,BOT` — copy a clean row up over the band |
| Child learns the wrong punctuation | the opening `¿` / `¡` was dropped while transcribing | the validator fails the build; transcription must be checked by eye too |
| Gender never sticks | word cards store bare nouns | write `el gato`; the validator rejects `gato` when `pos` is `m.`/`f.` |
| Word card ends up blank when tapped | its inner HTML was handed to the button-state helper | cards are divs — play the clip without touching their contents |
| Narration is silent in Safari but fine in Chrome | mp3 with a partial trailing frame | `gen_audio.py` trims it; keep that step |
| Audio never plays | Blob URL, or `crossOrigin` set on a data URI | use the `data:audio/mp3;base64,…` URL directly and set nothing else |
| Rebuild takes minutes for a one-word fix | full re-record | `--incremental-audio` |
| Answer key printed with the questions | it was expanded, or the print rule was lost | fold it for the child's copy; the CSS breaks the page when expanded |
| Parent cannot mark the open questions | `sampleAnswer` was never written | add it to imitation / paragraphImitation |
| Two pages collide | the same `page` number used twice | one number per page; `caption` distinguishes a spread |

## Boundaries

- **Spanish picture books only.** For English reading comprehension use a
  different tool — this one is built around a book that is read aloud, page by page.
- Do not rewrite the CSS/JS from scratch. Change `assets/*.template` if you truly
  need to, then re-run the smoke tests.
- Do not invent the book's text. Transcribe it.
- The finished lesson contains copyrighted pages. Personal use only.
