"""Mix the professional narration onto the briefing clips.

The words are the pro paragraphs in build.py (the same prose as voice-pro.md).
Takes already on disk live in assets/narration/ as one wav per paragraph.
Running this file joins those takes, starts each clip's speech at 0.8 seconds,
and remuxes the existing picture. It does not redraw a frame.

    python3 docs/explainer/narrate.py --synthesize   # call edge-tts, then mix
    python3 docs/explainer/narrate.py                # mix the wavs already saved

A synthesized take that would run past the end of a clip is sped slightly
with atempo so it finishes inside the clip. A short take keeps a silent tail.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

MEDIA = ROOT / "media"
NARRATION = ROOT / "assets" / "narration"
STAGING = Path("/tmp/ks-narrated")

VOICE = "en-US-ChristopherNeural"
RATE = "-10%"
HEAD = 0.8
PAUSE = 0.45
# When a take would run past the clip, speed it enough to leave this breath.
MIN_TAIL = 0.6
SAMPLE_RATE = 48000


def probe_duration(path: Path, stream: str = "a") -> float:
    selector = "a:0" if stream == "a" else "v:0"
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-select_streams", selector,
            "-show_entries", "stream=duration",
            "-of", "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def video_md5(path: Path) -> str:
    out = subprocess.check_output(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "md5", "-"],
        text=True,
    ).strip()
    return out


def run(cmd: list[str]) -> None:
    subprocess.check_call(cmd)


def wav_args(dest: Path) -> list[str]:
    return ["-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(dest)]


async def synthesize_paragraph(text: str, dest: Path) -> None:
    import edge_tts

    dest.parent.mkdir(parents=True, exist_ok=True)
    mp3 = dest.with_suffix(".mp3")
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text.strip(), VOICE, rate=RATE).save(str(mp3))
            last_error = None
            break
        except Exception as exc:  # network blips from the speech service
            last_error = exc
            await asyncio.sleep(2 ** attempt)
    if last_error is not None:
        raise last_error
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), *wav_args(dest)])
    mp3.unlink(missing_ok=True)


def paragraph_paths(section: dict) -> list[Path]:
    stem = Path(section["file"]).stem
    return [NARRATION / f"{stem}-p{i}.wav" for i in range(1, len(section["pro"]) + 1)]


async def synthesize_all() -> None:
    NARRATION.mkdir(parents=True, exist_ok=True)
    jobs = []
    for section in build.SECTIONS:
        for path, text in zip(paragraph_paths(section), section["pro"]):
            jobs.append(synthesize_paragraph(text, path))
    await asyncio.gather(*jobs)
    for section in build.SECTIONS:
        for path in paragraph_paths(section):
            print(f"wrote {path.relative_to(ROOT)} ({probe_duration(path):.2f}s)")


def join_paragraphs(paths: list[Path], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(paths[0]), *wav_args(dest)])
        return
    silence = dest.with_name("_pause.wav")
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
        "-t", f"{PAUSE:.3f}", *wav_args(silence),
    ])
    parts: list[Path] = []
    for i, path in enumerate(paths):
        if i:
            parts.append(silence)
        parts.append(path)
    listing = dest.with_suffix(".concat.txt")
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    try:
        run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            *wav_args(dest),
        ])
    finally:
        listing.unlink(missing_ok=True)
        silence.unlink(missing_ok=True)


def fit_speech(speech: Path, duration: float, dest: Path) -> float:
    """Place speech at 0.8s and pad to the clip. Return the atempo factor."""
    speech_dur = probe_duration(speech)
    budget = duration - HEAD
    tempo = 1.0
    src = speech
    if speech_dur > budget:
        tempo = speech_dur / (budget - MIN_TAIL)
        sped = dest.with_name(dest.stem + ".sped.wav")
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
            "-filter:a", f"atempo={tempo:.6f}",
            *wav_args(sped),
        ])
        src = sped
    delay_ms = int(round(HEAD * 1000))
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-filter:a",
        (
            f"aformat=sample_fmts=s16:sample_rates={SAMPLE_RATE}:channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms},"
            f"apad=whole_dur={duration:.6f},"
            f"atrim=0:{duration:.6f}"
        ),
        "-ar", str(SAMPLE_RATE), "-ac", "2", "-c:a", "pcm_s16le", str(dest),
    ])
    if src is not speech:
        src.unlink(missing_ok=True)
    return tempo


def remux(video: Path, audio: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", str(SAMPLE_RATE), "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        str(dest),
    ])


def concat(paths: list[Path], dest: Path) -> None:
    listing = dest.with_suffix(".concat.txt")
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in paths), encoding="utf-8")
    try:
        run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-c", "copy", "-movflags", "+faststart",
            str(dest),
        ])
    finally:
        listing.unlink(missing_ok=True)


def mix() -> Path:
    for section in build.SECTIONS:
        build.prepare(section)
    STAGING.mkdir(parents=True, exist_ok=True)
    staged: list[Path] = []
    print(f"{'clip':32} {'video':>8} {'speech':>8} {'tempo':>7} {'tail':>7}")
    for section in build.SECTIONS:
        src = MEDIA / section["file"]
        duration = probe_duration(src, stream="v")
        parts = paragraph_paths(section)
        missing = [p for p in parts if not p.exists()]
        if missing:
            raise SystemExit(f"missing narration {missing[0]}. Run with --synthesize.")
        speech = STAGING / f"{Path(section['file']).stem}.speech.wav"
        join_paragraphs(parts, speech)
        speech_dur = probe_duration(speech)
        bed = STAGING / f"{Path(section['file']).stem}.bed.wav"
        tempo = fit_speech(speech, duration, bed)
        out = STAGING / section["file"]
        before = video_md5(src)
        remux(src, bed, out)
        after = video_md5(out)
        out_v = probe_duration(out, stream="v")
        if before != after:
            raise SystemExit(f"video stream changed for {section['file']}")
        if abs(out_v - duration) > 0.05:
            raise SystemExit(f"duration changed for {section['file']}: {duration} -> {out_v}")
        fitted = speech_dur / tempo
        tail = duration - HEAD - fitted
        print(f"{section['file']:32} {duration:8.3f} {speech_dur:8.3f} {tempo:7.3f} {tail:7.2f}")
        staged.append(out)
        bed.unlink(missing_ok=True)
    assembly = STAGING / "assembly.mp4"
    concat(staged, assembly)
    print("assembly video", probe_duration(assembly, stream="v"))
    print("assembly format", subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(assembly)],
        text=True,
    ).strip())
    return assembly


def install() -> None:
    for section in build.SECTIONS:
        src = STAGING / section["file"]
        dest = MEDIA / section["file"]
        if not src.exists():
            raise SystemExit(f"missing staged clip {src}. Run the mix first.")
        dest.write_bytes(src.read_bytes())
        print("installed", dest)
    assembly = STAGING / "assembly.mp4"
    dest = MEDIA / "assembly.mp4"
    dest.write_bytes(assembly.read_bytes())
    print("installed", dest)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthesize", action="store_true", help="call edge-tts and replace the paragraph wavs")
    parser.add_argument("--install", action="store_true", help="copy the staged mix over docs/explainer/media")
    args = parser.parse_args()
    if args.synthesize:
        asyncio.run(synthesize_all())
    mix()
    if args.install:
        install()


if __name__ == "__main__":
    main()
