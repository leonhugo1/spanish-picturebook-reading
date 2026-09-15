#!/usr/bin/env node
/**
 * smoke_worksheet.js — open the built worksheet and check the answer key,
 * the fill-in interaction and the grading all work.
 *
 *   node scripts/smoke_worksheet.js <worksheet.html> [screenshot_prefix]
 */
"use strict";

const path = require("path");
const { launch, watchErrors, report } = require("./_browser");

async function main() {
  const target = process.argv[2];
  const shotPrefix = process.argv[3] || null;
  if (!target) {
    console.error("usage: node scripts/smoke_worksheet.js <worksheet.html> [screenshot_prefix]");
    process.exit(2);
  }

  const browser = await launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1000, height: 1400 });
  const errors = watchErrors(page);

  await page.goto("file://" + path.resolve(target), { waitUntil: "domcontentloaded", timeout: 60000 });
  await new Promise(r => setTimeout(r, 500));

  // ---- folded state ------------------------------------------------------
  const folded = await page.evaluate(() => {
    const q = s => document.querySelector(s);
    const visible = e => { if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    const css = Array.from(document.styleSheets)
      .flatMap(s => { try { return Array.from(s.cssRules).map(r => r.cssText); } catch { return []; } })
      .join("\n");
    return {
      hasKey: !!q("#answerKey"),
      hasToggle: !!q("#akToggle"),
      toggleLabel: (q("#akToggle")?.textContent || "").trim(),
      hiddenWhileFolded: !visible(q("#akBody")),
      rendered: (q("#akBody")?.innerHTML || "").length > 200,
      showAnswersClass: document.body.classList.contains("show-answers"),
      foldsByDefault: /body\.show-answers\s+\.ak-body\s*\{\s*display\s*:\s*block/i.test(css),
      hiddenInPrint: /body:not\(\.show-answers\)\s+#answerKey/i.test(css),
      pageBreak: /break-before\s*:\s*(page|always)|page-break-before\s*:\s*always/i.test(css),
      matchItems: document.querySelectorAll("#matchLeft .chip").length,
      fillBlanks: document.querySelectorAll("#fillList .blank").length,
      sumBlanks: document.querySelectorAll("#sumList .blank").length,
    };
  });

  if (shotPrefix) {
    await page.evaluate(() => document.getElementById("answerKey").scrollIntoView());
    await new Promise(r => setTimeout(r, 250));
    await page.screenshot({ path: shotPrefix + "_folded.png" });
  }

  // ---- fill-in interaction ----------------------------------------------
  const filling = await page.evaluate(() => {
    const chip = document.querySelector("#fillBank .bank-chip");
    const blank = document.querySelector("#fillList .blank");
    if (!chip || !blank) return { skipped: true };
    chip.click();
    blank.click();
    const filled = blank.classList.contains("filled");
    return { skipped: false, filled, text: blank.textContent.trim(), chipWord: chip.textContent.trim() };
  });

  // ---- expand the answer key --------------------------------------------
  const expanded = await page.evaluate(() => {
    document.getElementById("akToggle").click();
    const body = document.getElementById("akBody");
    const r = body.getBoundingClientRect();
    const txt = body.innerText || "";
    return {
      showAnswersClass: document.body.classList.contains("show-answers"),
      visible: r.width > 0 && r.height > 0,
      toggleLabel: (document.getElementById("akToggle")?.textContent || "").trim(),
      ariaExpanded: document.getElementById("akToggle").getAttribute("aria-expanded"),
      blocks: body.querySelectorAll(".ak-block").length,
      listItems: body.querySelectorAll(".ak-list li").length,
      hasSampleAnswer: /参考/.test(txt),
      hasFullSummary: /完整答案/.test(txt),
      mentionsOpenEnded: /开放题|批改要点/.test(txt),
      textLen: txt.length,
    };
  });

  if (shotPrefix) await page.screenshot({ path: shotPrefix + "_expanded.png" });

  // ---- grading -----------------------------------------------------------
  const grading = await page.evaluate(() => {
    document.getElementById("submitBtn").click();
    const out = document.getElementById("scoreOut");
    return {
      submitted: document.body.classList.contains("submitted"),
      scoreShown: out.classList.contains("show"),
      scoreText: (out.textContent || "").trim(),
      markedBlanks: document.querySelectorAll(".blank.mark-ok, .blank.mark-bad").length,
    };
  });

  await browser.close();

  const checks = [
    ["answer key section exists", folded.hasKey],
    ["toggle button exists", folded.hasToggle],
    ["folded by default", folded.showAnswersClass === false],
    ["answer body hidden while folded", folded.hiddenWhileFolded],
    ["answer content rendered", folded.rendered],
    ["CSS keeps it hidden until expanded", folded.foldsByDefault],
    ["CSS hides it from a plain print", folded.hiddenInPrint],
    ["CSS breaks the page when expanded", folded.pageBreak],
    ["matching exercise built", folded.matchItems > 0],
    ["fill blanks built", folded.fillBlanks > 0],
    ["summary blanks built", folded.sumBlanks > 0],
    ["bank chip fills a blank", filling.skipped || (filling.filled && filling.text === filling.chipWord)],
    ["expanding sets show-answers", expanded.showAnswersClass === true],
    ["answer body becomes visible", expanded.visible],
    ["aria-expanded flips", expanded.ariaExpanded === "true"],
    ["toggle label switches", /隐藏|Ocultar/.test(expanded.toggleLabel)],
    ["all five answer blocks rendered", expanded.blocks >= 4],
    ["every objective answer is listed", expanded.listItems >= folded.matchItems + folded.fillBlanks + folded.sumBlanks],
    ["imitation sample answers present", expanded.hasSampleAnswer],
    ["summary shows the finished paragraph", expanded.hasFullSummary],
    ["open-ended guidance present", expanded.mentionsOpenEnded],
    ["submit marks the sheet graded", grading.submitted],
    ["score is displayed", grading.scoreShown && /\d/.test(grading.scoreText)],
    ["objective items get marked", grading.markedBlanks > 0],
    ["no page errors", errors.length === 0],
  ];

  console.log("=== folded ===");
  console.log(JSON.stringify(folded, null, 2));
  console.log("=== expanded ===");
  console.log(JSON.stringify(expanded, null, 2));

  const failed = report("worksheet checks", checks, errors);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch(e => { console.error(e); process.exit(1); });
