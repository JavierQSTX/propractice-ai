"""Compare /feedback_audio scores on full recordings vs audio-only copies.

The audio-only copies mimic what lcmx-module's sidecar recorder uploads:
Opus in WebM at 32 kbps (Chrome/Firefox/Edge) and AAC in MP4 at 64 kbps
(Safari). AAC at 32 kbps moved scores on set_1/1 and set_3, so it runs at 64.
Each file goes through the same ffmpeg → mp3 step and pipeline as production.

Run from ai_feedback/ (needs ffmpeg and .env):
    poetry run python -m scripts.compare_audio_only set_1 set_5
"""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env")

from ai_feedback.ai import get_feedback  # noqa: E402
from ai_feedback.models import ScriptDetails, SupportedLanguage  # noqa: E402
from ai_feedback.utils import convert_video_to_audio  # noqa: E402

DATA = Path("data")
ACCURACY_TOLERANCE = 10
CONFIDENCE_TOLERANCE = 10
AUDIO_ONLY_VARIANTS = {
    "opus32": ("webm", ["-c:a", "libopus", "-b:a", "32k"]),
    "aac64": ("m4a", ["-c:a", "aac", "-b:a", "64k"]),
}


def make_audio_only(src: Path, out_dir: Path, variant: str) -> Path:
    ext, codec_args = AUDIO_ONLY_VARIANTS[variant]
    dst = out_dir / f"{src.stem}-{variant}.{ext}"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vn", "-ac", "1", *codec_args, str(dst)],
        check=True,
    )
    return dst


async def score(media: Path, payload: dict) -> tuple[int, int]:
    mp3 = convert_video_to_audio(str(media))
    try:
        result = await get_feedback(
            audio_filename=mp3,
            script_details=ScriptDetails(
                question=payload.get("question", ""),
                keyElements=payload.get("keyElements", []),
                briefing=payload.get("briefing", ""),
            ),
            user_id="audio-only-compare",
            tags=["audio-only-compare"],
            language=SupportedLanguage.ENGLISH.value,
        )
    finally:
        Path(mp3).unlink(missing_ok=True)
    return result["accuracy"], result["confidence"]


async def main(sets: list[str]) -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        for set_name in sets:
            for video in sorted((DATA / "sets" / set_name).iterdir()):
                payload_path = DATA / "challenges" / f"payload_{video.stem}.json"
                if video.suffix not in (".webm", ".mkv") or not payload_path.exists():
                    continue
                payload = json.loads(payload_path.read_text())
                base_acc, base_conf = await score(video, payload)
                row = [f"{set_name}/{video.name}", f"full {base_acc}/{base_conf}"]
                for variant in AUDIO_ONLY_VARIANTS:
                    acc, conf = await score(make_audio_only(video, Path(tmp), variant), payload)
                    ok = (
                        abs(acc - base_acc) <= ACCURACY_TOLERANCE
                        and abs(conf - base_conf) <= CONFIDENCE_TOLERANCE
                        and (acc == 0) == (base_acc == 0)  # coherence gate agrees
                    )
                    failures += not ok
                    row.append(f"{variant} {acc}/{conf}{'' if ok else ' !!'}")
                print(" | ".join(row))
    print(f"{failures} variant(s) outside tolerance")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:] or ["set_1"])))
