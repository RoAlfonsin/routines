#!/usr/bin/env python3
"""Bake the spoken narration for The Hour into MP3 clips.

The run screen speaks the current step. Instead of synthesising that live in the
browser — which sounds different on every phone and needs the device's TTS engine —
every phrase is generated once here and committed under audio/. The page then just
plays a file, with the device voice kept as the fallback for any phrase without a
clip (a move invented in the editor, say).

    # one-off setup (edge-tts is not part of the site's runtime)
    python3 -m venv .venv-audio && .venv-audio/bin/pip install edge-tts

    .venv-audio/bin/python make_audio.py            # regenerate everything
    .venv-audio/bin/python make_audio.py --check    # report, change nothing

What gets read:
  * the sun salutations   — the move name only (Rodri, 2026-10-02: reading a cue in
                            the middle of the flow breaks it),
  * everything else       — the move name followed by its cue, i.e. the description
                            as written in pool.json,
  * video blocks          — their label (no cue exists).

audio/manifest.json maps the exact spoken string to its file, so the page never has
to guess a filename. Regenerate after changing a move's name or cue text, or the
page silently falls back to the device voice for it.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
AUDIODIR = HERE / "audio"
MANIFEST = AUDIODIR / "manifest.json"

VOICE = "en-US-MichelleNeural"
RATE = "-10%"

POOL = json.loads((HERE / "pool.json").read_text(encoding="utf-8"))
R = json.loads((HERE / "routines.json").read_text(encoding="utf-8"))
BY_ID = {m["id"]: m for m in POOL["moves"]}


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "clip"


def spoken(move: dict, with_cue: bool) -> str:
    """The exact string the run screen speaks for one move."""
    name = move.get("name") or move["id"]
    cue = (move.get("cue") or "").strip()
    if with_cue and cue:
        return name + ". " + cue
    return name


def wanted() -> dict[str, str]:
    """{spoken text: filename stub} for every phrase the page can utter."""
    out: dict[str, str] = {}

    def add(text: str, stub: str):
        out.setdefault(text, stub)

    # the sun salutations: names only, so the flow is not interrupted by a cue
    for m in R.get("sun", {}).get("moves") or []:
        mv = BY_ID.get(m["ref"])
        if mv:
            add(spoken(mv, with_cue=False), slug(mv.get("name") or mv["id"]))

    # heads-up for anything referenced but missing from the pool
    missing = set()

    def walk(cfg, with_cue=True, tag=""):
        for m in (cfg or {}).get("moves") or []:
            mv = BY_ID.get(m["ref"])
            if not mv:
                missing.add(m["ref"])
                continue
            add(spoken(mv, with_cue), slug(mv.get("name") or mv["id"]) + ("--cue" if with_cue else ""))

    walk(R.get("warmup"), True, "warmup")
    walk(R.get("cooldown"), True, "cooldown")
    for d in R["days"]:
        walk(d.get("main"), True, d["id"])
        for ex in d.get("extra") or []:
            walk(ex, True, d["id"])

    if missing:
        print("referenced but not in pool.json: " + ", ".join(sorted(missing)), file=sys.stderr)

    # video blocks are announced by their label
    for key in ("settle",):
        blk = R.get(key) or {}
        if blk.get("video") and blk.get("title"):
            add(blk["title"] if len(blk["title"]) < 60 else blk.get("label", blk["title"]),
                slug(key))
    return out


def unique_files(phrases: dict[str, str]) -> dict[str, str]:
    """Two phrases can share a stub (e.g. a move used with and without its cue, or
    the same name in two sections) — give every phrase its own file."""
    seen: dict[str, int] = {}
    out: dict[str, str] = {}
    for text, stub in phrases.items():
        seen[stub] = seen.get(stub, 0) + 1
        out[text] = stub + (".mp3" if seen[stub] == 1 else f"-{seen[stub]}.mp3")
    return out


def synth(text: str, dest: pathlib.Path, exe: str) -> bool:
    cmd = [exe, "--voice", VOICE, f"--rate={RATE}", "--text", text,
           "--write-media", str(dest)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
        print("  FAILED:", text[:60], (p.stderr or "").strip()[:200], file=sys.stderr)
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report what would change")
    ap.add_argument("--exe", default=str(HERE / ".venv-audio/bin/edge-tts"),
                    help="path to the edge-tts executable")
    args = ap.parse_args()

    phrases = unique_files(wanted())
    AUDIODIR.mkdir(exist_ok=True)
    old = {}
    if MANIFEST.exists():
        old = json.loads(MANIFEST.read_text(encoding="utf-8")).get("clips", {})

    todo = [t for t, f in phrases.items() if old.get(t) != f or not (AUDIODIR / f).exists()]
    print(f"{len(phrases)} phrases, {len(todo)} to generate "
          f"(voice {VOICE} at {RATE})")
    if args.check:
        for t in todo:
            print("  would make:", t[:70])
        return 0

    made, failed = 0, 0
    for i, text in enumerate(sorted(todo), 1):
        dest = AUDIODIR / phrases[text]
        if synth(text, dest, args.exe):
            made += 1
            print(f"  [{i}/{len(todo)}] {phrases[text]}  ({dest.stat().st_size // 1024} KB)")
        else:
            failed += 1

    clips = {t: f for t, f in phrases.items() if (AUDIODIR / f).exists()}
    MANIFEST.write_text(json.dumps({
        "voice": VOICE,
        "rate": RATE,
        "generated": datetime.datetime.now(datetime.timezone.utc)
                       .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "note": ("Baked narration. Key = the exact string the run screen speaks; "
                 "value = the file in this directory. Anything not listed here falls "
                 "back to the device's own voice."),
        "clips": clips,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    total = sum((AUDIODIR / f).stat().st_size for f in clips.values())
    # drop clips that are no longer referenced
    for f in AUDIODIR.glob("*.mp3"):
        if f.name not in clips.values():
            f.unlink()
            print("  removed stale", f.name)
    print(f"wrote {MANIFEST.name}: {len(clips)} clips, {total / 1024:.0f} KB"
          + (f", {failed} failed" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
