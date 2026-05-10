# 🚀 دليل النشر الشامل - PopCorn Distributed System

## 📋 المتطلبات الأساسية

### 1. حسابات HuggingFace
تحتاج إلى حسابين على الأقل:
- **الحساب الرئيسي**: ToolKit-backend (موجود)
- **الحساب الثانوي**: rayig (موجود)

### 2. الحصول على Tokens
1. اذهب إلى: https://huggingface.co/settings/tokens
2. أنشئ token جديد مع صلاحيات:
   - ✅ Read access to repos
   - ✅ Write access to repos
   - ✅ Manage repos (create, delete)
3. احفظ الـ token في مكان آمن

### 3. إعداد ملف .env
```bash
cd PopCorn

# انسخ ملف المثال
cp .env.example .env

# عدل الملف وأضف الـ tokens
nano .env
```

أضف هذه الأسطر في `.env`:
```bash
# HuggingFace Tokens
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxx  # Token للحساب الرئيسي
HF_TOKEN_2=hf_xxxxxxxxxxxxxxxxxxxxxxxxxx  # Token للحساب الثانوي (rayig)

# أسماء الحسابات
HF_ACCOUNT_MAIN=ToolKit-backend
HF_ACCOUNT_2=rayig
```

---

## 🎯 خطوات النشر

### المرحلة 1: التحقق من البيئة

```bash
# تأكد من وجود الـ tokens
cd PopCorn
python3 -c "import os; print('HF_TOKEN:', 'Found' if os.getenv('HF_TOKEN') else 'Missing')"
```

### المرحلة 2: نشر النظام الموزع

```bash
# تحميل المتغيرات من .env
export $(cat .env | grep -v '^#' | xargs)

# تشغيل النشر
python3 deploy_production_system.py
```

### المرحلة 3: التحقق من النشر

```bash
# فحص الـ Spaces المنشورة
python3 -c "
from huggingface_hub import HfApi
import os

api = HfApi(token=os.getenv('HF_TOKEN'))
user = api.whoami()
print(f'Username: {user[\"name\"]}')
print('Spaces:', [s.id for s in api.list_spaces(author=user['name'])])
print('Datasets:', [d.id for d in api.list_datasets(author=user['name'])])
"
```

---

## 📦 ما سيتم نشره

### Spaces (4 مساحات)

#### 1. popcorn-main (ToolKit-backend)
- **الغرض**: API الرئيسي والواجهة الأمامية
- **الخدمات**: API, Frontend, WebSocket
- **الأولوية**: عالية
- **الحالة**: قيد التشغيل

#### 2. popcorn-streaming (ToolKit-backend)
- **الغرض**: خدمات البث ومعالجة الوسائط
- **الخدمات**: Stream Handler, Video Processing, Cache
- **الأولوية**: عالية
- **الحالة**: مخطط

#### 3. popcorn-backup (rayig)
- **الغرض**: خدمات النسخ الاحتياطي والمزامنة
- **الخدمات**: Backup Manager, Sync Bot, Mirror Manager
- **الأولوية**: متوسطة
- **الحالة**: مخطط

#### 4. popcorn-analytics (rayig)
- **الغرض**: التحليلات والمراقبة
- **الخدمات**: Analytics, Health Monitor, User Tracking
- **الأولوية**: متوسطة
- **الحالة**: مخطط

### Datasets (6 قواعد بيانات)

#### 1. PopCornDB-Main (ToolKit-backend)
- **الغرض**: قاعدة البيانات الأساسية
- **الجداول**: movies, series, episodes, users
- **الحجم المتوقع**: 5 GB
- **الأولوية**: حرجة

#### 2. PopCornDB-Media (ToolKit-backend)
- **الغرض**: بيانات الوسائط والكاش
- **الجداول**: media_files, thumbnails, subtitles
- **الحجم المتوقع**: 10 GB
- **الأولوية**: عالية

#### 3. PopCornDB-Analytics (ToolKit-backend)
- **الغرض**: التحليلات والسجلات
- **الجداول**: view_logs, user_activity, performance_metrics
- **الحجم المتوقع**: 3 GB
- **الأولوية**: متوسطة

#### 4. PopCornDB-Backup (rayig)
- **الغرض**: النسخ الاحتياطي الكامل
- **الجداول**: all_tables_backup
- **الحجم المتوقع**: 20 GB
- **الأولوية**: عالية

#### 5. PopCornDB-Cache (rayig)
- **الغرض**: الكاش الموزع
- **الجداول**: cache_entries, session_data
- **الحجم المتوقع**: 2 GB
- **الأولوية**: متوسطة

#### 6. PopCornDB-Archive (rayig)
- **الغرض**: أرشيف البيانات التاريخية
- **الجداول**: archived_logs, old_sessions
- **الحجم المتوقع**: 5 GB
- **الأولوية**: منخفضة

---

## 🔧 إصلاح مشكلة المزامنة مع Telegram

### المشكلة
المسلسل الجديد لم يظهر بسبب خطأ في الوصول للمجموعة الخاصة.

### الحل

#### 1. التحقق من صلاحيات البوت
```bash
# افتح Telegram وتحقق من:
# - البوت موجود في المجموعة
# - البوت لديه صلاحيات Admin
# - البوت يمكنه قراءة الرسائل
```

#### 2. تشخيص المشكلة
```bash
cd PopCorn
python3 fix_telegram_sync.py
```

#### 3. إعادة المسح الكامل
```bash
python3 trigger_fullscan.py
```

#### 4. التحقق من النتائج
```bash
python3 check_db_counts.py
```

---

## 📊 مراقبة النظام

### 1. فحص صحة الـ Spaces
```bash
python3 -c "
from app.multi_space_manager import get_manager

manager = get_manager()
manager.register_spaces_from_config()
stats = manager.get_statistics()

print('Total Spaces:', stats['total_spaces'])
print('Healthy Spaces:', stats['healthy_spaces'])
"
```

### 2. فحص قواعد البيانات
```bash
python3 -c "
from app.multi_dataset_manager import get_manager

manager = get_manager()
manager.register_datasets_from_config()
stats = manager.get_statistics()

print('Total Datasets:', stats['total_datasets'])
print('Synced Datasets:', stats['synced_datasets'])
"
```

### 3. اختبار Load Balancing
```bash
python3 test_distributed_system.py
```

---

## 🎯 الخطوات التالية

### 1. بعد النشر الناجح
- ✅ تحديث URLs في التطبيق
- ✅ اختبار جميع الخدمات
- ✅ مراقبة الأداء
- ✅ إعداد النسخ الاحتياطي التلقائي

### 2. التحسينات المستقبلية
- 🔄 إضافة CDN للصور
- 🔄 تحسين الكاش
- 🔄 إضافة المزيد من Mirrors
- 🔄 تحسين Load Balancing

---

## 🆘 حل المشاكل الشائعة

### مشكلة: "HF_TOKEN not found"
**الحل:**
```bash
# تأكد من وجود .env
ls -la .env

# تحميل المتغيرات
export $(cat .env | grep -v '^#' | xargs)

# التحقق
echo $HF_TOKEN
```

### مشكلة: "Repository already exists"
**الحل:**
```bash
# هذا طبيعي - السكريبت سيستخدم الـ repo الموجود
# لا حاجة لفعل شيء
```

### مشكلة: "Peer id invalid" في Telegram
**الحل:**
```bash
# 1. تأكد من أن البوت في المجموعة
# 2. أعط البوت صلاحيات Admin
# 3. شغل السكريبت التشخيصي
python3 fix_telegram_sync.py
```

### مشكلة: "Rate limit exceeded"
**الحل:**
```bash
# انتظر 5 دقائق ثم حاول مرة أخرى
# HuggingFace لديه حدود على عدد الطلبات
```

---

## 📝 ملاحظات مهمة

1. **الـ Tokens حساسة** - لا تشاركها أبداً
2. **النسخ الاحتياطي** - احتفظ بنسخة من قاعدة البيانات
3. **المراقبة** - راقب الأداء بانتظام
4. **التحديثات** - حدث الكود بانتظام

---

## 🎉 النجاح!

عند اكتمال النشر بنجاح، ستحصل على:
- ✅ 4 Spaces تعمل
- ✅ 6 Datasets متزامنة
- ✅ Load Balancing نشط
- ✅ Failover تلقائي
- ✅ مراقبة شاملة

**الخطوة التالية**: اختبر التطبيق وتأكد من عمل جميع الميزات!

---

## 📞 الدعم

إذا واجهت أي مشاكل:
1. راجع هذا الدليل
2. تحقق من السجلات (logs)
3. شغل السكريبتات التشخيصية
4. راجع IMPLEMENTATION_LOG.md

**تم إنشاء هذا الدليل بواسطة**: Bob (AI Software Engineer)  
**التاريخ**: 2026-05-09  
**الإصدار**: 1.0