#!/usr/bin/env python3
"""
Turn a scanned Spanish picture-book PDF into web-ready page images.

Most Spanish graded readers floating around are page-image PDFs with **no text
layer**: every page is one big scan, and resellers often stamp a promo
watermark across the top of each spread. This script handles the whole
mechanical part so the authoring step is pure content work:

  1. render every page at 2x  (PyMuPDF)
  2. blank out the watermark band by copying a clean row up over it
  3. crop the page margins to a per-layout box
  4. resize to a fixed width and write progressive JPEGs
  5. optionally emit a "caption strip" contact sheet — one band per page,
     stacked — so you can transcribe all the Spanish lines in a single look
     instead of opening ten files

Probe mode (--print-bounds) reports the ink bounding box of every page, which
is how you find the crop boxes in the first place.

Examples
--------
# 1. find the boxes
python3 prep_pages.py book.pdf build/pages --print-bounds

# 2. story pages share one box; the cover and the word-list page differ
python3 prep_pages.py book.pdf build/pages \
    --erase-band 196,252 \
    --box 214,196,1466,978 \
    --page-box 1=248,248,1422,1016 \
    --page-box 2=320,205,1110,548 \
    --captions

The box coordinates are in the *rendered* pixel space (zoom x PDF points),
so always run --print-bounds first and copy the numbers it reports.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

INK = 120  # grey level below which a pixel counts as real ink (watermarks are lighter)


def parse_box(text: str) -> tuple[int, int, int, int]:
    parts = [int(float(x)) for x in text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected left,top,right,bottom")
    return tuple(parts)  # type: ignore[return-value]


def parse_pair(text: str) -> tuple[int, int]:
    parts = [int(float(x)) for x in text.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("expected top,bottom")
    return tuple(parts)  # type: ignore[return-value]


def render(pdf: Path, raw_dir: Path, zoom: float) -> list[Path]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    out = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        p = raw_dir / f"p{i:02d}.png"
        pix.save(str(p))
        out.append(p)
    n = doc.page_count
    doc.close()
    print(f"[prep] rendered {n} page(s) at zoom {zoom} -> {raw_dir}")
    return out


def bounds(img: np.ndarray) -> tuple[int, int, int, int] | None:
    """Ink bounding box (ignores light-grey watermarks)."""
    dark = img < INK
    rows = np.where(dark.sum(axis=1) > 3)[0]
    cols = np.where(dark.sum(axis=0) > 3)[0]
    if not len(rows) or not len(cols):
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("out_dir", help="where the web-ready JPEGs go")
    ap.add_argument("--raw-dir", default=None, help="keep the 2x renders here")
    ap.add_argument("--zoom", type=float, default=2.0)
    ap.add_argument("--erase-band", type=parse_pair, default=None,
                    help="top,bottom — blank this horizontal band using the row below it")
    ap.add_argument("--box", type=parse_box, default=None,
                    help="left,top,right,bottom crop for pages without a specific box")
    ap.add_argument("--page-box", action="append", default=[], metavar="N=L,T,R,B",
                    help="crop box for one specific page (1-based, repeatable)")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--captions", action="store_true",
                    help="write _captions.png: the caption band of every page, stacked")
    ap.add_argument("--caption-band", type=parse_box, default=parse_box("200,900,1480,968"))
    ap.add_argument("--print-bounds", action="store_true",
                    help="report the ink bounding box per page and exit")
    args = ap.parse_args()

    pdf = Path(args.pdf).expanduser().resolve()
    if not pdf.exists():
        print(f"error: not found: {pdf}", file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir).expanduser().resolve()
    raw_dir = Path(args.raw_dir).expanduser().resolve() if args.raw_dir else out_dir.parent / "raw"

    raws = render(pdf, raw_dir, args.zoom)

    if args.print_bounds:
        print(f"\n{'page':<8} {'left':>6} {'top':>6} {'right':>6} {'bottom':>6}")
        for p in raws:
            g = np.array(Image.open(p).convert("L"))
            b = bounds(g)
            print(f"{p.stem:<8} {b[0]:>6} {b[1]:>6} {b[2]:>6} {b[3]:>6}" if b else f"{p.stem:<8}  (blank)")
        print("\nUse these numbers for --box / --page-box. Remember the watermark band:")
        print("run with a low threshold to see where the light-grey stamp sits.")
        return 0

    per_page = {}
    for spec in args.page_box:
        k, _, v = spec.partition("=")
        per_page[int(k)] = parse_box(v)

    out_dir.mkdir(parents=True, exist_ok=True)
    strips = []
    for i, p in enumerate(raws, start=1):
        arr = np.array(Image.open(p).convert("RGB"))
        if args.erase_band:
            top, bot = args.erase_band
            if 0 <= top < bot < arr.shape[0] - 1:
                arr[top:bot + 1, :] = arr[bot + 1, :]   # copy a clean row up over the band
        box = per_page.get(i, args.box)
        pil = Image.fromarray(arr)
        if box:
            pil = pil.crop(box)
        w, h = pil.size
        if args.width and w != args.width:
            pil = pil.resize((args.width, round(h * args.width / w)), Image.LANCZOS)
        dst = out_dir / f"p{i:02d}.jpg"
        pil.convert("RGB").save(dst, "JPEG", quality=args.quality, optimize=True, progressive=True)
        print(f"  p{i:02d} -> {dst.name}  {pil.size}  {os.path.getsize(dst)//1024:>4} KB")
        if args.captions:
            strips.append(Image.fromarray(arr).crop(args.caption_band))

    if strips:
        l, t, r, b = args.caption_band
        band_h = b - t
        sheet = Image.new("RGB", (r - l, band_h * len(strips)), "white")
        for i, s in enumerate(strips):
            sheet.paste(s, (0, i * band_h))
        cap = raw_dir / "_captions.png"
        sheet.save(cap)
        print(f"\n[prep] caption sheet -> {cap}  ({sheet.size})")
        print("[prep] transcribe every line from this one image, then verify against the pages")

    total = sum(os.path.getsize(f) for f in out_dir.glob("*.jpg"))
    print(f"[prep] {len(raws)} page(s), {total//1024} KB total -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
