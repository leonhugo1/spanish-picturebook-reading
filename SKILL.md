---
name: spanish-picturebook-reading
description: Turn a Spanish picture book (page photos, scans, or a PDF) into a single-file interactive HTML reading lesson — per-page illustration, Spanish text with Chinese subtitles, neural-voice narration, sentence-level grammar glosses and click-to-hear word cards — plus a printable worksheet with a parent answer key. Use when the user wants a Spanish picture-book lesson, 西语绘本精读, 绘本精读课件, or a matching worksheet.
metadata:
  version: "1.3.1"
---

# Spanish picture-book reading

A picture book is driven by images, so the work here is not "article comprehension".
It is **one page → one Spanish line → one Chinese line → the grammar behind it**.

The audience is a Chinese-speaking child starting Spanish: the interface speaks
Chinese, the book stays in Spanish, and the explanation track is spoken Chinese.

## Deliverables — one command, two files

| File | What it is |
|---|---|
| `<stem>_Lectura_Lesson.html` | The lesson: picture-book viewer + intensive handout + pre/post frame |
| `<stem>_Cuaderno_Worksheet.html` | The worksheet, with a folded answer key for the parent |
| `<library>/index.html` | The course library page (Step 5): one card per lesson, linking both files |
| `source/normalized_*.json` | What was built, so it can be rebuilt |

Both finished files carry a **`🏠 课程库` back-to-library button** in the header,
driven by `meta.indexHref` (see Step 5).

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
      └ the card reads the headword; the example line under it reads the sentence
```

Both halves of a word card are narrated: tapping the card plays `book.word.{i}`,
tapping the example sentence plays `book.wordex.{i}`. The example line is dead text
without the second clip — the smoke test fails if it goes missing.

The second view is the **intensive handout**, and it is narrated too — in Chinese,
because that is what it is written in. Every Chinese block gets its own 🗣 button
with the full play/pause state machine (a clip can run half a minute):

```
┌ Página 3 · 第 1 句 ──────────────────────┐
│ Este es un alce.                         │  ← the Spanish stays silent here
│ ┌──────────────────────────────────┐     │
│ │ 译 · 这是一只驼鹿。          [🗣] │     │  ← deep.zh.{N}.{M}
│ └──────────────────────────────────┘     │
│ 语法/词法 ·                          [🗣] │  ← deep.gram.{N}.{M}
│ este = 这个（阳性）…                      │
└──────────────────────────────────────────┘
   deep vocabulary [🗣]  ·  cultural notes [🗣]
```

## Rules

1. **Two tracks, two voices.** Anything the child has to *read* is Spanish and is
   spoken by a Spanish voice; anything that *explains* it is Chinese and is spoken
   by a Chinese voice. A Chinese subtitle printed under a Spanish line is still
   never read aloud — the explanation track is its own recording, made from the
   handout's own text. All narration is pre-recorded neural audio embedded as
   base64; browser system voices are never used. A missing clip shows a red 🔇.
2. **Picture first, then text.** Every page is "look, then read". Pre-reading
   questions should point at the illustration.
3. **Explain in Chinese, name forms in Spanish.** Grammar notes are Chinese prose
   that names the actual form (`ser`, `estar`, `el/la`, `-ar` verbs).
4. **Teach nouns with their article.** `el gato`, never `gato` — gender is half the
   word. The validator enforces this for cards tagged `m.` / `f.`.
5. **Page numbers are unique.** Use `caption` to tell the halves of a spread apart.
6. **Do not redistribute the book.** A finished lesson holds scanned pages of
   someone else's copyrighted work. Keep it in the family; never publish it.
7. **Run `audit_content.py` before every build.** It catches the authoring
   mistakes the validator and the smoke tests cannot see. A lesson that fails
   the audit does not get built — fixing one JSON line now beats rebuilding a
   whole book later.
8. **Never reuse a crop box across books.** Page size and watermark position are
   per-book. Probe every book with `--print-bounds` first.
9. **Two layers of answers.** The child's answers appear only after Submit. The
   parent gets a separate answer key, folded away, that prints on its own sheet.

## Step 1 · Input and page preparation

You need the book (photos, scans, or a PDF) and an output directory.

> ⚠️ **Crop boxes are per-book — never carry them over.** Three RAZ books in a row
> turned out to be 1920×1242 (landscape), 931×1440 (portrait) and 841×595 (square),
> with the watermark band starting around row 20, 195 and 20 respectively. Always
> run `--print-bounds` on the book in front of you and copy the numbers it reports.

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
- `--caption-band L,T,R,B` decides which rows that strip keeps. Its default comes
  from one particular book — give it the band `--print-bounds` reported for *this*
  book, or the strip slices the sentences in half and you transcribe them wrong.
- Output is 1200px wide, JPEG q82, 30–150 KB per page.
- **Portrait books (taller than 2:1) need extra compression.** A portrait page has
  nearly twice the area of a landscape one, so 1200px lands at ~280 KB per page and
  a 5 MB lesson. Add `--width 1000 --quality 80` — visually identical, 4 MB file.

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

Two voices:

| Track | Default | Rate | Override |
|---|---|---|---|
| Spanish (the book, word cards, speaking prompts) | `es-ES-ElviraNeural` | `-12%` | `EDGE_TTS_VOICE` |
| Chinese (the handout's explanations) | `zh-CN-XiaoxiaoNeural` | `+0%` | `EDGE_TTS_CN_VOICE` |

The Spanish track is slower than article pace because the child is following a
highlighted line in a foreign language. The Chinese track keeps a normal pace — it
is the child's first language and the text is already dense.

Other Spanish voices: `es-ES-AlvaroNeural`, `es-MX-DaliaNeural`, `es-AR-ElenaNeural`.
Other Chinese voices: `zh-CN-YunxiNeural`, `zh-CN-XiaoyiNeural`. The Microsoft
*Multilingual* voices (`zh-CN-XiaoxiaoMultilingualNeural`) are **not** available on
the free edge-tts endpoint — requesting one raises `NoAudioReceived`.

Both tracks are mp3 as edge-tts emits them. AAC would shrink the Chinese track by
~40 % (`EDGE_TTS_CN_CODEC=auto` or `=m4a`, needs `afconvert`; the player reads each
segment's type from `INITIAL_DATA.audioMimes`), but it is **not the default** — a
second container is a second way to end up silent on a device you did not test, and
the Chinese track is the one place a mistake is inaudible in every static check.
Expect the Chinese track to roughly double a lesson's file size (about +1.5 MB per
ten-page book) — that is the cost of a narration the child can actually follow.

A `--incremental-audio` rebuild takes seconds instead of minutes: only segments
whose own text changed are re-recorded, and the two tracks invalidate separately —
rewriting a grammar note costs one Chinese clip, never the whole Spanish narration.

## Step 3.5 · Audit the content — before building

`validate.js` checks structure; the smoke tests check that the page runs. Neither
can see the mistakes that actually happen while authoring, so there is a separate
pass for content:

```bash
python3 scripts/audit_content.py .        # lesson + worksheet, exit code 0/1
```

| Check | Why it matters |
|---|---|
| A fill-in answer missing from its own `wordBank` | The child can never produce the right answer — the question is dead |
| A Cyrillic or Greek letter among Latin ones (`buscastе`) | Identical on screen, but it breaks search, TTS and grading |
| Unpaired `¿` / `¡` | The most common OCR and hand-copying error |
| A page's `sentences[].es` not present in that page's `textEs` | The page narration and the sentence narration say **different things** |
| A noun word card without its article | Gender never gets learned (`v.` / `adv.` / `loc.` cards are skipped) |
| HTML inside a plain-text field | It renders as literal markup in front of the child |

Run it **before** `build.js` — finding a missing word-bank entry after the whole
book is written costs ten times more.

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

## Step 5 · Build the course library — once per batch

Finished lessons pile up as `<library>/<NNN-slug>/out/`, and the child needs one
entry point. Generate it:

```bash
python3 scripts/make_index.py <library-root> --books-dir <source PDF folder>
```

It reads every subdirectory's `content.json` and writes `<library-root>/index.html`:
one card per lesson (Spanish title, Chinese title, page count, word-card count,
first objective), buttons into the lesson and into the worksheet, a progress count
at the top, and a collapsible list of the books still to do. **Idempotent — rerun
it whenever you add a lesson.**

### The back-to-library button

Both finished files show a **`🏠 课程库`** button in the header (left of Export /
Print). It is driven by `meta.indexHref` in the JSON:

```json
"meta": { "indexHref": "../../index.html" }
```

The path is **relative to the built HTML file**. Under this skill's layout
(`<library>/<NNN-slug>/out/`) it is always `"../../index.html"`. Leave the field out
and no button is rendered — which is the right choice for a one-off lesson.
Both smoke tests assert that the button appears exactly when the JSON asks for it,
and that it points where the JSON said.

⚠️ It is a relative link: copying a single HTML file somewhere else breaks the
button (the lesson itself is unaffected). Copy the whole library to keep it working.

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
| The next book is cropped into the artwork | its crop box was copied from the previous book | page size is per-book — landscape, portrait and square all occur; always re-probe |
| Caption strip shows half a sentence | `--caption-band` still holds another book's rows | pass the band `--print-bounds` reported for *this* book |
| A portrait lesson is 5 MB | a portrait page has ~2× the area of a landscape one | add `--width 1000 --quality 80` |
| A smoke test fails on every new book | the assertion hard-codes one book's vocabulary | assert on structure (`li` / `<b>` counts) and on values read from `INITIAL_DATA` |
| Build continues after a failed audit | `cmd \| tail` returns *tail's* exit status | use `if ! cmd; then …`, or redirect to a file and read the status |
| The watermark check flags half the artwork | mid-grey pixels are counted, and artwork is grey too | a watermark is a *narrow band spanning the full width* — look at the strip, don't trust the threshold |
| An edit silently did not land | several files edited in the same pass | re-read the changed lines afterwards; never assume the write succeeded |
| The word-card example line is silent | only `book.word.{i}` was recorded, so the example has no clip | record `book.wordex.{i}` from `exampleEs` too — two taps, two clips |
| The reading-aloud section asks for nothing repeatable | its clip was recorded from the Chinese lead-in, so the button spoke Chinese | give every speaking prompt an `es` sentence; *that* is what `post.speak.N` records |
| The handout's explanation buttons are silent | the `deep.*` segments were never collected — the Chinese track is separate from the Spanish one | collect `deep.zh` / `deep.gram` / `deep.vocab` / `deep.cult` too, and let the smoke test assert the count matches |
| Explanation audio loads but never plays | the clip was re-encoded (AAC) while the player still hard-coded `audio/mp3` | carry the type per segment in `INITIAL_DATA.audioMimes`; the smoke test loads one clip for real |
| The explanation reads "★ … = …" aloud | the handout text is written for the eye | run it through `clean_speech()` in `gen_audio.py` before speaking |
| A new Chinese clip re-records the whole Spanish track | one combined voice/fingerprint check invalidated everything | keep the two tracks independent: invalidate per language, on voice *and* codec |
| **Tapping a speaker button does nothing** | the button had a second click listener, so one tap ran `playSeg` twice — the second call stopped the clip the first had just started | wire `.tts` in **exactly one place** (the delegated handler on `document`); never add a per-button listener, just render `class="tts" data-segid="…"` |
| A smoke test passes while the page is silent | it waited for `loadedmetadata`; a clip reports that even when it can never play (wrong mime, unplayable container) | assert a **real tap** reaches `playing`, and that one tap constructs **exactly one** `Audio` |
| Every smoke run dies with exit 137 / SIGTERM | the full browser was launched on a machine that was already short of RAM, and an aborted run leaves ~11 zombie processes behind | prefer `chrome-headless-shell` (now first in the candidate list); `pkill -f chrome-headless-shell` to clear leftovers |

## Boundaries

- **Spanish picture books only.** For English reading comprehension use a
  different tool — this one is built around a book that is read aloud, page by page.
- Do not rewrite the CSS/JS from scratch. Change `assets/*.template` if you truly
  need to, then re-run the smoke tests.
- Do not invent the book's text. Transcribe it.
- The finished lesson contains copyrighted pages. Personal use only.

---
