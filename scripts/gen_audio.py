#!/usr/bin/env python3
"""
Generate the narration for a Spanish picture-book lesson with edge-tts.

Every speaker button in the lesson plays a pre-recorded clip embedded in the
HTML as base64 — the browser's built-in speech synthesis is never used, because
system voices sound robotic and vary wildly between devices.

    python3 scripts/gen_audio.py <content.json> <out_dir>
    python3 scripts/gen_audio.py --incremental <content.json> <out_dir>

`--incremental` keeps clips whose text has not changed (compared per segment by
a content hash) and only re-records what is new or edited. Changing an
illustration, a Chinese gloss or a grammar note therefore costs nothing —
only edits to the Spanish itself trigger a re-record.

Output: <out_dir>/audio.json
    { voice, rate, pitch, count, segments: {segId: base64 mp3}, hashes: {segId: hash} }

Voices (set EDGE_TTS_VOICE to override):
    es-ES-ElviraNeural   Castilian, female   (default)
    es-ES-AlvaroNeural   Castilian, male
    es-MX-DaliaNeural    Latin American, female
    es-MX-JorgeNeural    Latin American, male
    es-AR-ElenaNeural    Rioplatense, female
    es-US-PalomaNeural   US Spanish, female
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_VOICE = "es-ES-ElviraNeural"

# Picture-book narration runs slower than article narration: the child is
# decoding a foreign language while following a highlighted line.
RATE = "-12%"
PITCH = "+0Hz"
VOLUME = "+0%"

# edge-tts ships MPEG-2 Layer 3 mono 24 kHz @ 48 kbps → 144 bytes per frame.
MP3_FRAME_BYTES = 144


def strip_html(s: str) -> str:
    """Speaker input is plain prose, never markup."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def text_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def collect_segments(content: dict) -> list[tuple[str, str]]:
    """
    Walk the content and return [(segId, plain text)] in a stable order.
    The segIds here MUST match the data-segid attributes in the lesson template.
    """
    segs: list[tuple[str, str]] = []

    # 1 · picture-book pages — whole page, then each sentence
    book = content.get("pictureBook") or {}
    for i, page in enumerate(book.get("pages") or []):
        try:
            n = int(page.get("page", i + 1))
        except (TypeError, ValueError):
            n = i + 1
        whole = strip_html(page.get("textEs", ""))
        if whole:
            segs.append((f"book.page.{n}", whole))
        for j, s in enumerate(page.get("sentences") or []):
            line = strip_html(s.get("es", "") if isinstance(s, dict) else s)
            if line:
                segs.append((f"book.sent.{n}.{j + 1}", line))

    # 2 · word cards — the card reads the headword, the example line reads itself
    for i, w in enumerate(book.get("wordCards") or []):
        word = strip_html(w.get("es", ""))
        if word:
            segs.append((f"book.word.{i}", word))
        example = strip_html(w.get("exampleEs", ""))
        if example:
            segs.append((f"book.wordex.{i}", example))

    # 3 · pre-reading key words
    pre = content.get("preReading") or {}
    for i, kw in enumerate(pre.get("keyWords") or []):
        word = strip_html(kw.get("word", ""))
        if word:
            segs.append((f"pre.kw.{i}", word))

    # 4 · post-reading speaking prompts — narrate the Spanish sentence the child
    #     is asked to read aloud. The Chinese lead-in is a subtitle: never spoken.
    post = content.get("postReading") or {}
    speaking = post.get("speaking") or {}
    for i, p in enumerate(speaking.get("prompts") or []):
        line = strip_html(p.get("es") or "")
        if line:
            segs.append((f"post.speak.{i + 1}", line))

    return segs


async def synth(voice: str, text: str, dest: Path) -> None:
    import edge_tts  # imported lazily so --help works without the dependency

    await edge_tts.Communicate(
        text=text, voice=voice, rate=RATE, pitch=PITCH, volume=VOLUME
    ).save(str(dest))


def trim_tail_padding(raw: bytes, frame: int) -> bytes:
    """
    edge-tts sometimes pads the end of an mp3 with bytes that are not a whole
    frame. WebKit rejects such files at EOF (MediaError) and the line goes
    silent, so drop the partial tail. The dropped bytes are buffer garbage.
    """
    if len(raw) < frame * 2:
        return raw
    rem = len(raw) % frame
    if rem:
        print(f"    [trim] dropping {rem} non-frame trailing bytes")
        return raw[: len(raw) - rem]
    return raw


async def synth_all(voice: str, todo: list[tuple[str, str]], tmp: Path) -> dict[str, str]:
    done: dict[str, str] = {}
    for seg_id, text in todo:
        dest = tmp / (seg_id.replace(".", "_") + ".mp3")
        try:
            await synth(voice, text, dest)
        except Exception as exc:  # noqa: BLE001 — report and keep going
            print(f"    [WARN] {seg_id}: {exc}", file=sys.stderr)
            continue
        if not dest.exists() or dest.stat().st_size < 200:
            print(f"    [WARN] {seg_id}: empty output", file=sys.stderr)
            continue
        raw = trim_tail_padding(dest.read_bytes(), MP3_FRAME_BYTES)
        if not raw:
            print(f"    [WARN] {seg_id}: nothing left after trim", file=sys.stderr)
            continue
        done[seg_id] = base64.b64encode(raw).decode("ascii")
        print(f"    [ok] {seg_id:<22} {len(text):>4} chars → {len(raw)//1024:>3} KB")
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate lesson narration with edge-tts.")
    ap.add_argument("content", help="content.json produced for the lesson")
    ap.add_argument("out_dir", help="directory to write audio.json into")
    ap.add_argument("--incremental", action="store_true",
                    help="reuse clips whose text is unchanged")
    args = ap.parse_args()

    content_path = Path(args.content).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = out_dir / "audio.json"

    if not content_path.exists():
        print(f"error: no such file: {content_path}", file=sys.stderr)
        return 2

    voice = os.environ.get("EDGE_TTS_VOICE", DEFAULT_VOICE)
    content = json.loads(content_path.read_text(encoding="utf-8"))
    segments = collect_segments(content)

    print(f"[audio] content:   {content_path.name}")
    print(f"[audio] voice:     {voice}   rate {RATE}")
    print(f"[audio] segments:  {len(segments)}")

    if not segments:
        audio_path.write_text(json.dumps(
            {"voice": voice, "rate": RATE, "pitch": PITCH, "volume": VOLUME,
             "count": 0, "segments": {}, "hashes": {}}, ensure_ascii=False), encoding="utf-8")
        print("[audio] nothing to record")
        return 0

    # ---- reuse what is still valid ----------------------------------------
    reuse: dict[str, str] = {}
    if args.incremental and audio_path.exists():
        try:
            prev = json.loads(audio_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[audio] WARN unreadable {audio_path.name} ({exc}); doing a full run", file=sys.stderr)
            prev = {}
        if prev.get("voice") and prev["voice"] != voice:
            print(f"[audio] voice changed ({prev['voice']} → {voice}); re-recording everything")
        else:
            prev_segs = prev.get("segments") or {}
            prev_hashes = prev.get("hashes") or {}
            if not prev_hashes and prev_segs:
                print("[audio] NOTE existing audio.json predates hashes; matching by id only", file=sys.stderr)
            for seg_id, text in segments:
                if seg_id not in prev_segs:
                    continue
                if not prev_hashes or prev_hashes.get(seg_id) == text_hash(text):
                    reuse[seg_id] = prev_segs[seg_id]
            if reuse:
                print(f"[audio] reusing:   {len(reuse)} clip(s) already up to date")

    todo = [(s, t) for s, t in segments if s not in reuse]
    print(f"[audio] recording: {len(todo)} clip(s)")

    fresh: dict[str, str] = {}
    if todo:
        with tempfile.TemporaryDirectory(prefix="pb_tts_") as td:
            fresh = asyncio.run(synth_all(voice, todo, Path(td)))

    # ---- rebuild in canonical order so stale clips never survive ----------
    final: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for seg_id, text in segments:
        if seg_id in fresh:
            final[seg_id] = fresh[seg_id]
        elif seg_id in reuse:
            final[seg_id] = reuse[seg_id]
        hashes[seg_id] = text_hash(text)

    audio_path.write_text(json.dumps({
        "voice": voice, "rate": RATE, "pitch": PITCH, "volume": VOLUME,
        "count": len(final), "segments": final, "hashes": hashes,
    }, ensure_ascii=False), encoding="utf-8")

    size_kb = sum(len(v) for v in final.values()) * 3 / 4 / 1024
    print(f"[audio] wrote {audio_path.name}: {len(final)}/{len(segments)} clips, ~{size_kb:.0f} KB of mp3")
    if len(final) != len(segments):
        missing = [s for s, _ in segments if s not in final]
        print(f"[audio] WARN {len(missing)} clip(s) missing: {', '.join(missing[:6])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
