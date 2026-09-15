# Release gates

Static validation passing is **not** a release claim. After `build.js` and
`validate.js` succeed, run the browser smoke tests and look at the result
yourself.

## Automated — must pass

```bash
node scripts/validate.js out/
node scripts/smoke_lesson.js    out/*_Lectura_Lesson.html    /tmp/shot.png
node scripts/smoke_worksheet.js out/*_Cuaderno_Worksheet.html /tmp/ak
```

Both smoke tests must print `SMOKE OK`.

`smoke_lesson.js` drives a real browser and asserts:

1. the picture-book data is embedded and the lesson opens on the book view
2. the illustration rendered (not a placeholder)
3. every sentence row rendered, with its Chinese subtitle present
4. grammar notes are present
5. the progress dots match the page count
6. word cards rendered in the same number as the data
7. the intensive handout folded in every sentence
8. narration clips are embedded
9. turning the page advances the pager and moves the dot
10. "previous" is disabled on page 1 and enabled afterwards
11. the hide-Spanish toggle applies the blur class *and* the blur is real
12. a word-card tap is wired
13. no JavaScript errors

`smoke_worksheet.js` asserts:

1. the answer key exists and is folded by default
2. the CSS keeps it hidden until expanded, hides it from a plain print, and
   forces a page break when expanded
3. all five exercises were built with the expected number of items
4. tapping a bank chip fills a blank
5. expanding sets `show-answers`, flips `aria-expanded` and renames the button
6. every objective answer is listed, imitation has sample answers, and the
   summary shows the finished passage
7. Submit marks the sheet and displays a score
8. no JavaScript errors

## By eye — the automated checks cannot see these

9. **Narration sounds right.** Tap "read the whole page" and a single sentence:
   it should be Spanish, at a natural-but-slow pace, not English and not a
   robotic system voice.
10. **Illustrations are clean.** Check a couple of pages for a leftover reseller
    watermark. A watermark that sits *over* the artwork needs `--erase-band`; one
    that sits in the margin just needs a tighter crop box.
11. **Vendor the text against the book.** Pick three sentences at random and
    compare with the page. Watch for a dropped opening `¿` / `¡` and for `ñ`
    transcribed as `n` — the validator catches the former, not the latter.
12. **Tablet width.** At under 900px the illustration should stack above the text
    and the page buttons should not overflow.
13. **File size.** A lesson should stay under ~20 MB. If it is bigger, the page
    images were not compressed (see `prep_scripts.py --print-bounds` /
    `--width` / `--quality`).
14. **Print both versions.** With the answer key folded, print: you should get the
    questions only. Expand it, print: the key must come out on its own sheet and
    must not be hidden behind the sticky submit bar.
15. **Open questions have answers.** The key should show `sampleAnswer` for
    imitation and paragraph imitation. If it says "open-ended" with nothing else,
    the content JSON is missing those fields.

## Do not claim a release if

- a new HTML shell was hand-written instead of building from the templates
- the CSS or JS was regenerated from scratch
- a browser system voice is doing the narration
- Chinese is being read aloud
- images are referenced by path rather than inlined (the file will not work offline)
- the smoke tests were not run, or were run and did not reach `SMOKE OK`
- the lesson contains scanned pages of a copyrighted book **and** is about to be
  shared publicly
