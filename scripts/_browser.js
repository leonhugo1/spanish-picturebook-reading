/**
 * _browser.js — locate a Chromium for the smoke tests, portably.
 *
 * Resolution order:
 *   1. CHROME_PATH environment variable
 *   2. a Playwright-managed Chromium in the usual cache directories
 *   3. a system Chrome / Chromium install
 *
 * The smoke tests need `puppeteer-core` (npm i -D puppeteer-core) plus any
 * Chrome-like binary. They are optional: build.js and validate.js never touch
 * a browser.
 */
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

function globish(dir, pattern) {
  // tiny directory scan so we don't pull in a glob dependency
  let entries;
  try {
    entries = fs.readdirSync(dir);
  } catch {
    return [];
  }
  const re = new RegExp("^" + pattern.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") + "$");
  return entries.filter(e => re.test(e)).map(e => path.join(dir, e)).sort().reverse();
}

function candidates() {
  const home = os.homedir();
  const out = [];

  // 2 · Playwright caches.
  //
  // `chrome-headless-shell` comes first on purpose: it is the same engine built
  // for headless only, so it starts faster and uses noticeably less memory than
  // the full browser. On a machine that is already short on RAM, launching the
  // full one can get the whole process SIGTERM'd mid-run.
  const pwRoots = [
    path.join(home, "Library", "Caches", "ms-playwright"), // macOS
    path.join(home, ".cache", "ms-playwright"),             // Linux
    path.join(process.env.LOCALAPPDATA || "", "ms-playwright"), // Windows
  ];
  for (const root of pwRoots) {
    for (const dir of globish(root, "chromium_headless_shell-*")) {
      out.push(path.join(dir, "chrome-headless-shell-mac-arm64", "chrome-headless-shell"));
      out.push(path.join(dir, "chrome-headless-shell-mac-x64", "chrome-headless-shell"));
      out.push(path.join(dir, "chrome-headless-shell-linux64", "chrome-headless-shell"));
      out.push(path.join(dir, "chrome-headless-shell-win64", "chrome-headless-shell.exe"));
    }
    for (const dir of globish(root, "chromium-*")) {
      out.push(path.join(dir, "chrome-mac-arm64", "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing"));
      out.push(path.join(dir, "chrome-mac-x64", "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing"));
      out.push(path.join(dir, "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"));
      out.push(path.join(dir, "chrome-linux", "chrome"));
      out.push(path.join(dir, "chrome-win", "chrome.exe"));
    }
  }

  // puppeteer caches
  for (const root of [path.join(home, ".cache", "puppeteer"), path.join(home, "Library", "Caches", "puppeteer")]) {
    for (const dir of globish(root, "chrome*")) {
      out.push(path.join(dir, "chrome-mac-arm64", "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing"));
      out.push(path.join(dir, "chrome-mac-x64", "Google Chrome for Testing.app", "Contents", "MacOS", "Google Chrome for Testing"));
      out.push(path.join(dir, "chrome-linux64", "chrome"));
      out.push(path.join(dir, "chrome-win64", "chrome.exe"));
    }
  }

  // 3 · system installs
  out.push(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
  );
  return out;
}

function findChromium() {
  if (process.env.CHROME_PATH) {
    if (fs.existsSync(process.env.CHROME_PATH)) return process.env.CHROME_PATH;
    console.warn(`[smoke] CHROME_PATH is set but not found: ${process.env.CHROME_PATH}`);
  }
  for (const c of candidates()) {
    if (c && fs.existsSync(c)) return c;
  }
  return null;
}

async function launch() {
  let puppeteer;
  try {
    puppeteer = require("puppeteer-core");
  } catch {
    console.error("[smoke] puppeteer-core is not installed.");
    console.error("[smoke]   npm install --no-save puppeteer-core");
    console.error("[smoke] (the smoke tests are optional — build + validate work without a browser)");
    process.exit(2);
  }
  const exe = findChromium();
  if (!exe) {
    console.error("[smoke] no Chrome/Chromium found.");
    console.error("[smoke] install one, or point CHROME_PATH at an existing binary.");
    process.exit(2);
  }
  console.log(`[smoke] chrome: ${exe}`);
  return puppeteer.launch({
    executablePath: exe,
    headless: "new",
    args: ["--no-sandbox", "--allow-file-access-from-files", "--autoplay-policy=no-user-gesture-required"],
  });
}

/** Attach error collectors that ignore the failures an offline sandbox causes. */
function watchErrors(page) {
  const errors = [];
  page.on("pageerror", e => errors.push("pageerror: " + e.message));
  page.on("console", m => {
    if (m.type() !== "error") return;
    const t = m.text();
    if (/fonts\.(googleapis|gstatic)\.com|ERR_(INTERNET|NAME|CONNECTION)/.test(t)) return;
    if (/no recording for|no audio for/.test(t)) return; // expected in a --no-audio build
    errors.push("console: " + t);
  });
  return errors;
}

function report(title, checks, errors) {
  console.log(`\n=== ${title} ===`);
  let failed = 0;
  for (const [name, ok] of checks) {
    console.log((ok ? "  PASS  " : "  FAIL  ") + name);
    if (!ok) failed++;
  }
  if (errors && errors.length) {
    console.log("=== page errors ===");
    errors.forEach(e => console.log("  " + e));
  }
  console.log(failed === 0 ? "\nSMOKE OK" : `\nSMOKE FAILED (${failed})`);
  return failed;
}

module.exports = { findChromium, launch, watchErrors, report };
