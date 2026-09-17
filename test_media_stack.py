import json
import os
from pathlib import Path

from media_router import MediaRouter


OUTPUT_DIR = Path(os.getenv("ARIA_OUTPUT_DIR", "outputs/media-test"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


router = MediaRouter()

results = []


def record(kind, result):
    item = {
        "kind": kind,
        "ok": result.ok,
        "provider": result.provider,
        "output_path": result.output_path,
        "error": result.error,
        "skipped": result.skipped,
    }
    results.append(item)

    status = "OK" if result.ok else "FAILED"
    print(f"[{status}] {kind}")
    print(f"  provider: {result.provider}")

    if result.output_path:
        print(f"  output: {result.output_path}")

    if result.error:
        print(f"  error: {result.error}")


# 1. Image
record(
    "image",
    router.generate_image(
        "A professional cinematic workspace for an AI freelancer brand, "
        "modern desk, laptop, soft lighting, realistic photography"
    ),
)

# 2. Video
record(
    "video",
    router.generate_video(
        "A cinematic 5 second shot of a modern creative workspace, "
        "subtle camera movement, professional atmosphere"
    ),
)

# 3. TTS
record(
    "tts",
    router.generate_tts(
        "Hello from Aria Freelancer. This is a real text to speech test."
    ),
)

# 4. Music
record(
    "music",
    router.generate_music(
        "Short professional cinematic background music for a technology brand"
    ),
)


results_file = OUTPUT_DIR / "media-stack-test-results.json"

with results_file.open("w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)


print("\n=== MEDIA TEST SUMMARY ===")

for result in results:
    print(
        f'{result["kind"]}: '
        f'{"OK" if result["ok"] else "FAILED"} '
        f'({result["provider"]})'
    )

print(f"\nResults saved to: {results_file}")


# The test is successful only when every requested category
# actually produces a file.
if any(not r["ok"] for r in results):
    raise SystemExit(1)
