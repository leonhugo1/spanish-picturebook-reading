#!/usr/bin/env python3
"""
Content audit for a Spanish picture-book lesson — run it BEFORE build.js.

`validate.js` checks structure and `smoke_*.js` check that the page runs. Neither
can see the mistakes that actually happen while authoring:

  * a fill-in answer that is not in its own word bank (the child can never
    produce it, so the question is unanswerable)
  * a Cyrillic/Greek character pasted in among Spanish text (`buscastе` with a
    Cyrillic е looks identical on screen and breaks search, TTS and grading)
  * a dropped inverted punctuation mark (`¿` / `¡`)
  * a page sentence that does not appear in that page's full text — which means
    the audio for the page and the audio for the sentence say different things
  * a noun word-card without its article
  * stray HTML inside a field the template renders as plain text

Usage:
    python3 scripts/audit_content.py <lesson_dir>          # reads content.json + worksheet.json
    python3 scripts/audit_content.py <content.json> <worksheet.json>

Exit code is 0 when clean, 1 when anything is flagged — safe to use as a gate.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HTML_TAG = re.compile(r"<[a-zA-Z/][^>]*>")
NON_LATIN = re.compile(r"[\u0370-\u03FF\u0400-\u04FF]")  # Greek + Cyrillic
ARTICLE = re.compile(r"^(el|la|los|las|un|una)\s", re.I)
# Only *nouns* must carry an article. Multi-word phrases and non-noun parts of
# speech (debajo de, por todos lados, buscar, allí…) legitimately have none.
NON_NOUN_POS = ("v.", "adv", "loc", "prep", "conj", "interj", "pron", "ger", "part", "num", "adj")
NO_ARTICLE_OK = {"buscar", "dormir", "vivir", "allí", "ahí", "aquí"}


def walk(obj, path=""):
    """Yield (json_path, string) for every string in the document."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def load_lesson(target: Path) -> tuple[Path, dict, dict]:
    if target.is_dir():
        cpath, wpath = target / "content.json", target / "worksheet.json"
    else:
        cpath, wpath = target, Path(sys.argv[2])
    if not cpath.exists():
        raise SystemExit(f"error: not found: {cpath}")
    content = json.loads(cpath.read_text(encoding="utf-8"))
    worksheet = json.loads(wpath.read_text(encoding="utf-8")) if wpath.exists() else {}
    return cpath.parent, content, worksheet


def audit(root: Path, content: dict, worksheet: dict) -> list[str]:
    bad: list[str] = []

    # ---- 1. stems must match, or build.js will refuse to pair them
    cs = content.get("meta", {}).get("filenameStem")
    ws = worksheet.get("meta", {}).get("filenameStem")
    if ws and cs != ws:
        bad.append(f"filenameStem 不一致：content={cs!r} worksheet={ws!r}")

    # ---- 2. fill-in answers must exist in their own word bank
    fb = worksheet.get("fillInBlank") or {}
    if fb:
        bank = set(fb.get("wordBank") or [])
        if len(bank) < len(fb.get("items") or []):
            bad.append(f"fillInBlank.wordBank 只有 {len(bank)} 个词，题目 {len(fb.get('items', []))} 个")
        for i, it in enumerate(fb.get("items") or []):
            if it.get("answer") not in bank:
                bad.append(f"fillInBlank[{i}] 答案 {it.get('answer')!r} 不在 wordBank —— 这题无解")
            for a in it.get("accepted") or []:
                if a not in bank:
                    bad.append(f"fillInBlank[{i}] accepted {a!r} 不在 wordBank")

    # ---- 3. summary blanks must line up with the answer list
    su = worksheet.get("summary") or {}
    if su:
        sbank = set(su.get("wordBank") or [])
        idx: list[int] = []

        def collect(o):
            if isinstance(o, dict) and "blank" in o:
                idx.append(o["blank"])
            elif isinstance(o, list):
                for x in o:
                    collect(x)

        collect(su.get("segments") or [])
        answers = su.get("answers") or []
        for i, a in enumerate(answers):
            if a not in sbank:
                bad.append(f"summary.answers[{i}] {a!r} 不在 wordBank")
        if sorted(idx) != list(range(len(answers))):
            bad.append(f"summary 空位下标 {sorted(idx)} 与 answers（{len(answers)} 个）对不上")

    # ---- 4. pages: unique numbers, non-empty text, sentences inside that text
    book = content.get("pictureBook") or {}
    pages = book.get("pages") or []
    nums = [p.get("page") for p in pages]
    if len(set(nums)) != len(nums):
        bad.append(f"页码重复：{nums}")
    for p in pages:
        label = f"p{p.get('page')}"
        text = (p.get("textEs") or "").strip()
        if not text:
            bad.append(f"{label} 缺 textEs")
        if not p.get("image"):
            bad.append(f"{label} 缺内嵌图片")
        for j, s in enumerate(p.get("sentences") or []):
            es = (s.get("es") or "").strip()
            if not es:
                bad.append(f"{label} sentences[{j}] 是空的")
            elif text and es not in text and text not in es:
                bad.append(
                    f"{label} sentences[{j}] 与整页 textEs 不一致 —— "
                    f"整页配音和逐句配音会说不同的话：{es[:40]!r}"
                )

    # ---- 5. word cards: nouns need their article (that is how gender gets learned)
    for i, w in enumerate(book.get("wordCards") or []):
        es = (w.get("es") or "").strip()
        pos = (w.get("pos") or "").strip().lower()
        if not es:
            bad.append(f"wordCards[{i}] 缺 es")
            continue
        if any(pos.startswith(p) for p in NON_NOUN_POS):
            continue
        if not ARTICLE.match(es) and es.lower() not in NO_ARTICLE_OK and not es[0].isupper():
            bad.append(f"wordCards[{i}] {es!r} 看起来是裸名词，应连着冠词（el / la）")

    # ---- 6. character hygiene + Spanish punctuation, across both files
    for src, name in ((content, "课件"), (worksheet, "练习册")):
        for path, s in walk(src):
            if HTML_TAG.search(s):
                bad.append(f"{name} {path} 里有 HTML 标签（模板按纯文本渲染）")
            m = NON_LATIN.search(s)
            if m:
                bad.append(
                    f"{name} {path} 混入了非拉丁字符 {m.group()!r}(U+{ord(m.group()):04X}) —— "
                    f"多半是西里尔/希腊字母冒充拉丁字母：{s[:60]!r}"
                )
            if path.endswith(".es") or path.endswith(".answer"):
                if s.count("¿") != s.count("?") and "?" in s:
                    bad.append(f"{name} {path} 的 ¿ 不成对：{s[:60]!r}")
                if s.count("¡") != s.count("!") and "!" in s:
                    bad.append(f"{name} {path} 的 ¡ 不成对：{s[:60]!r}")

    return bad


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    root, content, worksheet = load_lesson(Path(sys.argv[1]).expanduser())
    bad = audit(root, content, worksheet)

    pages = len((content.get("pictureBook") or {}).get("pages") or [])
    cards = len((content.get("pictureBook") or {}).get("wordCards") or [])
    print(f"[audit] {root}")
    print(f"[audit] {pages} 页 · {cards} 张单词卡")
    if bad:
        print(f"[audit] ✗ 发现 {len(bad)} 个问题：")
        for b in bad:
            print(f"        · {b}")
        return 1
    print("[audit] ✓ 内容自审通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
