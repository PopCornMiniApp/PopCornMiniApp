# PopCorn 🍿 — Project Awareness Document

> آخر تحديث: 2026-05-08 (v3.3)

## نظرة عامة على المشروع

PopCorn هو تطبيق مصغر داخل تيليجرام (Telegram Mini App) لمشاهدة الأفلام والمسلسلات بجودة عالية مع بث مباشر عبر بروتوكول MTProto.

---

## المعمارية الكاملة

```
[مستخدم تيليجرام]
       │
       ▼
[البوت الرئيسي (MAIN_BOT)]  ← يعمل كـ حامل للتطبيق المصغر + مزامنة المجموعة
       │  يفتح Mini App — لا يرسل أي وسائط
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

[scanner.py] يمسح كل المواضيع والرسائل:
  ├── يُشغَّل يدوياً بأمر /admin → زر "مزامنة المجموعة الآن"
  └── يُشغَّل تلقائياً كل ساعتين (_periodic_autoscan)

[HuggingFace Dataset: ToolKit-backend/PopCornDB]
  └── popcorn.db ← يُحمَّل تلقائيًا كل 10 دقائق + عند كل تغيير

[Pyrogram MTProto clients]
  └── stream_bot_1 + stream_bot_2 ← تدفق الفيديو مباشرة من تيليجرام
```

---

## قاعدة البيانات

**الجداول:**
- `movies`: id, tmdb_id, title, title_ar, poster_path, backdrop_path, rating, file_id, file_size, duration, topic_id, message_id
- `series`: id, tmdb_id, title, title_ar, poster_path, backdrop_path, rating, total_seasons, status
- `episodes`: series_id, season_number, episode_number, file_id, file_size, duration, topic_id, message_id
- `topic_series_map`: topic_id → series_id (ربط مواضيع المجموعة بالمسلسلات) ← جدول حيوي جديد

---

## الإصلاحات (v3.3 — 2026-05-08)

### ✅ إصلاح 1: دوال قاعدة البيانات المفقودة (السبب الجذري لعدم المزامنة)
**المشكلة:** `scanner.py` و`sync_bot.py` يستدعيان `db.update_movie_file`, `db.get_episode`, `db.update_episode_file` لكنها غير موجودة في `database.py` — مما يسبب AttributeError ويوقف المزامنة تماماً.
**الحل:** أضفنا الدوال الثلاث المفقودة وجدول `topic_series_map` لقاعدة البيانات.

### ✅ إصلاح 2: البوت لا يرد على الأوامر
**المشكلة:** البوت لا يحذف الـ webhook قبل بدء الـ polling، وكان `drop_pending_updates=False`.
**الحل:** أضفنا `bot.delete_webhook(drop_pending_updates=True)` قبل بدء الـ polling وغيّرنا إلى `drop_pending_updates=True`.

### ✅ إصلاح 3: عدم تحديث قاعدة البيانات من المجموعة تلقائياً
**المشكلة:** `_periodic_sync` كان يرفع DB فقط ولا يمسح المجموعة للمحتوى الجديد.
**الحل:** أضفنا `_periodic_autoscan()` يعمل كل ساعتين ويشغّل `run_full_scan()` تلقائياً.

### ✅ إصلاح 4: توقيع `_map_topic_to_series` خاطئ
**المشكلة:** في `register_topic_handler.py` تُستدعى بمعاملين لكنها معرّفة بمعامل واحد.
**الحل:** استبدلناها بـ `set_topic_series_map(topic_id, series_id)` من `database.py`.

### ✅ إصلاح 5: أزرار البوت وتنظيم الكيبورد
**الحل:** أعدنا ترتيب أزرار inline keyboard بحيث كل صف منفصل لتجنب التداخل مع أزرار تيليجرام الأصلية.

### ✅ إصلاح 6: المسح الكامل يصل 3000 رسالة بدلاً من 2000
**الحل:** رفعنا حد `get_chat_history` من 2000 إلى 3000 لضمان التقاط كل المحتوى.

---

## المتغيرات البيئية المطلوبة

| المتغير | الوصف |
|---|---|
| `MAIN_BOT_TOKEN` | البوت الرئيسي — حامل التطبيق + مزامنة المجموعة |
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

## ملفات المشروع الرئيسية

| الملف | الوظيفة |
|---|---|
| `app/main.py` | FastAPI app — API routes + bot startup + periodic tasks |
| `app/bot_commands.py` | أوامر البوت الرئيسي (start, app, admin, fullscan) |
| `app/sync_bot.py` | مزامنة المجموعة الخاصة — يحفظ file_ids في DB |
| `app/scanner.py` | فحص كامل للمجموعة — يُشغَّل يدوياً وتلقائياً كل ساعتين |
| `app/database.py` | SQLite + مزامنة HuggingFace Dataset |
| `app/register_topic_handler.py` | معالج أحداث إنشاء/تعديل المواضيع |
| `app/stream.py` | بث الفيديو عبر Pyrogram MTProto |
| `app/config.py` | إعدادات المشروع من متغيرات البيئة |
| `app/tmdb.py` | جلب البيانات الوصفية من TMDB |
| `static/` | الفرونت المبني (React/Vite) |
| `frontend/` | كود الفرونت المصدر |

---

## قاعدة ذهبية

> **البوت الرئيسي لا يرسل أي وسائط (فيديو/صور/ملفات) أبداً.**
> دوره: إرسال زر "فتح PopCorn" + مزامنة المجموعة الخاصة.
> كل المحتوى يُشاهَد داخل التطبيق المصغر عبر المشغل المدمج.
> البوتات المسؤولة عن البث هي STREAM_BOT_1 و STREAM_BOT_2 فقط عبر Pyrogram.
