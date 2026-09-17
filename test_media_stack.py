import os
import json
import traceback
from pathlib import Path

from media_router import MediaRouter

OUT = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs"))
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = []


def record(kind, result):
    item = {
        "kind": kind,
        "ok": bool(result.ok),
        "provider": result.provider,
        "output_path": result.output_path,
        "skipped": bool(result.skipped),
        "error": result.error,
    }
    RESULTS.append(item)

    status = "PASS" if result.ok else ("SKIP" if result.skipped else "FAIL")
    print(f"[{status}] {kind}: provider={result.provider}")
    if result.output_path:
        print(f"       output={result.output_path}")
    if result.error:
        print(f"       error={result.error}")


def main():
    router = MediaRouter()

    print("=== ARIA MEDIA STACK TEST ===")
    print("This test calls each configured provider chain once.")
    print("Secrets are never printed.\n")

    # Image
    record(
        "image",
        router.generate_image(
            prompt="A clean professional abstract illustration for a Persian psychology education Instagram post"
        ),
    )

    # Video
    record(
        "video",
        router.generate_video(
            prompt="A short cinematic abstract scene about personal growth, calm lighting, vertical social-media style"
        ),
    )

    # TTS
    record(
        "tts",
        router.generate_tts(
            text="این یک تست صدای آریا برای بررسی اتصال سرویس تولید صوت است."
        ),
    )

    # Music
    record(
        "music",
        router.generate_music(
            prompt="Calm minimal instrumental background music for an educational social media video"
        ),
    )

    result_path = OUT / "media-stack-test-results.json"
    result_path.write_text(
        json.dumps(
            {
                "test": "aria-media-stack-v1",
                "results": RESULTS,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nResults saved to: {result_path}")

    failures = [x for x in RESULTS if not x["ok"] and not x["skipped"]]
    passes = [x for x in RESULTS if x["ok"]]
    skips = [x for x in RESULTS if x["skipped"]]

    print("\n=== SUMMARY ===")
    print(f"PASS: {len(passes)}")
    print(f"SKIP: {len(skips)}")
    print(f"FAIL: {len(failures)}")

    # A skip means a provider was not configured/implemented, but the router
    # itself behaved correctly. Fail only on real provider exceptions.
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
