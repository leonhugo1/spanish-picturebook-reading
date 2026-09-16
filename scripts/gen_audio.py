#!/usr/bin/env python3
"""
Generate the narration for a Spanish picture-book lesson with edge-tts.

Every speaker button in the lesson plays a pre-recorded clip embedded in the
HTML as base64 — the browser's built-in speech synthesis is never used, because
system voices sound robotic and vary wildly between devices.

    python3 scripts/gen_audio.py <content.json> <out_dir>
    python3 scripts/gen_audio.py --incremental <content.json> <out_dir>

**Two voices, two jobs.** Everything a child has to *read* is Spanish and is
spoken by a Spanish voice. Everything a child has to *understand* is Chinese and
is spoken by a Chinese voice — that is the intensive handout (per-sentence
translation and grammar, deep vocabulary, cultural notes). So the rule "only
Spanish reaches the speaker" applies to the book; the explanation track is a
second, deliberately Chinese voice.

`--incremental` keeps clips whose text has not changed (compared per segment by
a content hash) and only re-records what is new or edited. Changing an
illustration, a Chinese gloss or a grammar note re-records that step's Chinese
track but leaves the Spanish narration alone.

Output: <out_dir>/audio.json
    { voice, voices, mimes, count, segments: {segId: base64}, hashes: {segId: hash} }
    `mimes` only lists segments that are NOT mp3 (see the codec note below).

Spanish voices (set EDGE_TTS_VOICE to override):
    es-ES-ElviraNeural   Castilian, female   (default)
    es-ES-AlvaroNeural   Castilian, male
    es-MX-DaliaNeural    Latin American, female
    es-MX-JorgeNeural    Latin American, male
    es-AR-ElenaNeural    Rioplatense, female
    es-US-PalomaNeural   US Spanish, female

Chinese voice (set EDGE_TTS_CN_VOICE to override):
    zh-CN-XiaoxiaoNeural   (default)   zh-CN-YunxiNeural   zh-CN-XiaoyiNeural

Chinese clips can optionally be re-encoded to 24 kbps AAC where `afconvert`
exists (macOS ships it), which cuts their size by ~40%. It is **off by default**:
AAC means a second container the player has to handle, and only mp3 is verified
end to end. Set `EDGE_TTS_CN_CODEC=auto` (use a re-encoder when one is present)
or `=m4a` (insist on AAC) to opt in.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_VOICE = "es-ES-ElviraNeural"
DEFAULT_CN_VOICE = "zh-CN-XiaoxiaoNeural"

# Picture-book narration runs slower than article narration: the child is
# decoding a foreign language while following a highlighted line. The Chinese
# explanation track keeps a normal pace — it is the child's first language and
# is already dense, so slowing it down only makes it tiring.
RATE = "-12%"
CN_RATE = "+0%"
PITCH = "+0Hz"
VOLUME = "+0%"

# Chinese clips are long (a whole lesson holds ~10 minutes of explanation), so
# shrinking them is tempting. But every extra container is a way to lose sound on
# a device nobody tested, and the Chinese text can never be verified by playing it
# in one browser alone — so the safe mp3 edge-tts already produces is the default.
# "auto" → AAC when a re-encoder exists; "m4a" → insist on AAC.
CN_CODEC = os.environ.get("EDGE_TTS_CN_CODEC", "mp3")   # mp3 | auto | m4a
AAC_BITRATE = "24000"
MIME_MP3 = "audio/mpeg"
MIME_AAC = "audio/mp4"

# edge-tts ships MPEG-2 Layer 3 mono 24 kHz @ 48 kbps → 144 bytes per frame.
MP3_FRAME_BYTES = 144

# Marks that read well on screen but not aloud.
_SPEECH_FIXES = (
    (re.compile(r"[★☆·•▪◦]"), " "),
    (re.compile(r"\s*[—–]{1,2}\s*"), "，"),
    (re.compile(r"\s*=\s*"), " 就是 "),
    (re.compile(r"\s*→\s*"), "变成"),
    (re.compile(r"[「」『』]"), ""),
    (re.compile(r"\s*\|\s*"), "，"),
    (re.compile(r"\s+"), " "),
)


def find_reencoder() -> str | None:
    """A tool that turns edge-tts's mp3 into something smaller, if there is one."""
    if CN_CODEC == "mp3":
        return None
    explicit = os.environ.get("PICTUREBOOK_AFCONVERT")
    if explicit and Path(explicit).exists():
        return explicit
    return shutil.which("afconvert")


def cn_mime(reencoder: str | None) -> tuple[str, str | None]:
    """(mime_type, encoder) for the Chinese track."""
    if CN_CODEC in ("m4a", "aac") or (CN_CODEC == "auto" and reencoder):
        return MIME_AAC, reencoder or "afconvert"
    return MIME_MP3, None


def strip_html(s: str) -> str:
    """Speaker input is plain prose, never markup."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def clean_speech(s: str) -> str:
    """
    Speaker input for the Chinese track. The handout is written to be read on
    screen, so it carries marks that only work visually — ★ for a key point,
    "=" between a form and its gloss, em dashes for asides. A voice reads those
    literally, so normalise them into punctuation before speaking.
    """
    text = strip_html(s)
    for pat, rep in _SPEECH_FIXES:
        text = pat.sub(rep, text)
    return text.strip(" ，、,;")


def text_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def voice_for(lang: str, es_voice: str, cn_voice: str) -> str:
    return cn_voice if lang == "zh" else es_voice


def rate_for(lang: str) -> str:
    return CN_RATE if lang == "zh" else RATE


def collect_segments(content: dict) -> list[tuple[str, str, str]]:
    """
    Walk the content and return [(segId, plain text, lang)] in a stable order.
    The segIds here MUST match the data-segid attributes in the lesson template.
    `lang` picks the voice: "es" for anything the child reads aloud, "zh" for
    anything that explains it.
    """
    segs: list[tuple[str, str, str]] = []
    book = content.get("pictureBook") or {}

    # 1 · picture-book pages — whole page, then each sentence
    for i, page in enumerate(book.get("pages") or []):
        try:
            n = int(page.get("page", i + 1))
        except (TypeError, ValueError):
            n = i + 1
        whole = strip_html(page.get("textEs", ""))
        if whole:
            segs.append((f"book.page.{n}", whole, "es"))
        for j, s in enumerate(page.get("sentences") or []):
            line = strip_html(s.get("es", "") if isinstance(s, dict) else s)
            if line:
                segs.append((f"book.sent.{n}.{j + 1}", line, "es"))

    # 2 · word cards — the card reads the headword, the example line reads itself
    for i, w in enumerate(book.get("wordCards") or []):
        word = strip_html(w.get("es", ""))
        if word:
            segs.append((f"book.word.{i}", word, "es"))
        example = strip_html(w.get("exampleEs", ""))
        if example:
            segs.append((f"book.wordex.{i}", example, "es"))

    # 3 · pre-reading key words
    pre = content.get("preReading") or {}
    for i, kw in enumerate(pre.get("keyWords") or []):
        word = strip_html(kw.get("word", ""))
        if word:
            segs.append((f"pre.kw.{i}", word, "es"))

    # 4 · post-reading speaking prompts — narrate the Spanish sentence the child
    #     is asked to read aloud. The Chinese lead-in is a subtitle: never spoken.
    post = content.get("postReading") or {}
    speaking = post.get("speaking") or {}
    for i, p in enumerate(speaking.get("prompts") or []):
        line = strip_html(p.get("es") or "")
        if line:
            segs.append((f"post.speak.{i + 1}", line, "es"))

    # 5 · the intensive handout — spoken in Chinese, because it *is* Chinese.
    #     A child working through ten pages of grammar needs to be able to hear
    #     the explanation, not just read it.
    deep = (content.get("whileReading") or {}).get("intensiveReading") or {}
    for i, page in enumerate(book.get("pages") or []):
        try:
            n = int(page.get("page", i + 1))
        except (TypeError, ValueError):
            n = i + 1
        # The lesson template falls back to the whole page text when a page
        # carries no `sentences`, so the handout shows one block for it. Mirror
        # that here or the segIds would not line up.
        lines = page.get("sentences") or []
        if not lines and strip_html(page.get("textEs", "")):
            lines = [{"zh": page.get("textZh", "")}]
        for j, s in enumerate(lines):
            if not isinstance(s, dict):
                continue
            gloss = clean_speech(s.get("zh", ""))
            if gloss:
                segs.append((f"deep.zh.{n}.{j + 1}", gloss, "zh"))
            notes = [clean_speech(x) for x in (s.get("grammar") or [])]
            notes = [x for x in notes if x]
            if notes:
                segs.append((f"deep.gram.{n}.{j + 1}", "。".join(notes), "zh"))

    for k, v in enumerate(deep.get("deepVocabulary") or []):
        parts = [clean_speech(v.get("meaningZh", "")), clean_speech(v.get("note", ""))]
        body = "。".join(x for x in parts if x)
        if body:
            segs.append((f"deep.vocab.{k}", body, "zh"))

    for k, c in enumerate(deep.get("culturalNotes") or []):
        body = clean_speech(c.get("explanation", ""))
        if body:
            segs.append((f"deep.cult.{k}", body, "zh"))

    return segs


async def synth(voice: str, text: str, rate: str, dest: Path) -> None:
    import edge_tts  # imported lazily so --help works without the dependency

    await edge_tts.Communicate(
        text=text, voice=voice, rate=rate, pitch=PITCH, volume=VOLUME
    ).save(str(dest))


def reencode(src: Path, dest: Path, encoder: str) -> bool:
    """Shrink a Chinese clip. Returns False so the caller can keep the mp3."""
    try:
        proc = subprocess.run(
            [encoder, "-f", "m4af", "-d", "aac", "-b", AAC_BITRATE, str(src), str(dest)],
            capture_output=True, timeout=120, check=False,
        )
    except Exception as exc:  # noqa: BLE001 — any failure means "keep the mp3"
        print(f"    [warn] {encoder} failed: {exc}", file=sys.stderr)
        return False
    if proc.returncode != 0 or not dest.exists() or dest.stat().st_size < 200:
        print(f"    [warn] {encoder} exited {proc.returncode}; keeping mp3", file=sys.stderr)
        return False
    return True


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


async def synth_all(
    jobs: list[tuple[str, str, str]],
    es_voice: str,
    cn_voice: str,
    encoder: str | None,
    tmp: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    """Record every job. Returns ({segId: base64}, {segId: mime})."""
    done: dict[str, str] = {}
    mimes: dict[str, str] = {}
    cn_aac_ok = True   # once the encoder fails, stop asking it
    for seg_id, text, lang in jobs:
        voice = voice_for(lang, es_voice, cn_voice)
        dest = tmp / (seg_id.replace(".", "_") + ".mp3")
        try:
            await synth(voice, text, rate_for(lang), dest)
        except Exception as exc:  # noqa: BLE001 — report and keep going
            print(f"    [WARN] {seg_id}: {exc}", file=sys.stderr)
            continue
        if not dest.exists() or dest.stat().st_size < 200:
            print(f"    [WARN] {seg_id}: empty output", file=sys.stderr)
            continue

        mime = MIME_MP3
        source = dest
        if lang == "zh" and encoder and cn_aac_ok:
            small = dest.with_suffix(".m4a")
            if reencode(dest, small, encoder):
                source, mime = small, MIME_AAC
            else:
                cn_aac_ok = False

        raw = source.read_bytes()
        if mime == MIME_MP3:
            raw = trim_tail_padding(raw, MP3_FRAME_BYTES)
        if not raw:
            print(f"    [WARN] {seg_id}: nothing left after trim", file=sys.stderr)
            continue
        done[seg_id] = base64.b64encode(raw).decode("ascii")
        if mime != MIME_MP3:
            mimes[seg_id] = mime
        print(f"    [ok] {seg_id:<22} {lang}  {len(text):>4} chars → {len(raw)//1024:>3} KB")
    return done, mimes


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

    es_voice = os.environ.get("EDGE_TTS_VOICE", DEFAULT_VOICE)
    cn_voice = os.environ.get("EDGE_TTS_CN_VOICE", DEFAULT_CN_VOICE)
    reencoder = find_reencoder()
    cn_type, _ = cn_mime(reencoder)

    content = json.loads(content_path.read_text(encoding="utf-8"))
    segments = collect_segments(content)
    n_es = sum(1 for _, _, lang in segments if lang == "es")
    n_zh = len(segments) - n_es

    print(f"[audio] content:   {content_path.name}")
    print(f"[audio] spanish:   {es_voice}   rate {RATE}   ({n_es} clips)")
    print(f"[audio] chinese:   {cn_voice}   rate {CN_RATE}   ({n_zh} clips)")
    print(f"[audio] zh codec:  " + (
        f"aac {int(AAC_BITRATE) // 1000} kbps via {Path(reencoder).name}" if cn_type == MIME_AAC
        else "mp3 48 kbps (no re-encoder found)"))

    if not segments:
        audio_path.write_text(json.dumps(
            {"voice": es_voice, "voices": {"es": es_voice, "zh": cn_voice},
             "rates": {"es": RATE, "zh": CN_RATE}, "cnMime": cn_type,
             "rate": RATE, "pitch": PITCH, "volume": VOLUME,
             "count": 0, "segments": {}, "mimes": {}, "hashes": {}}, ensure_ascii=False),
            encoding="utf-8")
        print("[audio] nothing to record")
        return 0

    # ---- reuse what is still valid ----------------------------------------
    # A clip is stale when its text changed, when its voice changed, or when the
    # Chinese track's codec changed (the stored bytes would carry the wrong MIME).
    # The two languages invalidate independently: editing a grammar note should
    # never cost a re-record of the Spanish narration.
    reuse: dict[str, str] = {}
    reuse_mimes: dict[str, str] = {}
    if args.incremental and audio_path.exists():
        try:
            prev = json.loads(audio_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[audio] WARN unreadable {audio_path.name} ({exc}); doing a full run", file=sys.stderr)
            prev = {}
        prev_voices = prev.get("voices") or {}
        if not prev_voices and prev.get("voice"):
            prev_voices = {"es": prev["voice"]}   # pre-1.3 audio.json
        stale: set[str] = set()
        if prev_voices.get("es") and prev_voices["es"] != es_voice:
            stale.add("es")
        if prev_voices.get("zh") and prev_voices["zh"] != cn_voice:
            stale.add("zh")
        if prev.get("cnMime") and prev["cnMime"] != cn_type:
            stale.add("zh")
        for lang in sorted(stale):
            print(f"[audio] {lang} voice/codec changed → re-recording that track")
        prev_segs = prev.get("segments") or {}
        prev_hashes = prev.get("hashes") or {}
        prev_mimes = prev.get("mimes") or {}
        if not prev_hashes and prev_segs:
            print("[audio] NOTE existing audio.json predates hashes; matching by id only", file=sys.stderr)
        for seg_id, text, lang in segments:
            if lang in stale or seg_id not in prev_segs:
                continue
            if not prev_hashes or prev_hashes.get(seg_id) == text_hash(text):
                reuse[seg_id] = prev_segs[seg_id]
                if seg_id in prev_mimes:
                    reuse_mimes[seg_id] = prev_mimes[seg_id]
        if reuse:
            print(f"[audio] reusing:   {len(reuse)} clip(s) already up to date")

    todo = [s for s in segments if s[0] not in reuse]
    print(f"[audio] recording: {len(todo)} clip(s)")

    fresh: dict[str, str] = {}
    fresh_mimes: dict[str, str] = {}
    if todo:
        with tempfile.TemporaryDirectory(prefix="pb_tts_") as td:
            fresh, fresh_mimes = asyncio.run(
                synth_all(todo, es_voice, cn_voice, reencoder, Path(td)))

    # ---- rebuild in canonical order so stale clips never survive ----------
    final: dict[str, str] = {}
    mimes: dict[str, str] = {}
    hashes: dict[str, str] = {}
    for seg_id, text, _lang in segments:
        if seg_id in fresh:
            final[seg_id] = fresh[seg_id]
            if seg_id in fresh_mimes:
                mimes[seg_id] = fresh_mimes[seg_id]
        elif seg_id in reuse:
            final[seg_id] = reuse[seg_id]
            if seg_id in reuse_mimes:
                mimes[seg_id] = reuse_mimes[seg_id]
        hashes[seg_id] = text_hash(text)

    audio_path.write_text(json.dumps({
        "voice": es_voice, "voices": {"es": es_voice, "zh": cn_voice},
        "rates": {"es": RATE, "zh": CN_RATE}, "cnMime": cn_type,
        "rate": RATE, "pitch": PITCH, "volume": VOLUME,
        "planned": len(segments),
        "count": len(final), "segments": final, "mimes": mimes, "hashes": hashes,
    }, ensure_ascii=False), encoding="utf-8")

    def raw_kb(ids) -> float:
        return sum(len(final[i]) for i in ids) * 3 / 4 / 1024

    es_ids = [s for s, _, l in segments if l == "es" and s in final]
    zh_ids = [s for s, _, l in segments if l == "zh" and s in final]
    print(f"[audio] wrote {audio_path.name}: {len(final)}/{len(segments)} clips "
          f"— spanish ~{raw_kb(es_ids):.0f} KB, chinese ~{raw_kb(zh_ids):.0f} KB")
    if len(final) != len(segments):
        missing = [s for s, _, _ in segments if s not in final]
        print(f"[audio] WARN {len(missing)} clip(s) missing: {', '.join(missing[:6])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
