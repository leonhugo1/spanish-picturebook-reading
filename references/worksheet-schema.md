# Worksheet schema

The worksheet JSON root has `meta` plus the exercise parts. Layout comes from
`assets/worksheet.html.template`.

```jsonc
{
  "meta": { "titleEs": "…", "filenameStem": "…" },
  "matching":          { "directions": "…", "items": [ … ] },
  "fillInBlank":       { "directions": "…", "wordBank": [ … ], "items": [ … ] },
  "imitation":         { "directions": "…", "items": [ … ] },
  "paragraphImitation":{ "directions": "…", "modelParagraph": "…", "logicSteps": [ … ], "scenarios": [ … ] },
  "summary":           { "directions": "…", "wordBank": [ … ], "segments": [ … ], "answers": [ … ] }
}
```

`meta.filenameStem` **must match the lesson's** — the build refuses a mismatch.

## meta

Required: `titleEs` (or legacy `titleEn`), `filenameStem`.

Optional: `titleZh`, `timeEstimate`, `directions` (a global instruction line),
`badgeLine`, `footer`.

## matching

Spanish word ↔ Chinese meaning.

- `directions`
- `items`: **4–10** × `{ word, meaning }`
  - `word` — Spanish, nouns written with their article (`el carro`). Plain text.
  - `meaning` — **Chinese.** Not a Spanish definition: the child is a Chinese
    speaker, and defining `cerca` as `cerca de algo` teaches nothing.

Pairs are shuffled at runtime, and a wrong pick flashes red instead of sticking.

## fillInBlank

Cloze with a shared word bank.

- `directions`
- `wordBank`: strings, at least as many as there are items
- `items`: **3–8** ×
  - `before` — text before the blank
  - `after` — text after the blank (often `". 天黑了。"` — the Chinese gloss lives here)
  - `answer` — the expected word
  - `accepted` — optional other acceptable spellings

The child taps a bank chip and then a blank. Tapping a filled blank clears it.

## imitation

Sentence imitation.

- `directions`
- `items`: **2–4** ×
  - `pattern` — a short label for the structure (`por + 地点`)
  - `example` — the sentence from the book
  - `scenarios`: **1–2** Chinese prompts describing a new context
  - `sampleAnswer` — **write this.** It is what the parent sees in the answer key.
    Leave it out and that item is marked "open-ended" with nothing to compare against.

The student never sees `sampleAnswer`; it appears only in the answer key.

## paragraphImitation

Optional. Omit the whole block and the section hides itself.

- `directions`
- `sourceTag`, `sourceTitle` — where the model comes from (`Páginas 3–10`)
- `modelParagraph` — the model paragraph, plain text
- `logicSteps`: **≥2** × `{ id, labelEs?, labelZh }` — shown as a chip chain so the
  child can see the structure to follow
- `scenarios`: **1–3** × `{ id, titleZh, titleEs?, prompt }` — pick a scenario
- `sampleAnswer` — optional; goes in the answer key

## summary

Guided summary cloze.

- `directions`
- `wordBank`: ≥ the number of blanks (add a distractor or two)
- `segments`: an alternating list —
  - a **string** renders as text
  - `{ "blank": N }` renders an input, where `N` is the 0-based index into `answers`
- `answers`: one string per blank

Keep the finished text short: **15–80 words** for a simple book, up to ~180 for a
longer one. Split into several items rather than one dense block.

## The answer key

The worksheet always ends with an answer key (Clave de respuestas). **You do not
write it** — it is assembled from the fields above:

| Section | What the key shows |
|---|---|
| matching | word — Chinese meaning, listed |
| fillInBlank | **the completed sentence**, answer in bold, plus any `accepted` variants |
| imitation | the model sentence + `sampleAnswer`; otherwise "open-ended" |
| paragraphImitation | model + required structure + `sampleAnswer` + marking guidance |
| summary | each blank's answer, then **the whole passage with the blanks filled in** |

Behaviour:

- **Folded by default.** The child never sees it.
- The parent expands it with the button, and **printing then puts it on its own
  sheet** (a page break is forced).
- Printing while folded produces a clean question-only copy — the answer key is
  removed entirely, not merely collapsed.
- A closing line reminds the parent that objective items are marked against the
  key while open-ended ones are judged on structure and sense.

## Rules

- Matching glosses and `summary.directions` are Chinese; the Spanish side is the
  book's language. Do not mix.
- Every answer must be traceable to the book or to the lesson's grammar notes.
- If you skip `sampleAnswer` on imitation / paragraphImitation, the validator
  prints a note so you notice before a parent does.
