# Content Plan

{
  "content_goal": "افزایش آگاهی علمی و کاربردی مخاطبان نوجوان و جوان درباره ریشه‌های هیجانی اهمال‌کاری و ارائه راهکارهای عملی برای مدیریت آن در قالب کاروسل اینستاگرام.",
  "audience_angle": "تغییر نگاه مخاطب از «من تنبل هستم» به «ذهن من در حال مواجهه با هیجان سخت است» و ایجاد صمیمیت بدون برچسب‌زنی روان‌شناختی.",
  "core_message": "اهمال‌کاری نشانه تنبلی یا کمبود اراده نیست، بلکه الگویی برای مدیریت هیجانات منفی و ترس از شکست است که با راهکارهای ریز و مستمر قابل اصلاح است.",
  "content_pillars": [
    "شناخت ریشه‌های هیجانی اهمال‌کاری",
    "تفاوت ساختاری تنبلی و اهمال‌کاری",
    "تکنیک‌های عملی شروع کار (کاهش اصطکاک اولیه)",
    "مدیریت کمال‌گرایی و پذیرش خود"
  ],
  "formats": [
    "Carousel (کاروسل آموزشی ۷ اسلایدی)",
    "Single Image Graphic (پوستر مفهومی)",
    "Short Reel (ویدیو کوتاه مرور نکات)",
    "Interactive Story (نظرسنجی و تعامل)"
  ],
  "hooks": [
    "چرا با اینکه می‌دونی کار مهمی داری، باز هم میری سراغ گوشی؟",
    "اهمال‌کاری تنبلی نیست؛ پس واقعاً چیه؟",
    "چطور قفل شروع کارهای سخت رو توی ۳ دقیقه بشکنیم؟"
  ],
  "call_to_action": "تو بیشتر توی چه موقعیت‌هایی کارت رو عقب می‌ندازی؟ برامون توی کامنت بنویس تا با هم راهکارهاش رو بررسی کنیم.",
  "calendar": [
    {
      "day": 1,
      "topic": "ریشه‌یابی هیجانی اهمال‌کاری",
      "format": "Carousel",
      "hook": "چرا کارهای مهم رو به بعد موکول می‌کنیم؟ (بررسی علت علمی بدون تعارف)"
    },
    {
      "day": 2,
      "topic": "تفکیک تنبلی از اهمال‌کاری",
      "format": "Single Image Graphic",
      "hook": "تنبلی یا اهمال‌کاری؟ این دو تا یکی نیستن!"
    },
    {
      "day": 3,
      "topic": "تکنیک گام‌های کوچک (Micro-steps)",
      "format": "Carousel",
      "hook": "چطور کار ۵ ساعته رو طوری خرد کنیم که ذهن ازش نترسه؟"
    },
    {
      "day": 4,
      "topic": "ارتباط کمال‌گرایی و عقب انداختن کارها",
      "format": "Short Reel",
      "hook": "تا همه چیز عالی نباشه شروع نمی‌کنی؟"
    },
    {
      "day": 5,
      "topic": "جمع‌بندی و پرسش و پاسخ تعاملی",
      "format": "Interactive Story",
      "hook": "بزرگ‌ترین مانع تو برای شروع کارها کدومه؟"
    }
  ],
  "planner": "aria-content-planner-v1"
}

# Review History

## Review Round 1

{
  "round": 1,
  "status": "manual_review",
  "score": null,
  "issues": [
    {
      "severity": "critical",
      "category": "review_agent_failure",
      "description": "All AI providers failed. Gemini: Gemini failed: gemini-3.6-flash: HTTP 429: {\n  \"error\": {\n    \"code\": 429,\n    \"message\": \"You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash\\nPlease retry in 35.312304315s.\",\n    \"status\": \"RESOURCE_EXHAUSTED\",\n    \"details\": [\n      {\n        \"@type\": \"type.googleapis.com/google.rpc.Help\",\n        \"links\": [\n          {\n            \"description\": \"Learn more about Gemini API quotas\",\n            \"url\": \"https://ai.google.dev/gemini-api/docs/rate-limits\"\n          }\n        ]\n      },\n      {\n        \"@type\": \" | gemini-2.5-flash-lite: HTTP 404: {\n  \"error\": {\n    \"code\": 404,\n    \"message\": \"This model models/gemini-2.5-flash-lite is no longer available to new users. Please update your code to use models/gemini-3.5-flash-lite for the latest features and improvements. We recommend you to use the Interactions API.\",\n    \"status\": \"NOT_FOUND\"\n  }\n}\n | OpenRouter: OPENROUTER_API_KEY is missing | Cerebras: HTTP 402: {\"message\":\"Payment required to access this resource. Visit your billing tab.\",\"type\":\"payment_required_error\",\"param\":\"quota\",\"code\":\"payment_required\"}"
    }
  ],
  "missing_deliverables": [],
  "revision_instructions": [],
  "reviewer": "aria-review-agent-v1"
}

# Final Status

Status: MANUAL_REVIEW_REQUIRED

Reason: All AI providers failed. Gemini: Gemini failed: gemini-3.6-flash: HTTP 429: {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash\nPlease retry in 35.312304315s.",
    "status": "RESOURCE_EXHAUSTED",
    "details": [
      {
        "@type": "type.googleapis.com/google.rpc.Help",
        "links": [
          {
            "description": "Learn more about Gemini API quotas",
            "url": "https://ai.google.dev/gemini-api/docs/rate-limits"
          }
        ]
      },
      {
        "@type": " | gemini-2.5-flash-lite: HTTP 404: {
  "error": {
    "code": 404,
    "message": "This model models/gemini-2.5-flash-lite is no longer available to new users. Please update your code to use models/gemini-3.5-flash-lite for the latest features and improvements. We recommend you to use the Interactions API.",
    "status": "NOT_FOUND"
  }
}
 | OpenRouter: OPENROUTER_API_KEY is missing | Cerebras: HTTP 402: {"message":"Payment required to access this resource. Visit your billing tab.","type":"payment_required_error","param":"quota","code":"payment_required"}

# پکیج محتوایی کاروسل اینستاگرام: ریشه‌یابی و مدیریت اهمال‌کاری

---

## 📌 عنوان جذاب (Title)
**فرار از کار یا فرار از هیجان؟ | چرا کارهای مهم‌مون رو عقب می‌ندازیم؟**

---

## 📱 متن اسلایدها (Carousel Slides)

### اسلاید ۱
چرا با اینکه می‌دونی یه کار مهم داری، باز هم میری سراغ گوشی؟
خیلی وقت‌ها فکر می‌کنیم تنبلیم، اما واقعیت چیز دیگه‌ایه. بیا این الگوی ذهنی رو علمی و ساده بررسی کنیم.

---

### اسلاید ۲
**اهمال‌کاری تنبلی نیست!**
تنبلی یعنی کلاً تمایلی به انجام کار نداری.
اما در اهمال‌کاری، تمایل داری کار انجام بشه، ولی یک حس ناخوشایند یا استرس، جلوی شروع کردنت رو می‌گیره.

---

### اسلاید ۳
**ریشه اصلی: فرار از هیجان منفی**
وقتی یک کار سخت یا مبهم داری، مغز اون رو به عنوان فشار یا ترس شناسایی می‌کنه.
برای فرار از این حس ناخوشایند، مغز سریعاً پناه می‌بره به کارهای راحت مثل فضای مجازی.

---

### اسلاید ۴
**تله کمال‌گرایی**
خیلی از مواقع، ترس از «عالی انجام ندادن» کار، باعث عقب انداختنش میشه.
ذهن می‌گه: «یا کامل و بی‌نقص، یا کلاً هیچ‌چی!» همین تفکر، بزرگ‌ترین مانع شروع حرکت است.

---

### اسلاید ۵
**راهکار اول: تکنیک micro-step (گام‌های میکروسکوپی)**
کار بزرگ رو به بخش‌های خیلی کوچک تقسیم کن.
به جای «خواندن کل کتاب»، بگو «خواندن فقط یک صفحه».
وقتی هدف کوچک باشه، ذهن احساس تهدید یا سختی نمی‌کنه.

---

### اسلاید ۶
**راهکار دوم: قانون ۲ دقیقه**
به خودت بگو: «من فقط ۲ دقیقه روی این کار زمان می‌ذارم و بعد می‌تونم رهاش کنم.»
سخت‌ترین بخش کار، همون شکستن اصطکاک و مقاومت اولیه ذهن است.

---

### اسلاید ۷
**چرخه سرزنش رو متوقف کن**
احساس گناه و خودسرزنشی، اضطراب رو بیشتر می‌کنه و اهمال‌کاری رو تشدید می‌کنه.
پذیرش این الگو و برخورد صبورانه با خود، اولین قدم برای تغییر عادت‌هاست.

---

### اسلاید ۸
**قدم اول رو همین امروز بردار**
تغییر الگوهای رفتاری زمان‌بره، اما با گام‌های ریز و مستمر ممکنه.

👇 **تو بیشتر توی چه موقعیت‌هایی کارت رو عقب می‌ندازی؟ برامون توی کامنت بنویس تا با هم بررسی‌اش کنیم.**

---

## 📝 کپشن اینستاگرام (Instagram Caption)

تا حالا شده با وجود اینکه می‌دونی فردا امتحان داری یا یک پروژه مهم روی میزت مونده، ساعت‌ها توی اکسپلور چرخ بزنی و بعدش دچار احساس گناه بشی؟ 📱💔

خیلی از ما توی این شرایط، اولین برچسبی که به خودمون می‌زنیم «تنبلی» یا «کمبود اراده» است. اما روان‌شناسی مدرن نگاه متفاوتی به این موضوع داره: 

اهمال‌کاری در واقع یک سیستم دفاعی ذهنی برای مدیریت هیجانات منفیه. وقتی کاری برامون مبهم، سخت، یا همراه با ترس از شکست به نظر میرسه، ذهن برای محافظت از ما در برابر احساس استرس، صورت‌مسئله رو پاک می‌کنه و سراغ لذت‌های سریع (مثل گوشی) میره.

🔑 **چطور این چرخه رو مدیریت کنیم؟**
۱. شناخت کمال‌گرایی و رها کردن تفکر «یا همه چیز یا هیچ‌چیز».
۲. خرد کردن کارها به قدم‌های بسیار کوچک که ذهن ازشون نترسه.
۳. جایگزین کردن خودشفقتی به جای سرزنش و احساس گناه.

یادت باشه هدف، تغییر یک‌شبه نیست؛ بلکه ایجاد آگاهی و برداشتن قدم‌های کوچک اما آگاهانه‌ست. 🍃

---

## 🎯 دعوت به اقدام (CTA)

**تو بیشتر توی چه موقعیت‌هایی کارت رو عقب می‌ندازی؟ برامون توی کامنت بنویس تا با هم راهکارهاش رو بررسی کنیم.**
