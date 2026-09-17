# Aria Media Stack Test

این تست هر چهار مسیر را یک‌بار اجرا می‌کند:

1. Image
2. Video
3. TTS
4. Music

فایل `test_media_stack.py` را در ریشه repo بگذار.

## اجرای دستی

```bash
python test_media_stack.py
```

## اجرای GitHub Actions

فایل `.github/workflows/media-test.yml` را در مسیر گفته‌شده قرار بده، سپس از:

Actions → Aria Media Stack Test → Run workflow

اجرا کن.

## Secrets / Variables

Secrets:
- `HF_TOKEN_1` (یا `HF_TOKEN`)
- `REPLICATE_API_TOKEN`
- `FAL_KEY`
- `ELEVENLABS_API_KEY`
- `GEMINI_API_KEY`

Repository Variables:
- `REPLICATE_IMAGE_MODEL`
- `REPLICATE_VIDEO_MODEL`
- `FAL_VIDEO_MODEL`
- `ELEVENLABS_VOICE_ID`

نکته: providerهایی که هنوز endpoint واقعی‌شان در فایل provider پیاده‌سازی نشده باشد، در گزارش `SKIP` می‌شوند؛ این به معنی سالم بودن API نیست، بلکه یعنی آن provider هنوز فعال نشده است.
