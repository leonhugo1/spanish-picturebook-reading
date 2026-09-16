#!/usr/bin/env node
/**
 * validate.js — static checks on what build.js produced.
 *
 *   node scripts/validate.js <out_dir>
 *   node scripts/validate.js <out_dir> --lesson-only
 *   node scripts/validate.js <out_dir> --worksheet-only
 *
 * This catches the mistakes that actually happen when transcribing a scanned
 * picture book: a dropped opening "¿" / "¡", a noun stored without its article
 * (so the child never learns the gender), a reused page number, an image left
 * as a file path instead of an inline data URI.
 *
 * Passing here is necessary but not sufficient — run the smoke tests too
 * (scripts/smoke_lesson.js, scripts/smoke_worksheet.js).
 */
"use strict";

const fs = require("fs");
const path = require("path");

const outDir = process.argv[2];
const flag = process.argv[3] || "";
if (!outDir) {
  console.error("usage: node scripts/validate.js <out_dir> [--lesson-only|--worksheet-only]");
  process.exit(1);
}

const errors = [];
const notes = [];
function fail(msg) { errors.push(msg); }
function note(msg) { notes.push(msg); }

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    fail(`cannot read ${path.relative(outDir, file)}: ${e.message}`);
    return null;
  }
}

function readHtml(file) {
  if (!fs.existsSync(file)) { fail(`missing output: ${path.basename(file)}`); return null; }
  const html = fs.readFileSync(file, "utf8");
  if (!html.trim()) { fail(`empty output: ${path.basename(file)}`); return null; }
  if (/\/Users\/|\/home\/[a-z]+\//.test(html)) {
    fail(`${path.basename(file)} contains an absolute local path (privacy leak)`);
  }
  return html;
}

/** The build record says whether narration was requested for this output. */
function readBuildRecord() {
  const p = path.join(outDir, "source", "build-record.json");
  if (!fs.existsSync(p)) return null;
  try {
    return JSON.parse(fs.readFileSync(p, "utf8"));
  } catch {
    return null;
  }
}

/** Pull the embedded INITIAL_DATA back out and compare it with the source. */
function checkEmbedded(html, source, label) {
  const m = html.match(/const INITIAL_DATA = (\{[\s\S]*?\});[\s\S]*?const meta\s*=\s*INITIAL_DATA\.meta/);
  if (!m) { fail(`${label}: embedded INITIAL_DATA not found or malformed`); return; }
  let embedded;
  try {
    // the build escapes "<" as \u003c to stay script-safe; JSON.parse handles it
    embedded = JSON.parse(m[1]);
  } catch (e) {
    fail(`${label}: embedded INITIAL_DATA is not valid JSON (${e.message})`);
    return;
  }
  const stripAudio = o => {
    const c = JSON.parse(JSON.stringify(o));
    delete c.audioMeta;
    return c;
  };
  if (JSON.stringify(stripAudio(embedded)) !== JSON.stringify(stripAudio(source))) {
    fail(`${label}: embedded data differs from source/normalized JSON — rebuild with build.js`);
  }
}

function requireMarkup(html, label, needles) {
  for (const n of needles) {
    if (!html.includes(n)) fail(`${label}: template contract missing "${n}"`);
  }
}

/* ------------------------------------------------------------ lesson ---- */

const LESSON_MARKUP = [
  "stage-tab", "panel-pre", "panel-while", "panel-post",
  "view-tab", "view-book", "view-deep",
  "bookStage", "bookPager", "bookDots", "book-line",
  "esToggle", "zhToggle", "bookWords",
  "deepSentences", "deepVocab", "deepCulture",
  "playSeg", "flashNoAudio",
  "--ocean-deep", "Fraunces",
  "data-segid",
];

/**
 * How many Chinese explanation blocks the handout will render. Mirrors the way
 * the lesson template walks the pages (a page with no `sentences` becomes one
 * block from textEs / textZh).
 */
function countDeepBlocks(src) {
  const deep = (src.whileReading || {}).intensiveReading || {};
  let n = 0;
  for (const p of (src.pictureBook || {}).pages || []) {
    const lines = (Array.isArray(p.sentences) && p.sentences.length)
      ? p.sentences
      : (String(p.textEs || "").trim() ? [{ zh: p.textZh || "" }] : []);
    for (const s of lines) {
      if (String(s.zh || "").trim()) n++;
      if (Array.isArray(s.grammar) && s.grammar.length) n++;
    }
  }
  for (const v of deep.deepVocabulary || []) if (v.meaningZh || v.note) n++;
  for (const c of deep.culturalNotes || []) if (String(c.explanation || "").trim()) n++;
  return n;
}

function validateLesson() {
  const src = readJson(path.join(outDir, "source", "normalized_content.json"));
  if (!src) return;
  const stem = src.meta.filenameStem;
  const html = readHtml(path.join(outDir, `${stem}_Lectura_Lesson.html`));
  if (!html) return;

  requireMarkup(html, "lesson", LESSON_MARKUP);
  checkEmbedded(html, src, "lesson");

  const book = src.pictureBook || {};
  const pages = book.pages || [];

  // page numbers must be unique
  const seen = new Set();
  pages.forEach((p, i) => {
    const n = p.page === undefined ? i + 1 : p.page;
    if (seen.has(n)) fail(`books pages: page ${n} is used twice (index ${i})`);
    seen.add(n);

    if (p.image && !/^data:image\//i.test(p.image)) {
      fail(`page ${n}: image must be an inline data:image/... URI so the file stays offline`);
    }
    const lines = (p.sentences || []);
    lines.forEach((s, j) => {
      if (!s || !String(s.es || "").trim()) fail(`page ${n}: sentence ${j + 1} has no Spanish text`);
    });
    if (!p.textEs && !lines.length) fail(`page ${n}: needs textEs or sentences`);
  });

  // Spanish punctuation must be paired — OCR drops the opening mark all the time
  const spLines = [];
  pages.forEach(p => {
    if (p.textEs) spLines.push([p.page, p.textEs]);
    (p.sentences || []).forEach((s, j) => { if (s.es) spLines.push([`${p.page}.${j + 1}`, s.es]); });
  });
  for (const [where, txt] of spLines) {
    if (/\?/.test(txt) && !/¿/.test(txt)) fail(`page ${where}: question is missing its opening "¿" — "${txt}"`);
    if (/!/.test(txt) && !/¡/.test(txt)) fail(`page ${where}: exclamation is missing its opening "¡" — "${txt}"`);
  }

  // nouns should be taught with their article so gender comes along for free
  (book.wordCards || []).forEach((w, i) => {
    if (!w.es || !w.zh) fail(`wordCards[${i}]: needs both es and zh`);
    if (/^(m|f)\.?$/i.test(String(w.pos || "").trim()) && !/^(el|la|los|las)\s/i.test(String(w.es).trim())) {
      fail(`wordCards[${i}]: noun "${w.es}" must be written with its article ("el gato", not "gato")`);
    }
    if (w.image && !/^data:image\//i.test(w.image)) {
      fail(`wordCards[${i}]: image must be an inline data:image/... URI`);
    }
  });

  // the pre / post frame is optional but, if present, must be usable
  const pre = src.preReading || {};
  if (pre.keyWords && (pre.keyWords.length < 1 || pre.keyWords.length > 8)) {
    fail(`preReading.keyWords should be 1–8 items (got ${pre.keyWords.length})`);
  }
  const speaking = (src.postReading || {}).speaking;
  if (speaking && !(speaking.prompts || []).length) {
    note("postReading.speaking has no prompts — the speaking section will look empty");
  }

  // narration coverage
  const segCount = Object.keys(src.audio || {}).length;
  const record = readBuildRecord();
  const builtSilent = !!(record && record.audio && record.audio.enabled === false);
  if (segCount === 0) {
    if (builtSilent) {
      note("built with --no-audio: no narration. Fine for a layout pass or CI, not for delivery.");
    } else {
      fail("lesson has no narration (audio is empty) — edge-tts was probably unavailable; rebuild without --no-audio");
    }
  } else {
    // gen_audio.py records how many clips the content asked for; a shortfall
    // means a recording failed, which no other check would notice.
    const planned = (src.audioMeta && src.audioMeta.planned) || 0;
    if (planned && segCount < planned) {
      fail(`narration is incomplete: ${segCount} clips embedded but the content needs ${planned} — re-run the build`);
    }
    const esCount = Object.keys(src.audio || {}).filter(k => !k.startsWith("deep.")).length;
    if (esCount === 0) fail("no Spanish narration in the lesson");
    const deepExpected = countDeepBlocks(src);
    const deepCount = Object.keys(src.audio || {}).filter(k => k.startsWith("deep.")).length;
    if (deepExpected && !deepCount) {
      note(`the handout has ${deepExpected} Chinese explanation block(s) but no explanation audio — rebuild to record them`);
    }
  }

  console.log(JSON.stringify({
    ok: errors.length === 0,
    artifact: `${stem}_Lectura_Lesson.html`,
    pages: pages.length,
    sentences: pages.reduce((a, p) => a + (p.sentences || []).length, 0),
    wordCards: (book.wordCards || []).length,
    narrationClips: segCount,
    audioVoice: (src.audioMeta || {}).voice || null,
  }, null, 2));
}

/* --------------------------------------------------------- worksheet ---- */

const WORKSHEET_MARKUP = [
  "sec-match", "sec-fill", "sec-imit", "sec-pimit", "sec-sum",
  "answerKey", "akToggle", "akBody",
  "submitBtn", "retryBtn", "scoreOut",
  "matchLeft", "matchRight", "fillBank", "fillList", "sumBank", "sumList",
  "show-answers", "blank",
];

function validateWorksheet() {
  const src = readJson(path.join(outDir, "source", "normalized_worksheet.json"));
  if (!src) return;
  const stem = src.meta.filenameStem;
  const html = readHtml(path.join(outDir, `${stem}_Cuaderno_Worksheet.html`));
  if (!html) return;

  requireMarkup(html, "worksheet", WORKSHEET_MARKUP);
  checkEmbedded(html, src, "worksheet");
  checkAnswerKey(html, src);

  const blanks = (src.summary.answers || []).length;
  console.log(JSON.stringify({
    ok: errors.length === 0,
    artifact: `${stem}_Cuaderno_Worksheet.html`,
    matching: (src.matching.items || []).length,
    fillInBlank: (src.fillInBlank.items || []).length,
    imitation: (src.imitation.items || []).length,
    paragraphImitation: src.paragraphImitation ? "yes" : "no",
    summaryBlanks: blanks,
    answerKey: true,
  }, null, 2));
}

function checkAnswerKey(html, src) {
  // the key is folded away by default and only printed once expanded
  if (!/body\.show-answers\s+\.ak-body\s*\{\s*display\s*:\s*block/i.test(html)) {
    fail("worksheet: answer key must be hidden until body.show-answers is set");
  }
  if (!/break-before\s*:\s*page|page-break-before\s*:\s*always/i.test(html)) {
    fail("worksheet: answer key needs a print page break so it prints on its own sheet");
  }
  if (!/body:not\(\.show-answers\)\s+#answerKey\s*\{\s*display\s*:\s*none/i.test(html)) {
    fail("worksheet: a folded answer key must not print at all");
  }
  // open-ended tasks should carry a sample answer for the parent
  const missing = (src.imitation.items || [])
    .map((it, i) => (it.sampleAnswer ? null : i + 1))
    .filter(Boolean);
  if (missing.length) {
    note(`imitation item(s) ${missing.join(", ")} have no sampleAnswer — the answer key will just say "open-ended"`);
  }
  if (src.paragraphImitation && !src.paragraphImitation.sampleAnswer) {
    note("paragraphImitation has no sampleAnswer — the answer key will just describe the structure");
  }
}

/* ---------------------------------------------------------------- run ---- */

const lessonPath = path.join(outDir, "source", "normalized_content.json");
const wsPath = path.join(outDir, "source", "normalized_worksheet.json");

if (flag === "--lesson-only") validateLesson();
else if (flag === "--worksheet-only") validateWorksheet();
else {
  if (fs.existsSync(lessonPath)) validateLesson();
  if (fs.existsSync(wsPath)) validateWorksheet();
  if (!fs.existsSync(lessonPath) && !fs.existsSync(wsPath)) {
    fail(`${outDir} does not look like a build output (no source/normalized_*.json)`);
  }
}

if (notes.length) {
  console.log("\nnotes:");
  notes.forEach(n => console.log("  · " + n));
}
if (errors.length) {
  console.error("\nvalidation FAILED:");
  errors.forEach(e => console.error("  ✗ " + e));
  process.exit(1);
}
console.log("\nvalidation OK");
