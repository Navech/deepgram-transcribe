"""Transcribe audio with Deepgram (pre-recorded / batch API).

Standalone module — no external project dependencies beyond `deepgram-sdk`.
Optional: `yt-dlp` on PATH enables transcribing URLs (Instagram reels, YouTube,
TikTok, X/Twitter videos, etc.) — the audio is downloaded to a temp file first.

    pip install deepgram-sdk
    brew install yt-dlp           # only needed for URL inputs
    export DEEPGRAM_API_KEY=...   # or put it in a local .env

    # as a CLI — files or URLs (auto-detected)
    python deepgram_transcribe.py audio.m4a
    python deepgram_transcribe.py *.mp3 --language en --diarize --out md
    python deepgram_transcribe.py "https://www.instagram.com/reel/..."
    python deepgram_transcribe.py "https://youtu.be/..." --language auto --out -

    # as a library
    from deepgram_transcribe import transcribe
    result = transcribe("audio.m4a")        # {"text", "confidence", "language"}
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

API_KEY_ENV = "DEEPGRAM_API_KEY"
DEFAULT_MODEL = "nova-3"
DEFAULT_LANGUAGE = "multi"  # nova-3 multilingüe; mejor que "es" para español. Override con --language es|en|auto
DEFAULT_TIMEOUT = 600       # segundos a esperar por la API (archivos grandes)
DEFAULT_RETRIES = 2         # reintentos nativos del SDK ante fallos reintentables


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def transcribe(
    audio_path: str | Path,
    *,
    model: str = DEFAULT_MODEL,
    language: str | None = DEFAULT_LANGUAGE,
    smart_format: bool = True,
    diarize: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_RETRIES,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Transcribe a local audio file and return {text, confidence, language}.

    `language=None` lets Deepgram auto-detect the language.
    `timeout`/`max_retries` tune the SDK request (raise `timeout` for large files).
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    api_key = api_key or _load_api_key()
    if not api_key:
        raise RuntimeError(
            f"Missing Deepgram API key. Set {API_KEY_ENV} in your environment or a local .env file."
        )

    client = _build_client(api_key)

    kwargs: dict[str, Any] = {
        "request": audio_path.read_bytes(),
        "model": model,
        "smart_format": smart_format,
        # request_options is a RequestOptions TypedDict; the SDK handles retries/timeout natively.
        "request_options": {"timeout_in_seconds": timeout, "max_retries": max_retries},
    }
    if language:
        kwargs["language"] = language
    if diarize:
        kwargs["diarize"] = True

    try:
        response = client.listen.v1.media.transcribe_file(**kwargs)
    except Exception as exc:  # noqa: BLE001 - surface a clean message
        raise RuntimeError(
            f"Deepgram transcription failed (model '{model}'). "
            "Check the API key is valid, you have remaining credit, and the file is a supported audio format. "
            f"Original error: {str(exc).strip() or type(exc).__name__}"
        ) from exc

    return _parse_response(response, fallback_language=language)


def _build_client(api_key: str):
    try:
        from deepgram import DeepgramClient
    except ImportError as exc:
        raise RuntimeError(
            "The deepgram-sdk package is not installed. Install it with: pip install deepgram-sdk"
        ) from exc
    return DeepgramClient(api_key=api_key)


def _parse_response(response: Any, *, fallback_language: str | None) -> dict[str, Any]:
    """Pull transcript/confidence/language out of the nested response defensively."""
    try:
        channel = response.results.channels[0]
        alternative = channel.alternatives[0]
        text = str(getattr(alternative, "transcript", "") or "").strip()
        confidence = getattr(alternative, "confidence", None)
        detected = getattr(channel, "detected_language", None)
    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Deepgram returned an unexpected response structure; could not extract a transcript. "
            f"Original error: {str(exc).strip() or type(exc).__name__}"
        ) from exc
    if not text:
        raise RuntimeError("Deepgram produced an empty transcript.")
    return {"text": text, "confidence": confidence, "language": detected or fallback_language or "und"}


def _load_api_key() -> str:
    """Return the API key from the environment, loading a sibling/CWD .env if needed."""
    key = os.environ.get(API_KEY_ENV, "").strip()
    if key:
        return key
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parent / ".env"):
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(f"{API_KEY_ENV}=") and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


# --------------------------------------------------------------------------- #
# URL support (yt-dlp)
# --------------------------------------------------------------------------- #
def _is_url(arg: str) -> bool:
    return arg.startswith("http://") or arg.startswith("https://")


def _download_audio(url: str, dest_dir: Path) -> tuple[Path, str]:
    """Download audio from a URL with yt-dlp. Returns (audio_path, stem-for-output).

    Uses `-f bestaudio/best` to grab the source's native audio container (m4a,
    webm, mp4, …) without conversion — Deepgram accepts all of these directly,
    so we avoid the ffmpeg dependency entirely for the typical case.
    """
    if not shutil.which("yt-dlp"):
        raise RuntimeError(
            "yt-dlp not found. Install with: brew install yt-dlp  (or: pipx install yt-dlp)"
        )
    out_template = str(dest_dir / "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestaudio/best",       # native audio, no re-encode → no ffmpeg needed
        "--no-playlist",
        "--quiet", "--no-warnings",
        "-o", out_template,
        url,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        lowered = stderr.lower()
        if "ffmpeg" in lowered or "ffprobe" in lowered:
            raise RuntimeError(
                "yt-dlp needs ffmpeg for this specific URL (it has separate audio+video streams "
                "that must be merged). Install it with: brew install ffmpeg  "
                "(Linux: apt install ffmpeg / pacman -S ffmpeg).\n"
                f"yt-dlp stderr: {stderr[:600]}"
            ) from exc
        raise RuntimeError(
            "yt-dlp failed to download the URL. The reel/video may be private, age-gated, or removed.\n"
            f"yt-dlp stderr: {stderr[:600]}"
        ) from exc
    files = [p for p in dest_dir.iterdir() if p.is_file()]
    if not files:
        raise RuntimeError("yt-dlp finished but produced no audio file — unexpected.")
    audio = files[0]
    return audio, audio.stem


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _render_markdown(name: str, source: str, result: dict[str, Any]) -> str:
    conf = result["confidence"]
    conf_str = f"{conf:.2f}" if isinstance(conf, (int, float)) else "n/a"
    return (
        f"# {name}\n\n"
        f"- **Fuente:** {source}\n"
        f"- **Modelo:** Deepgram\n"
        f"- **Idioma:** {result['language']}\n"
        f"- **Confidence:** {conf_str}\n\n"
        f"---\n\n{result['text']}\n"
    )


def _process_one(
    arg: str,
    *,
    model: str,
    language: str | None,
    smart_format: bool,
    diarize: bool,
    timeout: int,
    max_retries: int,
    out: str,
) -> int:
    """Process a single arg (file path or URL). Returns 0 on success, 1 on failure."""
    label = arg
    try:
        if _is_url(arg):
            with tempfile.TemporaryDirectory(prefix="dg_") as tmp:
                tmp_dir = Path(tmp)
                audio_path, stem = _download_audio(arg, tmp_dir)
                label = audio_path.name
                result = transcribe(
                    audio_path, model=model, language=language, smart_format=smart_format,
                    diarize=diarize, timeout=timeout, max_retries=max_retries,
                )
                source = arg
                # For URLs we write the output into the CWD (the temp dir is wiped).
                out_base = Path.cwd() / stem
        else:
            path = Path(arg)
            result = transcribe(
                path, model=model, language=language, smart_format=smart_format,
                diarize=diarize, timeout=timeout, max_retries=max_retries,
            )
            source = path.name
            out_base = path.with_suffix("")
            label = path.name
    except Exception as exc:  # noqa: BLE001
        print(f"✗ {label}: {exc}", file=sys.stderr)
        return 1

    conf = result["confidence"]
    conf_str = f"{conf:.2f}" if isinstance(conf, (int, float)) else "n/a"
    if out == "-":
        print(f"\n=== {source} ({result['language']}, confidence {conf_str}) ===")
        print(result["text"])
    else:
        out_path = out_base.with_suffix(f".{out}")
        content = _render_markdown(out_base.name, source, result) if out == "md" else result["text"] + "\n"
        out_path.write_text(content, encoding="utf-8")
        print(f"✓ {source} → {out_path.name}  ({result['language']}, confidence {conf_str})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Deepgram. Accepts file paths or URLs (yt-dlp)."
    )
    parser.add_argument("audio", nargs="+", help="Audio file(s) or video URL(s) (IG/YouTube/TikTok/X).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Deepgram model (default: {DEFAULT_MODEL}).")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language code (e.g. es, en), 'multi' for nova-3 multilingual, or 'auto' to detect "
        f"(default: {DEFAULT_LANGUAGE}).",
    )
    parser.add_argument("--no-smart-format", action="store_true", help="Disable punctuation/formatting.")
    parser.add_argument("--diarize", action="store_true", help="Label speakers (Speaker 0, 1, ...).")
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT,
        help=f"Seconds to wait for the API; raise for large files (default: {DEFAULT_TIMEOUT}).",
    )
    parser.add_argument(
        "--retries", type=int, default=DEFAULT_RETRIES,
        help=f"Max SDK retries on retryable failures (default: {DEFAULT_RETRIES}).",
    )
    parser.add_argument(
        "--out",
        choices=["txt", "md", "-"],
        default="txt",
        help="Save next to each audio as .txt or .md, or '-' to only print (default: txt).",
    )
    args = parser.parse_args(argv)
    language = None if args.language.lower() == "auto" else args.language

    exit_code = 0
    for raw in args.audio:
        exit_code |= _process_one(
            raw,
            model=args.model,
            language=language,
            smart_format=not args.no_smart_format,
            diarize=args.diarize,
            timeout=args.timeout,
            max_retries=args.retries,
            out=args.out,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
