#!/usr/bin/env node
/**
 * build.js — one command, two deliverables.
 *
 *   node scripts/build.js content.json worksheet.json out/
 *   node scripts/build.js --lesson-only content.json out/
 *   node scripts/build.js --worksheet-only worksheet.json out/
 *
 * Flags
 *   --no-audio             skip narration, build a silent lesson
 *   --force-audio          fail instead of silently shipping a silent lesson
 *   --incremental-audio    reuse recordings whose Spanish text is unchanged
 *
 * A lesson and a worksheet both need `meta.filenameStem`, and the two must match.
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const TPL_LESSON = path.join(ROOT, "assets", "lesson.html.template");
const TPL_WORKSHEET = path.join(ROOT, "assets", "worksheet.html.template");
const GEN_AUDIO = path.join(__dirname, "gen_audio.py");

const LESSON_TYPES = ["spanish_picturebook_reading", "reading_and_writing"];

/* ------------------------------------------------------------------ utils */

function die(msg) {
  console.error("build: " + msg);
  process.exit(1);
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    die(`cannot read ${file}: ${e.message}`);
  }
}

/** JSON that is safe to drop inside a <script> tag. */
function jsonForScript(obj) {
  return JSON.stringify(obj)
    .replace(/</g, "\\u003c")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function checkStem(meta, label) {
  if (!meta || typeof meta !== "object") die(`${label}: meta object is required`);
  if (!meta.filenameStem) die(`${label}: meta.filenameStem is required`);
  if (!/^[A-Za-z0-9_-]+$/.test(meta.filenameStem)) {
    die(`${label}: meta.filenameStem may only contain ASCII letters, digits, "_" and "-"`);
  }
  if (!meta.titleEs && !meta.titleEn) {
    die(`${label}: meta.titleEs (or legacy titleEn) is required`);
  }
  // keep the two spellings mirrored so templates and tools can read either
  meta.titleEs = meta.titleEs || meta.titleEn;
  meta.titleEn = meta.titleEn || meta.titleEs;
  return meta;
}

/* -------------------------------------------------------------- normalize */

function normalizeLesson(raw) {
  if (!raw || typeof raw !== "object") die("lesson: root must be an object");
  const meta = checkStem(raw.meta, "lesson");
  if (!meta.lessonType) die("lesson: meta.lessonType is required");
  if (!LESSON_TYPES.includes(meta.lessonType)) {
    die(`lesson: meta.lessonType must be one of ${LESSON_TYPES.map(t => `"${t}"`).join(", ")}`);
  }
  const pages = raw.pictureBook && raw.pictureBook.pages;
  if (!Array.isArray(pages) || !pages.length) {
    die("lesson: pictureBook.pages must be a non-empty array (this skill builds picture-book lessons)");
  }
  const seen = new Set();
  pages.forEach((p, i) => {
    const n = p.page === undefined ? i + 1 : p.page;
    if (seen.has(n)) die(`lesson: pictureBook.pages[${i}] reuses page number ${n} — page numbers must be unique`);
    seen.add(n);
    if (!p.textEs && !(Array.isArray(p.sentences) && p.sentences.length)) {
      die(`lesson: pictureBook.pages[${i}] (page ${n}) needs textEs or sentences`);
    }
  });

  const out = JSON.parse(JSON.stringify(raw));
  out.meta.badges = out.meta.badges || ["Lectura de cuento", out.meta.titleEs];
  out.meta.footer = out.meta.footer || "Spanish picture-book reading · Lectura guiada de cuento";
  out.teacherTips = out.teacherTips || {};
  out.preReading = out.preReading || {};
  out.whileReading = out.whileReading || {};
  out.postReading = out.postReading || {};
  return out;
}

function normalizeWorksheet(raw) {
  if (!raw || typeof raw !== "object") die("worksheet: root must be an object");
  checkStem(raw.meta, "worksheet");
  for (const key of ["matching", "fillInBlank", "imitation", "summary"]) {
    if (!raw[key]) die(`worksheet: section "${key}" is required`);
  }
  const m = raw.matching.items || [];
  if (m.length < 4 || m.length > 10) die(`worksheet: matching.items must have 4–10 entries (got ${m.length})`);
  const f = raw.fillInBlank.items || [];
  if (f.length < 3 || f.length > 8) die(`worksheet: fillInBlank.items must have 3–8 entries (got ${f.length})`);
  if (!Array.isArray(raw.fillInBlank.wordBank) || raw.fillInBlank.wordBank.length < f.length) {
    die("worksheet: fillInBlank.wordBank must cover every blank");
  }
  const im = raw.imitation.items || [];
  if (im.length < 2 || im.length > 4) die(`worksheet: imitation.items must have 2–4 entries (got ${im.length})`);
  const answers = raw.summary.answers || [];
  if (!answers.length) die("worksheet: summary.answers is required");
  if (!Array.isArray(raw.summary.wordBank) || raw.summary.wordBank.length < answers.length) {
    die("worksheet: summary.wordBank must cover every blank");
  }

  const out = JSON.parse(JSON.stringify(raw));
  out.meta.badges = out.meta.badges || ["Cuaderno del alumno", out.meta.titleEs];
  out.meta.footer = out.meta.footer || "Lectura de cuento · Cuaderno del alumno";
  return out;
}

/* ------------------------------------------------------------------ audio */

/**
 * Find a Python that has edge-tts. Portable: no hard-coded machine paths.
 * Override with PYTHON=/path/to/python3.
 */
function findPython() {
  const cands = [];
  if (process.env.PYTHON) cands.push(process.env.PYTHON);
  if (process.env.VIRTUAL_ENV) {
    cands.push(path.join(process.env.VIRTUAL_ENV, "bin", "python3"));
    cands.push(path.join(process.env.VIRTUAL_ENV, "Scripts", "python.exe"));
  }
  if (process.platform === "win32") {
    cands.push("python", "py");
  } else {
    cands.push("python3", "python");
  }
  for (const c of cands) {
    if (!c) continue;
    const r = spawnSync(c, ["-c", "import edge_tts"], { encoding: "utf8" });
    if (r.status === 0) return c;
  }
  return null;
}

function generateAudio(contentPath, outDir, incremental) {
  const py = findPython();
  if (!py) {
    console.warn("[audio] edge-tts not found (tried PYTHON, VIRTUAL_ENV, python3, python).");
    console.warn("[audio] install it with:  pip install edge-tts");
    console.warn("[audio] the lesson will be built WITHOUT narration.");
    return null;
  }
  const voice = process.env.EDGE_TTS_VOICE || "es-ES-ElviraNeural";
  console.log(`[audio] python: ${py}`);
  console.log(`[audio] voice:  ${voice}`);
  if (incremental) console.log("[audio] mode:   incremental (reuse unchanged segments)");

  const args = [GEN_AUDIO];
  if (incremental) args.push("--incremental");
  args.push(contentPath, outDir);

  const r = spawnSync(py, args, { encoding: "utf8" });
  if (r.stdout) process.stdout.write(r.stdout);
  if (r.status !== 0) {
    console.warn(`[audio] gen_audio.py exited ${r.status}`);
    if (r.stderr) console.warn(r.stderr.trim());
    return null;
  }
  const audioPath = path.join(outDir, "audio.json");
  if (!fs.existsSync(audioPath)) {
    console.warn(`[audio] expected ${audioPath} was not written`);
    return null;
  }
  return JSON.parse(fs.readFileSync(audioPath, "utf8"));
}

/* ------------------------------------------------------------------ build */

function buildLesson(content, outDir, audio) {
  const stem = content.meta.filenameStem;
  const audioSegs = (audio && audio.segments) || {};
  const withAudio = Object.keys(audioSegs).length > 0;
  content.audio = audioSegs;
  content.audioMeta = withAudio
    ? { voice: audio.voice, rate: audio.rate, count: audio.count, generatedAt: new Date().toISOString() }
    : { voice: null, count: 0, note: "no narration — rebuild with audio enabled" };

  const tpl = fs.readFileSync(TPL_LESSON, "utf8")
    .replace(/__TITLE_ES__/g, esc(content.meta.titleEs))
    .replace(/__TITLE_EN__/g, esc(content.meta.titleEs))
    .replace("__INITIAL_DATA_JSON__", jsonForScript(content));

  const outFile = path.join(outDir, `${stem}_Lectura_Lesson.html`);
  fs.writeFileSync(outFile, tpl);
  fs.writeFileSync(path.join(outDir, "source", "normalized_content.json"), JSON.stringify(content, null, 2));
  return { stem, outFile, withAudio };
}

function buildWorksheet(ws, outDir) {
  const stem = ws.meta.filenameStem;
  const tpl = fs.readFileSync(TPL_WORKSHEET, "utf8")
    .replace(/__TITLE_ES__/g, esc(ws.meta.titleEs))
    .replace(/__TITLE_EN__/g, esc(ws.meta.titleEs))
    .replace("__INITIAL_DATA_JSON__", jsonForScript(ws));

  const outFile = path.join(outDir, `${stem}_Cuaderno_Worksheet.html`);
  fs.writeFileSync(outFile, tpl);
  fs.writeFileSync(path.join(outDir, "source", "normalized_worksheet.json"), JSON.stringify(ws, null, 2));
  return { stem, outFile };
}

/* -------------------------------------------------------------------- CLI */

const USAGE = `Usage:
  node scripts/build.js <content.json> <worksheet.json> <out_dir>
  node scripts/build.js --lesson-only <content.json> <out_dir>
  node scripts/build.js --worksheet-only <worksheet.json> <out_dir>

Flags (before the positional arguments):
  --no-audio            build without narration
  --force-audio         abort if narration could not be generated
  --incremental-audio   only re-record changed lines (fast rebuilds)`;

function main() {
  let argv = process.argv.slice(2);
  let mode = "both";
  let audioMode = "auto";

  while (argv[0] && argv[0].startsWith("--")) {
    if (argv[0] === "--no-audio") { audioMode = "off"; argv = argv.slice(1); continue; }
    if (argv[0] === "--force-audio") { audioMode = "force"; argv = argv.slice(1); continue; }
    if (argv[0] === "--incremental-audio") { audioMode = "incremental"; argv = argv.slice(1); continue; }
    if (argv[0] === "--lesson-only") { mode = "lesson"; argv = argv.slice(1); continue; }
    if (argv[0] === "--worksheet-only") { mode = "worksheet"; argv = argv.slice(1); continue; }
    if (argv[0] === "-h" || argv[0] === "--help") { console.log(USAGE); return; }
    die(`unknown flag ${argv[0]}\n\n${USAGE}`);
  }

  let lessonSrc = null, worksheetSrc = null, outDir = null;
  if (mode === "lesson") {
    [lessonSrc, outDir] = argv;
  } else if (mode === "worksheet") {
    [worksheetSrc, outDir] = argv;
  } else if (argv.length === 2) {
    // single package.json with { lesson, worksheet }
    const pkgPath = argv[0];
    outDir = argv[1];
    const pkg = readJson(pkgPath);
    if (!pkg.lesson || !pkg.worksheet) die("package file must contain `lesson` and `worksheet`");
    lessonSrc = { file: pkgPath, data: pkg.lesson };
    worksheetSrc = { file: pkgPath, data: pkg.worksheet };
  } else if (argv.length === 3) {
    [lessonSrc, worksheetSrc, outDir] = argv;
  } else {
    die(USAGE);
  }
  if (!outDir) die(USAGE);

  const lesson = lessonSrc
    ? normalizeLesson(typeof lessonSrc === "object" ? lessonSrc.data : readJson(lessonSrc))
    : null;
  const worksheet = worksheetSrc
    ? normalizeWorksheet(typeof worksheetSrc === "object" ? worksheetSrc.data : readJson(worksheetSrc))
    : null;

  if (lesson && worksheet && lesson.meta.filenameStem !== worksheet.meta.filenameStem) {
    die(`filenameStem mismatch: lesson="${lesson.meta.filenameStem}" worksheet="${worksheet.meta.filenameStem}"`);
  }

  outDir = path.resolve(outDir);
  fs.mkdirSync(path.join(outDir, "source"), { recursive: true });

  // ---- narration ----------------------------------------------------------
  let audio = null;
  if (lesson && audioMode !== "off") {
    const contentPath = path.join(outDir, "source", "normalized_content.json");
    fs.writeFileSync(contentPath, JSON.stringify(lesson, null, 2));
    audio = generateAudio(contentPath, outDir, audioMode === "incremental");
    if (audioMode === "force" && !audio) {
      die("--force-audio was requested but no narration was produced (check Python + edge-tts)");
    }
  }

  // ---- emit ---------------------------------------------------------------
  const written = [];
  let stem = null;
  if (lesson) {
    const r = buildLesson(lesson, outDir, audio);
    stem = r.stem;
    written.push(path.basename(r.outFile));
    console.log(`  narration: ${r.withAudio ? `${Object.keys(lesson.audio).length} clips` : "none"}`);
  }
  if (worksheet) {
    const r = buildWorksheet(worksheet, outDir);
    stem = stem || r.stem;
    written.push(path.basename(r.outFile));
  }

  fs.writeFileSync(
    path.join(outDir, "source", "build-record.json"),
    JSON.stringify(
      {
        builtAt: new Date().toISOString(),
        stem,
        outputs: written,
        audio: lesson
          ? { enabled: !!(audio && audio.count), voice: audio ? audio.voice : null, clips: audio ? audio.count : 0 }
          : null,
      },
      null,
      2
    )
  );

  console.log("\nwrote:");
  written.forEach(f => console.log("  " + path.join(outDir, f)));
}

main();
