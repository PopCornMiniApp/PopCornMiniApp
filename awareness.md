# PopCorn 🍿 — Project Awareness Document

> آخر تحديث: 2026-05-08

## نظرة عامة على المشروع

PopCorn هو تطبيق مصغر داخل تيليجرام (Telegram Mini App) لمشاهدة الأفلام والمسلسلات بجودة عالية مع بث مباشر عبر بروتوكول MTProto.

---

## المعمارية الكاملة

```
[مستخدم تيليجرام]
       │
       ▼
[البوت الرئيسي (MAIN_BOT)]  ← يعمل فقط كـ حامل للتطبيق المصغر
       │  يفتح Mini App فقط — لا يرسل أي وسائط
       ▼
[HuggingFace Space: toolkit-backend-popcorn.hf.space]
       │
       ├── FastAPI Backend (port 7860)
       │     ├── /api/movies, /api/series, /api/search
       │     ├── /api/stream/{file_id}  ← بث الفيديو عبر Pyrogram MTProto
       │     └── /api/admin/*           ← أوامر الإدارة
       │
       ├── Frontend (React/Vite → static/)
       │     └── يعمل داخل إطار التطبيق المصغر في تيليجرام
       │
       └── SQLite DB (/tmp/popcorn.db) ← مزامنة تلقائية مع HuggingFace Dataset
```

## مسار البيانات

```
[مجموعة DB الخاصة: -1003826837517]
  └── Topics (forum topics) تحتوي على:
        ├── فيلم: #Title #movies #midXXXXX #TMDB_ID
        └── مسلسل: #Title #series #sN #sidXXXXX #TMDB_ID
              └── ملفات الفيديو داخل كل Topic بـ caption:
                    ├── فيلم: #Title #Movie
                    └── حلقة: #Title #SN #EN

[sync_bot.py] يستمع لرسائل المجموعة الخاصة:
  ├── Topic جديد → register_topic() → TMDB → upsert_movie/series
  └── ملف فيديو → file_id محفوظ في DB (لا إعادة إرسال)

[HuggingFace Dataset: ToolKit-backend/PopCornDB]
  └── popcorn.db ← يُحمَّل تلقائيًا كل 10 دقائق + عند كل تغيير

[Pyrogram MTProto clients]
  └── stream_bot_1 + stream_bot_2 ← تدفق الفيديو مباشرة من تيليجرام
```

## مسار المستخدم داخل التطبيق

```
1. المستخدم يفتح البوت → يضغط "فتح PopCorn" → يفتح Mini App
2. الصفحة الرئيسية: أفلام مميزة + آخر الإضافات
3. المستخدم يختار فيلم/مسلسل → صفحة التفاصيل (TMDB: ملصق، قصة، تقييم، ممثلون)
4. يضغط "مشاهدة" → مشغل الفيديو المدمج في التطبيق
5. المشغل يطلب: GET /api/stream/{file_id}
6. Backend يبث الفيديو عبر Pyrogram (MTProto) مع دعم Range requests للتخطي
```

---

## قاعدة البيانات

**الجداول:**
- `movies`: id, tmdb_id, title, title_ar, poster_path, backdrop_path, rating, file_id, file_size, duration, topic_id, message_id
- `series`: id, tmdb_id, title, title_ar, poster_path, backdrop_path, rating, total_seasons, status
- `episodes`: series_id, season_number, episode_number, file_id, file_size, duration, topic_id, message_id
- `topic_series_map`: topic_id → series_id (ربط مواضيع المجموعة بالمسلسلات)

**الإحصائيات الحالية (2026-05-08):**
- أفلام: 22
- مسلسلات: 3 (Stranger Things, See, روايته وروايتها)
- حلقات: 78

---

## المتغيرات البيئية المطلوبة

| المتغير | الوصف |
|---|---|
| `MAIN_BOT_TOKEN` | البوت الرئيسي — حامل التطبيق فقط |
| `STREAM_BOT_1`, `STREAM_BOT_2` | بوتات البث عبر Pyrogram |
| `SESSION_1_API_ID`, `SESSION_1_API_HASH` | بيانات MTProto للبث |
| `SESSION_2_API_ID`, `SESSION_2_API_HASH` | بيانات MTProto احتياطية |
| `ADMIN_ID` | معرف المشرف (5703679073) |
| `PRIVATE_GROUP_ID` | المجموعة الخاصة لقاعدة البيانات (-1003826837517) |
| `PUBLIC_CHANNEL_ID` | القناة العامة (-1003944402689) |
| `HF_TOKEN` | رمز HuggingFace للمزامنة |
| `HF_DATASET_NAME` | ToolKit-backend/PopCornDB |
| `TMDB_API_KEY` | مفتاح TMDB للبيانات الوصفية |

---

## المشاكل التي تم حلها (2026-05-08)

### ✅ الإصلاح 1: البوت يرسل فيديوهات للخاص
**المشكلة:** `scan_file_ids` كان يستخدم `bot.forward_message(chat_id=ADMIN_ID)` لاستخراج file_ids، مما يتسبب في إرسال كل الفيديوهات للمشرف في الخاص.

**الحل:** استبدلنا `forward_message()` بـ `pyro.get_messages(GROUP_ID, msg_id)` — Pyrogram يقرأ الرسائل مباشرة من المجموعة عبر MTProto دون إرسال أي شيء لأي مكان.

### ✅ الإصلاح 2: الفرونت يعرض JSON خطأ
**المشكلة:** `@app.get("/{full_path:path}")` مع `async def spa(_: str)` — FastAPI يفسر `_` كـ query parameter مطلوب وليس path parameter، مما يسبب خطأ `Field required`.

**الحل:** تغيير التوقيع إلى `async def spa(full_path: str)` ليطابق اسم متغير المسار.

### ✅ الإصلاح 3: خطأ إملائي في رابط Mini App
**المشكلة:** `MINI_APP_URL = "https://toolki-backend-popcorn.hf.space"` (toolki بدلاً من toolkit)

**الحل:** تصحيح الرابط إلى `"https://toolkit-backend-popcorn.hf.space"`

---

## البوت الرئيسي — قاعدة ذهبية

> **البوت الرئيسي لا يرسل أي وسائط (فيديو/صور/ملفات) أبداً.**
> دوره الوحيد: إرسال زر "فتح PopCorn" الذي يفتح Mini App.
> كل المحتوى يُشاهَد داخل التطبيق المصغر عبر المشغل المدمج.
> البوتات المسؤولة عن البث هي STREAM_BOT_1 و STREAM_BOT_2 فقط عبر Pyrogram.

---

## ملفات المشروع الرئيسية

| الملف | الوظيفة |
|---|---|
| `app/main.py` | FastAPI app — API routes + static file serving |
| `app/bot_commands.py` | أوامر البوت الرئيسي (start, app, admin) |
| `app/sync_bot.py` | مزامنة المجموعة الخاصة — يحفظ file_ids في DB |
| `app/stream.py` | بث الفيديو عبر Pyrogram MTProto |
| `app/database.py` | SQLite + مزامنة HuggingFace Dataset |
| `app/config.py` | إعدادات المشروع من متغيرات البيئة |
| `app/tmdb.py` | جلب البيانات الوصفية من TMDB |
| `static/` | الفرونت المبني (React/Vite) |
| `frontend/` | كود الفرونت المصدر |

---

## التطويرات المقترحة

- [ ] إضافة صفحة "المفضلة" مع حفظ محلي (localStorage)
- [ ] دعم البحث بالعربية مع تصحيح الإملاء
- [ ] إضافة نظام تقييم من المستخدمين
- [ ] دعم الترجمات (subtitle) في المشغل
- [ ] إضافة مسلسلات وأفلام جديدة بشكل دوري
