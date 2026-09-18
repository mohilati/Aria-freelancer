# Aria Clinic Media Patch v3

این فایل policy را کنار `agent.py` نگه دار.

## تغییرات اجباری

### Persian narration
- برای فارسی از `persian_tts.py` استفاده کن.
- پیش‌فرض: `fa-IR-DilaraNeural`
- rate پیش‌فرض: `-4%`
- قبل از ساخت MP4، صدای narration را تولید و وجود فایل معتبر را بررسی کن.
- اگر TTS ناموفق شد، Scene نباید silently completed شود.

### Visual generation
- از `visual_prompt_policy.py` برای ساخت prompt استفاده کن.
- شخصیت اصلی بین Sceneها ثابت بماند.
- برای تبلیغ کلینیک، اگر reference image واقعی مرکز وجود دارد، به generator داده شود.
- تصویر با `visual_qa.py` بررسی شود.
- اگر QA رد کرد، همان Scene دوباره generate شود.
- حداکثر 3 تلاش برای هر Scene.
- تصویر ردشده هرگز وارد خروجی نهایی نشود.

### Video fallback
- Video provider اولویت دارد.
- Image fallback فقط بعد از شکست video استفاده شود.
- image fallback باید با `media_assembler.image_to_clip()` به کلیپ متحرک تبدیل شود.

### Music
- موسیقی خارجی/کپی‌شده استفاده نشود.
- اگر Music API در دسترس نبود، `make_suspense_bed()` استفاده شود.
- موسیقی نباید روی narration غلبه کند.

### Final gate
قبل از mark کردن job به عنوان completed:
1. MP4 وجود داشته باشد.
2. duration > 10s باشد.
3. audio stream وجود داشته باشد.
4. narration وجود داشته باشد.
5. هیچ Scene با visual QA ردشده باقی نمانده باشد.
