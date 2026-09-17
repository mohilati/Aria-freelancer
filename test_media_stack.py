import json
import os
from pathlib import Path

from media_router import MediaRouter

OUT = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test"))
OUT.mkdir(parents=True, exist_ok=True)


def main():
    router = MediaRouter()
    results = []

    tests = [
        ("image", lambda: router.generate_image(
            "A professional clean abstract illustration for a Persian educational Instagram post"
        )),
        ("video", lambda: router.generate_video(
            "A short cinematic vertical social-media scene about personal growth, calm lighting"
        )),
        ("tts", lambda: router.generate_tts(
            "این یک تست واقعی صدای آریا برای بررسی اتصال سرویس تولید صوت است."
        )),
        ("music", lambda: router.generate_music(
            "Create a short calm instrumental background track for an educational social media video. Instrumental only, no vocals."
        )),
    ]

    for kind, fn in tests:
        try:
            result = fn()
            item = {
                "kind": kind,
                "ok": result.ok,
                "provider": result.provider,
                "output_path": result.output_path,
                "skipped": result.skipped,
                "error": result.error,
            }
            print(json.dumps(item, ensure_ascii=False))
            results.append(item)
        except Exception as exc:
            item = {
                "kind": kind,
                "ok": False,
                "provider": "exception",
                "output_path": None,
                "skipped": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(json.dumps(item, ensure_ascii=False))
            results.append(item)

    (OUT / "media-stack-test-results.json").write_text(
        json.dumps({"test": "aria-media-stack-v2", "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Fail only when every provider in a category is genuinely exhausted.
    # A media test is successful only when every requested category
# actually produces a file.
if any(not r["ok"] for r in results):
    raise SystemExit(1)


if __name__ == "__main__":
    main()
