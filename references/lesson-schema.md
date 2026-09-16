# Lesson schema

The JSON root has `meta`, an optional `teacherTips`, the `pictureBook` block, and
three stage objects: `preReading`, `whileReading`, `postReading`.

Stage names are fixed. Layout, CSS and behaviour all come from
`assets/lesson.html.template` — this schema only carries content.

```jsonc
{
  "meta": { /* see below */ },
  "pictureBook": { "bookTitle": "…", "level": "A1", "pages": [ … ], "wordCards": [ … ] },
  "preReading":  { "leadIn": {…}, "prediction": {…}, "keyWords": [ … ] },
  "whileReading": { "intensiveReading": { "deepVocabulary": [ … ], "culturalNotes": [ … ] } },
  "postReading": { "predictionCheck": {…}, "speaking": {…}, "textToSelf": {…},
                   "textToWorld": {…}, "exitTicket": {…} }
}
```

The three stages are optional in practice — the template renders whatever is
there and shows a placeholder for what is not. A lesson can be **just a
`pictureBook`** and it will still work.

## meta

| Field | Required | Notes |
|---|---|---|
| `titleEs` | ✔ | The book's Spanish title. Shown as the page heading. |
| `titleZh` | | Chinese title, shown as a subtitle. |
| `filenameStem` | ✔ | ASCII letters, digits, `_`, `-`. Becomes the output filename. **The lesson and worksheet must share it.** |
| `lessonType` | ✔ | `spanish_picturebook_reading` (legacy `reading_and_writing` also accepted). |
| `objectives` | | 3–5 learning goals, shown in the hero. |
| `timeEstimate` | | Short timing note. |
| `badgeLine` | | Hero badge text. Defaults to `Lectura de cuento`. |
| `footer` | | Page footer. |

## pictureBook

### pages[]

One entry per book page or spread.

| Field | Required | Notes |
|---|---|---|
| `page` | recommended | Page number. Defaults to the array index + 1. **Must be unique** — the validator rejects duplicates. Use `caption` to distinguish a left/right half of one spread. |
| `image` | recommended | Inline `data:image/…;base64,` URI. Any other form fails validation, because an external path would break the single-file guarantee. Omit it and the page renders a "no illustration" placeholder. |
| `caption` | | Small caption under the picture. |
| `textEs` | ✔* | The page's Spanish text. Narrated as one continuous clip. |
| `textZh` | | Chinese gist of the whole page, shown under the Spanish. |
| `sentences[]` | ✔* | Per-sentence breakdown — see below. |
| `note` | | Teaching note for this page, rendered as a highlighted card. |

\* at least one of `textEs` / `sentences` is required.

### pages[].sentences[]

| Field | Required | Notes |
|---|---|---|
| `es` | ✔ | The sentence in Spanish. |
| `zh` | | Chinese translation — the small subtitle line. Never narrated. |
| `grammar` | recommended | Array of **Chinese** grammar/lexis notes, one point each. |

`grammar` is where the teaching actually happens. Compare:

```json
{ "es": "El gato quiere tocarla.", "zh": "猫想摸摸它。",
  "grammar": [
    "querer + 动词原形：quiere tocar → quiere tocarla",
    "直接宾语代词 la 后置并连写：tocar + la = tocarla，指 la luna"
  ] }
```

```json
{ "es": "El gato quiere tocarla.", "grammar": ["这是动词", "注意语法"] }   // ✗ teaches nothing
```

A good note names the form, gives the rule, and points at something visible in
the sentence. Keep each note to one sentence.

### wordCards[]

Click-to-hear vocabulary cards.

| Field | Required | Notes |
|---|---|---|
| `es` | ✔ | **Write nouns with their article** — `el gato`, not `gato`. The validator enforces this when `pos` is `m.`/`f.`, because the gender is half the word. |
| `zh` | ✔ | Chinese gloss. |
| `pos` | | Part of speech (`m.`, `f.`, `v.`, `ger.`…). |
| `image` | | Optional inline data URI. |
| `emoji` | | Fallback visual when there is no image. |
| `exampleEs` | | Example sentence shown on the card. **Narrated**: tapping the example line plays `book.wordex.{i}`, so a child can hear the word in context. |

## preReading

Optional but worth writing — a book with no lead-in starts cold.

- `leadIn`: `{ prompt, placeholder?, tipKey? }`
- `prediction`: `{ hint?, prompt, placeholder? }`
- `keyWords`: 1–8 flip cards `{ word, meaning, example }`

## whileReading.intensiveReading

The per-sentence handout is **generated from `pictureBook.pages[].sentences[]`**
— never retype the same sentences here. This block only carries what the book
pages do not:

- `deepVocabulary[]`: `{ word, pos?, meaningZh, collocations[]?, note? }`
- `culturalNotes[]`: `{ term?, context?, explanation }`

## postReading

All five are optional; the template renders whichever are present.

- `predictionCheck`: `{ prompt, placeholder? }`
- `speaking`: `{ hint?, prompts: [{ prompt?, es, zh? }] }` — the child **reads a sentence
  aloud**, so every prompt supplies one:
  - `prompt` — Chinese lead-in shown above the sentence (never narrated)
  - `es` — **the Spanish sentence to read aloud**; this is what `post.speak.N` records
  - `zh` — its Chinese meaning, shown small underneath
  Give a concrete, complete sentence — not a frame with blanks. The child should be
  able to press 🔊, hear the whole sentence, and repeat it.
- `textToSelf`: `{ prompt, placeholder? }`
- `textToWorld`: `{ prompt, placeholder?, sides: [{ id, label }] }`
- `exitTicket`: `{ prompt, placeholder?, tipKey? }`

## teacherTips

A map of key → Chinese guidance. Attach one to an activity with `tipKey`, and an
`i` button appears next to it.

```json
"teacherTips": { "leadin": "先让孩子用中文说说他看到了什么，再引入西语词。" }
```

## Narration

Every speaker button plays a clip from `INITIAL_DATA.audio`, keyed by segment id.
`scripts/gen_audio.py` builds those clips from the content, so these ids are a
contract between the two:

| segId | Content |
|---|---|
| `book.page.{N}` | Whole page N, read continuously |
| `book.sent.{N}.{M}` | Sentence M of page N |
| `book.word.{i}` | Word card i (Spanish only) |
| `book.wordex.{i}` | The example sentence on word card i |
| `pre.kw.{i}` | Pre-reading key word i |
| `post.speak.{i}` | Speaking prompt i (1-based) |

Rules:

- **Spanish only.** Chinese is a subtitle; it is never spoken.
- Clips are pre-recorded and embedded as base64. Browser system voices are never
  used — they sound robotic and vary between devices. A missing clip shows a red
  🔇, never a fallback voice.
- Changing an illustration, a Chinese gloss or a grammar note does **not** change
  any segment text, so `--incremental-audio` re-records nothing.
- Playback uses a `data:audio/mp3;base64,…` URL directly. Do not switch to Blob
  URLs (rejected in some hardened browser configurations) and do not set
  `crossOrigin` on a data URI.
- `gen_audio.py` trims a partial MP3 frame off the tail. WebKit rejects padded
  files at EOF and the line goes silent; keep that trim if you touch the script.

## Authoring rules

- Do not invent the book's words. Transcribe them. Translations, grammar and word
  cards are yours to write; the original is not.
- Spanish punctuation comes in pairs — `¿…?` and `¡…!`. Transcribing from a scan
  drops the opening mark constantly, which teaches the child the wrong thing. The
  validator catches it.
- Nouns go in word cards with their article.
- Page numbers must be unique.
- Compress page images before embedding them (see `prep_pages.py`). A raw phone
  photo inside base64 turns a lesson into a 30 MB file that will not open on a
  tablet.
