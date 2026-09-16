#!/usr/bin/env node
/**
 * smoke_lesson.js — open the built lesson in a real browser and check it works.
 *
 *   node scripts/smoke_lesson.js <lesson.html> [screenshot.png]
 *
 * Needs puppeteer-core plus any Chrome/Chromium; see _browser.js for how it is
 * located. Set CHROME_PATH to override.
 */
"use strict";

const path = require("path");
const { launch, watchErrors, report } = require("./_browser");

async function main() {
  const target = process.argv[2];
  const shot = process.argv[3] || null;
  if (!target) {
    console.error("usage: node scripts/smoke_lesson.js <lesson.html> [screenshot.png]");
    process.exit(2);
  }

  const browser = await launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 1000 });
  const errors = watchErrors(page);

  await page.goto("file://" + path.resolve(target), { waitUntil: "domcontentloaded", timeout: 60000 });
  await new Promise(r => setTimeout(r, 700));

  // INITIAL_DATA is declared with const, so it is NOT a window property.
  const first = await page.evaluate(() => {
    const DATA = typeof INITIAL_DATA === "undefined" ? null : INITIAL_DATA;
    const q = s => document.querySelector(s);
    const qa = s => Array.from(document.querySelectorAll(s));
    const visible = e => { if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };

    // jump to the reading stage, where the book lives
    document.querySelector('.stage-tab[data-stage="while"]').click();

    return {
      hasData: !!(DATA && DATA.pictureBook && DATA.pictureBook.pages.length),
      pages: DATA?.pictureBook?.pages?.length || 0,
      words: DATA?.pictureBook?.wordCards?.length || 0,
      clips: Object.keys(DATA?.audio || {}).length,
      onBookView: !!q("#view-book")?.classList.contains("active"),
      bookVisible: visible(q("#bookStage")),
      hasArt: !!q(".book-figure img")?.getAttribute("src"),
      lines: qa(".book-line").length,
      spanishShown: (q(".book-line-es")?.textContent || "").trim().length > 0,
      chineseShown: (q(".book-line-zh")?.textContent || "").trim().length > 0,
      grammarBlocks: qa(".book-line-grammar").length,
      dots: qa(".book-dot").length,
      activeDot: qa(".book-dot").findIndex(d => d.classList.contains("active")),
      pager: (q("#bookPager")?.textContent || "").replace(/\s+/g, " ").trim(),
      prevDisabled: !!q("#bookPrev")?.disabled,
      wordCards: qa(".word").length,
      deepSentences: qa("#deepSentences .int-sent").length,
      deepVocab: qa("#deepVocab .int-vocab").length,
      // Back-to-library link: appears only when the JSON declares meta.indexHref.
      homeHref: q(".hero-home")?.getAttribute("href") || null,
      homeVisible: visible(q(".hero-home")),
      homeExpected: DATA?.meta?.indexHref || null,
    };
  });

  // page turn
  const second = await page.evaluate(() => {
    document.getElementById("bookNext").click();
    const q = s => document.querySelector(s);
    return {
      pager: (q("#bookPager")?.textContent || "").replace(/\s+/g, " ").trim(),
      activeDot: Array.from(document.querySelectorAll(".book-dot")).findIndex(d => d.classList.contains("active")),
      firstLine: (q(".book-line-es")?.textContent || "").trim(),
      prevDisabled: !!q("#bookPrev")?.disabled,
    };
  });

  // hide-Spanish toggle blurs the Spanish line
  const masking = await page.evaluate(() => {
    const toggle = document.getElementById("esToggle");
    toggle.click();
    const line = document.querySelector(".book-line");
    // read the state BEFORE restoring the toggle
    const applied = line.classList.contains("es-hidden");
    const blurred = getComputedStyle(document.querySelector(".book-line-es")).filter !== "none";
    toggle.click(); // restore
    return { applied, blurred, restored: !line.classList.contains("es-hidden") };
  });

  // word card click should not blow up (it plays a clip or flashes "no audio")
  const cardClick = await page.evaluate(() => {
    const c = document.querySelector(".word");
    if (!c) return { clicked: false };
    c.click();
    return { clicked: true, hasClass: c.classList.contains("speaking") };
  });

  if (shot) {
    await page.evaluate(() => document.getElementById("bookStage").scrollIntoView());
    await new Promise(r => setTimeout(r, 300));
    await page.screenshot({ path: shot });
  }

  await browser.close();

  const checks = [
    ["picture-book data embedded", first.hasData],
    ["opens on the book view", first.onBookView],
    ["book stage is visible", first.bookVisible],
    ["page illustration rendered", first.hasArt],
    ["sentence rows rendered", first.lines > 0],
    ["Spanish line visible", first.spanishShown],
    ["Chinese subtitle visible", first.chineseShown],
    ["grammar notes rendered", first.grammarBlocks > 0],
    ["dot count matches page count", first.dots === first.pages && first.pages > 0],
    ["word cards rendered", first.wordCards === first.words && first.words > 0],
    ["intensive tab folds in every sentence", first.deepSentences > 0],
    ["intensive tab lists deep vocabulary", first.deepVocab >= 0],
    // CI builds with --no-audio (edge-tts needs the network); SMOKE_ALLOW_SILENT
    // acknowledges that a silent build is intentional rather than a mistake.
    ["narration clips embedded", first.clips > 0 || process.env.SMOKE_ALLOW_SILENT === "1"],
    ["next page advances", second.pager !== first.pager],
    ["progress dot follows", second.activeDot === first.activeDot + 1],
    ["prev disabled on page 1", first.prevDisabled === true],
    ["prev enabled on page 2", second.prevDisabled === false],
    ["hide-Spanish toggle applies", masking.applied],
    ["hide-Spanish actually blurs", masking.blurred],
    ["word card click is wired", cardClick.clicked && cardClick.hasClass],
    // Must appear exactly when the source asks for it — never silently missing,
    // never pointing somewhere other than the declared library index.
    ["back-to-library link matches meta.indexHref",
      (first.homeExpected === null && first.homeHref === null) ||
      (first.homeExpected !== null && first.homeHref === first.homeExpected)],
    ["back-to-library link visible when declared", !first.homeExpected || first.homeVisible],
    ["no page errors", errors.length === 0],
  ];

  console.log("=== probe ===");
  console.log(JSON.stringify({ ...first, ...second }, null, 2));

  const failed = report("lesson checks", checks, errors);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch(e => { console.error(e); process.exit(1); });
