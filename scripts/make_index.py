#!/usr/bin/env python3
"""
Generate the course-library index page for a folder of picture-book lessons.

Every lesson lives in its own `<NNN-slug>/` folder holding `content.json`,
`worksheet.json` and an `out/` directory with the built HTML. This script walks
those folders and writes a single `<course_root>/index.html` that links both
files of every finished lesson, plus a "still to do" list built from the source
PDF folder when one is given.

Lessons get a 🏠 课程库 button in their header pointing back here — set
`meta.indexHref` in the lesson JSON (from `out/` that is `"../../index.html"`).

Usage:
    python3 scripts/make_index.py <course_root>
    python3 scripts/make_index.py <course_root> --books-dir ~/Downloads/绘本/C

Re-run it after building a new lesson; it is idempotent.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

BOOK_RE = re.compile(r"^(\d{3})\.\s*(.+?)(?:淘宝.*)?$")

HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --sand:#FBF5E9; --sand-deep:#F2E7D3;
    --ocean-deep:#0D5A62; --ocean-mid:#16818A; --ocean-light:#DCF0EE;
    --coral:#E2703A; --coral-light:#FBE4D6;
    --gold:#E0A233; --gold-light:#FBEBCB;
    --ink:#1C2B2E; --ink-soft:#4B5D60;
    --line:#E4DAC5; --radius:14px;
  }
  *{ box-sizing:border-box; }
  body{ margin:0; background:var(--sand); color:var(--ink);
        font-family:system-ui,-apple-system,'PingFang SC','Segoe UI',sans-serif;
        line-height:1.6; -webkit-font-smoothing:antialiased; }
  .display{ font-family:Georgia,'Songti SC','Times New Roman',serif; }
  .stripe{ height:8px; background:repeating-linear-gradient(90deg,
           var(--coral) 0 24px, var(--gold) 24px 48px, var(--ocean-mid) 48px 72px, var(--ink) 72px 74px); }

  header.hero{ background:linear-gradient(180deg, var(--ocean-deep) 0%, #0A464C 100%);
               color:var(--sand); padding:34px 24px 30px; }
  .hero-inner{ max-width:1180px; margin:0 auto; }
  .kicker{ font-size:12px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
           color:var(--gold); margin-bottom:10px; }
  h1{ margin:0 0 8px; font-size:34px; line-height:1.2; }
  .sub{ margin:0 0 16px; max-width:70ch; color:rgba(251,245,233,.82); font-size:15px; }
  .stats{ display:flex; gap:22px; flex-wrap:wrap; }
  .stat{ font-size:13px; color:rgba(251,245,233,.72); }
  .stat b{ display:block; font-size:22px; color:var(--sand); font-weight:700; }

  main{ max-width:1180px; margin:0 auto; padding:34px 24px 60px; }
  h2.section{ font-size:19px; margin:0 0 16px; display:flex; align-items:center; gap:10px; }
  h2.section span.count{ font-size:13px; font-weight:500; color:var(--ink-soft); }

  .grid{ display:grid; gap:18px; grid-template-columns:repeat(auto-fill, minmax(292px, 1fr)); }
  .card{ background:#fff; border:1px solid var(--line); border-radius:var(--radius);
         padding:20px 20px 18px; display:flex; flex-direction:column;
         box-shadow:0 1px 2px rgba(28,43,46,.04); transition:box-shadow .16s ease, transform .16s ease; }
  .card:hover{ box-shadow:0 6px 18px rgba(28,43,46,.09); transform:translateY(-1px); }
  .card.done{ border-top:4px solid var(--ocean-mid); }
  .card.todo{ border-top:4px solid var(--line); background:var(--sand-deep); }
  .num{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; font-weight:700;
        color:var(--coral); letter-spacing:.08em; margin-bottom:6px; }
  .card h3{ margin:0 0 4px; font-size:20px; line-height:1.25; }
  .zh{ font-size:13px; color:var(--ink-soft); margin-bottom:12px; }
  .tags{ display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
  .tag{ font-size:11px; font-weight:600; padding:3px 9px; border-radius:999px;
        background:var(--ocean-light); color:var(--ocean-deep); }
  .tag.gold{ background:var(--gold-light); color:#8A6212; }
  .obj{ font-size:13px; color:var(--ink-soft); margin:0 0 16px; flex:1;
        display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .actions{ display:flex; gap:8px; flex-wrap:wrap; margin-top:auto; }
  .btn{ font-size:13px; font-weight:600; text-decoration:none; padding:9px 15px; border-radius:999px;
        border:1px solid var(--line); color:var(--ink); background:var(--sand);
        transition:background .15s ease, border-color .15s ease; }
  .btn:hover{ background:var(--sand-deep); border-color:#D8CBB0; }
  .btn.primary{ background:var(--ocean-deep); border-color:var(--ocean-deep); color:#fff; }
  .btn.primary:hover{ background:var(--ocean-mid); border-color:var(--ocean-mid); }
  .missing{ font-size:12px; color:var(--coral); font-weight:600; }

  details.todo-list{ margin-top:34px; border-top:1px dashed var(--line); padding-top:22px; }
  details.todo-list summary{ cursor:pointer; font-weight:600; font-size:15px; color:var(--ink-soft); }
  details.todo-list ol{ margin:14px 0 0; padding-left:0; list-style:none;
                        columns:2; column-gap:28px; font-size:13px; color:var(--ink-soft); }
  @media (max-width:640px){ details.todo-list ol{ columns:1; } }
  details.todo-list li{ break-inside:avoid; padding:2px 0; }
  details.todo-list b{ font-family:ui-monospace,Menlo,monospace; color:var(--coral); font-weight:700; }

  footer{ max-width:1180px; margin:0 auto; padding:0 24px 50px;
          font-size:12px; color:var(--ink-soft); }
</style>
</head>
<body>
"""


def build_card_lesson(folder: Path) -> dict | None:
    cj = folder / "content.json"
    if not cj.exists():
        return None
    try:
        data = json.loads(cj.read_text(encoding="utf-8"))
    except Exception:
        return None
    meta = data.get("meta", {})
    book = data.get("pictureBook", {})
    out = folder / "out"
    return {
        "num": folder.name[:3],
        "slug": folder.name,
        "titleEs": meta.get("titleEs") or meta.get("titleEn") or folder.name,
        "titleZh": meta.get("titleZh", ""),
        "pages": len(book.get("pages") or []),
        "cards": len(book.get("wordCards") or []),
        "obj": (meta.get("objectives") or [""])[0],
        "lesson": next((p.name for p in sorted(out.glob("*_Lectura_Lesson.html"))), None),
        "worksheet": next((p.name for p in sorted(out.glob("*_Cuaderno_Worksheet.html"))), None),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("course_root")
    ap.add_argument("--books-dir", default=None,
                    help="folder of source PDFs, used to list the lessons still to do")
    ap.add_argument("--title", default="西班牙语绘本精读 · 课程库")
    args = ap.parse_args()

    root = Path(args.course_root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"error: not a folder: {root}")

    lessons = [c for c in (build_card_lesson(d) for d in sorted(root.iterdir()) if d.is_dir()) if c]
    lessons.sort(key=lambda x: x["num"])
    done_nums = {l["num"] for l in lessons}

    pending: list[tuple[str, str]] = []
    all_books = 0
    if args.books_dir:
        bd = Path(args.books_dir).expanduser().resolve()
        for pdf in sorted(bd.glob("*.pdf")):
            m = BOOK_RE.match(pdf.stem)
            if not m:
                continue
            all_books += 1
            if m.group(1) not in done_nums:
                pending.append((m.group(1), m.group(2).strip()))

    total_pages = sum(l["pages"] for l in lessons)
    total_cards = sum(l["cards"] for l in lessons)
    built = sum(1 for l in lessons if l["lesson"])
    total_books = all_books or len(lessons)

    parts = [HEAD.replace("__TITLE__", html.escape(args.title))]
    parts.append(f"""
<header class="hero">
  <div class="hero-inner">
    <div class="kicker">Español · Lectura de cuentos · Nivel C</div>
    <h1 class="display">{html.escape(args.title)}</h1>
    <p class="sub">把一本西语绘本变成单文件交互课件（逐句点读 + 中西双行字幕 + 可点击发声单词卡）
       和一份可打印练习册（含家长答案页）。全部离线可用，不需要网络。</p>
    <div class="stats">
      <div class="stat"><b>{len(lessons)} / {total_books}</b>已完成</div>
      <div class="stat"><b>{total_pages}</b>页绘本</div>
      <div class="stat"><b>{total_cards}</b>张单词卡</div>
      <div class="stat"><b>{built}</b>套课件已构建</div>
    </div>
  </div>
</header>
<div class="stripe"></div>
<main>
  <h2 class="section">📚 已完成 <span class="count">{len(lessons)} 课</span></h2>
  <div class="grid">""")

    for l in lessons:
        tags = [f'{l["pages"]} 页', f'{l["cards"]} 张单词卡']
        if l["worksheet"]:
            tags.append("含答案页")
        tag_html = "".join(
            f'<span class="tag{" gold" if t == "含答案页" else ""}">{html.escape(t)}</span>' for t in tags
        )
        rel = f'{l["slug"]}/out/'
        if l["lesson"]:
            actions = (f'<a class="btn primary" href="{html.escape(rel + l["lesson"])}">📖 精读课件</a>')
            if l["worksheet"]:
                actions += f'<a class="btn" href="{html.escape(rel + l["worksheet"])}">✏️ 练习册</a>'
        else:
            actions = '<span class="missing">尚未构建（out/ 为空）</span>'
        parts.append(f"""
    <article class="card done">
      <div class="num">{html.escape(l["num"])}</div>
      <h3 class="display">{html.escape(l["titleEs"])}</h3>
      <div class="zh">{html.escape(l["titleZh"])}</div>
      <div class="tags">{tag_html}</div>
      <p class="obj">{html.escape(l["obj"])}</p>
      <div class="actions">{actions}</div>
    </article>""")

    if not lessons:
        parts.append('<p class="obj">还没有已完成的课。</p>')
    parts.append("\n  </div>")

    if pending:
        items = "".join(
            f'<li><b>{html.escape(n)}</b> {html.escape(t)}</li>' for n, t in pending
        )
        parts.append(f"""
  <details class="todo-list">
    <summary>还有 {len(pending)} 本待做 —— 点开看清单</summary>
    <ol>{items}</ol>
  </details>""")

    parts.append("""
</main>
<footer>
  每课的课件与练习册都是单文件 HTML，图片与配音全部内嵌。用 iPad 的 Safari 或文件 App 打开即可，不需要联网。
</footer>
</body>
</html>
""")

    out = root / "index.html"
    out.write_text("".join(parts), encoding="utf-8")
    print(f"[index] {out}  {out.stat().st_size/1024:.1f} KB")
    print(f"[index] 已完成 {len(lessons)} 课 · 待做 {len(pending)} 本 · 共 {total_pages} 页")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
