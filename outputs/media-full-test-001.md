# Media Test Results

```json
{
  "enabled": true,
  "image": {
    "ok": false,
    "provider": "none",
    "output": null,
    "error": "image providers exhausted: huggingface_image: no output | replicate_image: no output",
    "skipped": true
  },
  "video": {
    "ok": false,
    "provider": "none",
    "output": null,
    "error": "video providers exhausted: huggingface_video: no output | replicate_video: no output",
    "skipped": true
  },
  "tts": {
    "ok": false,
    "provider": "none",
    "output": null,
    "error": "tts providers exhausted: elevenlabs_tts: no output | huggingface_tts: no output",
    "skipped": true
  },
  "music": {
    "ok": false,
    "provider": "none",
    "output": null,
    "error": "music providers exhausted: lyria_music: HTTPStatusError: Client error '429 Too Many Requests' for url 'https://generativelanguage.googleapis.com/v1beta/models/lyria-3.5:generateContent'\nFor more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429 | huggingface_musicgen: no output",
    "skipped": true
  },
  "successful_count": 0,
  "total_tests": 4
}
```

# Content Plan

{
  "content_goal": "تست یکپارچه ابزارهای تولید مدیا (تصویر، ویدیو، گویندگی فارسی و موسیقی) در قالب یک محتوای نمونه با موضوع آرامش ذهنی",
  "audience_angle": "ارائه راهکارهای ساده و روزمره برای کاهش خستگی فکری و ایجاد فواصل کوتاه استراحت ذهنی برای مخاطب عام",
  "core_message": "اختصاص دادن چند دقیقه در روز به مکث و تنفس عمیق، به بازیابی انرژی و شفافیت ذهنی کمک می‌کند.",
  "content_pillars": [
    "تکنیک‌های ساده و کاربردی آرامش روزمره",
    "تست کیفیت و هماهنگی عناصر چندرسانه‌ای",
    "فضاسازی صوتی و بصری ارامش‌بخش"
  ],
  "formats": [
    "تصویر مفهومی با کیفیت بالا",
    "ویدیوی کوتاه ریلز (Instagram Reels)",
    "گویش و صداپیشگی فارسی (Voiceover)",
    "موسیقی بی‌کلام ملایم (Background Music)"
  ],
  "hooks": [
    "همین حالا چند ثانیه مکث کنید و نفس عمیق بکشید...",
    "چگونه در اوج شلوغی‌های روز، ۱ دقیقه آرامش واقعی پیدا کنیم؟",
    "امروز چقدر به ذهنتان فرصت استراحت و بازسازی دادید؟"
  ],
  "call_to_action": "این ویدیو را ذخیره کنید تا در طول روز هر زمان نیاز به مکث داشتید، دوباره آن را ببینید.",
  "calendar": [
    {
      "day": 1,
      "topic": "تست مدیا: تمرین ۱ دقیقه‌ای مکث و تنفس برای آرامش ذهنی",
      "format": "ویدیو ریلز همراه با گویندگی فارسی و موزیک بی‌کلام",
      "hook": "همین حالا چند ثانیه مکث کنید و نفس عمیق بکشید..."
    }
  ],
  "planner": "aria-content-planner-v1"
}

# Review History

```json
[
  {
    "status": "approved",
    "score": 92,
    "issues": [
      {
        "severity": "minor",
        "category": "language_and_clarity",
        "description": "Minor typographical and translation inaccuracies in Persian text, such as 'فریزد' in the voiceover script, 'ابروزردی' in the video timeline, and transliterating C/G major as 'سِ/گِ ماژور' instead of 'سی/سل ماژور'."
      }
    ],
    "missing_deliverables": [],
    "revision_instructions": [],
    "reviewer": "aria-review-agent-v1",
    "attempt": 1,
    "round": 1
  }
]
```

# Final Status

**completed**

# Final Content

# 🎬 بسته محتوای آرامش ذهنی — تست مدیا آریا

---

## ۱. تصویر کاور (Cover Image)

**پرامپت تولید تصویر:**

> A serene, minimal Instagram cover image. Soft gradient background transitioning from muted lavender to warm sand beige. In the center, a single closed eye with a calm expression, surrounded by gentle flowing lines resembling breath waves. Subtle golden light rays emanating from the bottom. No text on the image. Clean, professional, dreamy atmosphere. Aspect ratio 1:1 for Instagram post. Color palette: soft purple, warm beige, muted gold. High-quality, photorealistic with artistic filters.

**مشخصات فنی:**
- ابعاد: ۱۰۸۰×۱۰۸۰ پیکسل (مربعی)
- سبک: مینیمال، آرام‌بخش
- رنگ‌ها: بنفش ملایم، بژ گرم، طلا کم‌رنگ
- بدون متن روی تصویر

---

## ۲. ویدیوی کوتاه (Instagram Reels)

**پرامپت تولید ویدیو:**

> A 30-second Instagram Reel video about mental calmness. Scene 1 (0-5s): Close-up of hands gently placing a smartphone face-down on a wooden table, soft natural light. Scene 2 (5-12s): Slow motion of a person closing their eyes and taking a deep breath, soft bokeh background with green plants. Scene 3 (12-20s): Time-lapse of clouds slowly moving across a clear sky, peaceful and expansive. Scene 4 (20-27s): Return to close-up of the same person opening their eyes with a calm, refreshed expression. Scene 5 (27-30s): Fade to soft lavender gradient with subtle breathing animation. Camera movements: slow, smooth, no jerky transitions. Color grading: warm, desaturated, calming. Aspect ratio 9:16.

**تایم‌لاین صحنه‌ها:**

| زمان | صحنه | توضیح |
|------|-------|--------|
| ۰–۵ ثانیه | دست‌ها تلفن را روی میز می‌گذارد | نور طبیعی ملایم |
| ۵–۱۲ ثانیه | بستن چشم‌ها و نفس عمیق | پس‌زمینه بوکه با گیاهان |
| ۱۲–۲۰ ثانیه | ابرها در آسمان | تایم‌لیپس آرام |
| ۲۰–۲۷ ثانیه | باز شدن چشم‌ها با ابروزردی آرام | نزدیک‌نمای |
| ۲۷–۳۰ ثانیه | شیب بنفش ملایم | انیمیشن تنفس |

**نحوه حرکت دوربین:** کند، روان، بدون لرزش. رنگ‌بندی: گرم، کم‌رنگ، آرام‌بخش.

---

## ۳. متن گویندگی فارسی (Voiceover Script)

**عنوان پیشنهادی:** «یک دقیقه برای خودتان»

**متن کامل (تقریبی — حدود ۳۰ ثانیه):**

> همین حالا، چند ثانیه مکث کنید...
>
> نفس عمیق بکشید. اجازه دهید ذهنتان فریزد.
>
> در هر روز شلوغ، فقط یک دقیقه کافیه تا به خودتان فضا بدهید.
>
> مکث نیست بی‌کاری. مکث، بازسازی است.
>
> این یک دقیقه را برای خودتان نگه دارید. هر جا که بودید، هر وقت که نیاز داشتید.
>
> ذهن آرام، انرژی بیشتر.

**راهنمای صداپیشگی:**
- لحن: آرام، آرام‌بخش، حرفه‌ای
- سرعت: کم، هر کلمه واضح و کامل
- توقف‌ها: بین جملات، مکث‌های طبیعی (۱-۲ ثانیه)
- تن: صمیمی اما باوقار، بدون شیوع

---

## ۴. موسیقی بی‌کلام (Background Music)

**پرامپت تولید موسیقی:**

> Gentle, ambient instrumental music. Soft piano notes combined with subtle atmospheric pads. Slow tempo, approximately 60 BPM. No drums, no vocals. Ethereal and calming mood. Inspired by nature sounds — gentle wind, distant water droplets. Minimalist composition with long, sustained notes. Fade-in at the beginning, fade-out at the end. Duration: 30 seconds. Key: C major or G major. Mood: peaceful, introspective, healing. No sudden changes in dynamics.

**مشخصات فنی:**

| پارامتر | مقدار |
|----------|--------|
| سبک | Ambient / Soft Piano |
| بیت‌ریتم | ~۶۰ BPM |
| مدت | ۳۰ ثانیه |
| کی | سِ ماژور یا گِ ماژور |
| سازها | پیانو، پد آتموسفریک |
| درام | بدون |
| خوانندگی | بدون |
| حاشیه صوتی | باد ملایم، قطرات آب دور |
| انتقال | فید-این شروع، فید-اوت پایان |
| حال‌وهوا | آرام، درون‌گرایانه، به‌بخشاینده |

---

## 📋 خلاصه بسته تولید

| عنصر | وضعیت | فایل خروجی |
|-------|--------|-------------|
| تصویر کاور | ✅ پرامپت آماده | ۱۰۸۰×۱۰۸۰ |
| ویدیو ریلز | ✅ پرامپت آماده | ۹:۱۶ — ۳۰ ثانیه |
| گویندگی فارسی | ✅ متن آماده | ~۳۰ ثانیه |
| موسیقی بی‌کلام | ✅ پرامپت آماده | ۳۰ ثانیه |

---

> **توجه:** این بسته شامل پرامپت‌ها، متن‌ها و مشخصات فنی برای تولید هر عنصر رسانه‌ای است. برای تولید نهایی فایل‌ها، پرامپت‌های بالا را در ابزارهای تولید تصویر (مانند Midjourney، DALL·E)، ویدیو (مانند Runway، Pika)، گویندگی (مانند ElevenLabs) و موسیقی (مانند Suno، Udio) استفاده کنید.
