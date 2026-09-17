from __future__ import annotations

import json
from pathlib import Path

from media_router import MediaRouter


OUT = Path("outputs/media-test")
OUT.mkdir(parents=True, exist_ok=True)

router = MediaRouter()

TESTS = {
    "image": {
        "prompt": (
            "A polished professional social media visual for an AI "
            "freelancer brand, modern studio, subtle technology "
            "aesthetic, no text, 16:9"
        ),
    },
    "video": {
        "prompt": (
            "A short cinematic motion graphic showing an AI freelancer "
            "workflow from brief to delivery, modern professional style"
        ),
        "duration": 5,
    },
    "tts": {
        "text": (
            "سلام. این یک تست واقعی از زنجیره تولید صدای آریا است."
        ),
    },
    "music": {
        "prompt": (
            "cinematic electronic background music for a professional "
            "AI freelancer portfolio"
        ),
        "duration": 8,
        "instrumental": True,
    },
}


def serialize(result):
    return {
        "ok": bool(result.ok),
        "provider": result.provider,
        "output": result.output_path,
        "output_url": getattr(result, "output_url", None),
        "error": result.error,
        "skipped": bool(result.skipped),
        "reason": getattr(result, "reason", None),
    }


results = {
    "provider_stats_before": router.provider_stats(),
    "tests": {},
}

for kind, kwargs in TESTS.items():
    print(f"[MediaStackTest] {kind}: starting")
    try:
        if kind == "tts":
            result = router.generate_tts(**kwargs)
        elif kind == "music":
            result = router.generate_music(**kwargs)
        elif kind == "video":
            result = router.generate_video(**kwargs)
        else:
            result = router.generate_image(**kwargs)

        results["tests"][kind] = serialize(result)
        print(
            f"[MediaStackTest] {kind}: "
            f"{'SUCCESS' if result.ok else 'FAILED'} "
            f"provider={result.provider}"
        )
    except Exception as exc:
        results["tests"][kind] = {
            "ok": False,
            "provider": "none",
            "output": None,
            "output_url": None,
            "error": f"{type(exc).__name__}: {exc}",
            "skipped": True,
            "reason": "unhandled exception",
        }
        print(f"[MediaStackTest] {kind}: ERROR {exc}")

results["provider_stats_after"] = router.provider_stats()
results["successful_count"] = sum(
    1 for item in results["tests"].values() if item.get("ok")
)
results["total_count"] = len(results["tests"])
results["all_succeeded"] = (
    results["successful_count"] == results["total_count"]
)

path = OUT / "media-stack-test.json"
path.write_text(
    json.dumps(results, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print(
    f"[MediaStackTest] finished: "
    f"{results['successful_count']}/{results['total_count']}"
)
print(f"[MediaStackTest] report -> {path}")
