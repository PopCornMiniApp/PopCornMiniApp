#!/usr/bin/env python3
import sqlite3
import os
import time
from datetime import datetime

print("🔍 تشخيص مشكلة المزامنة\n")
print("="*60)

# 1. فحص قاعدة البيانات المحلية
local_db = "/tmp/popcorn.db"
if os.path.exists(local_db):
    age_hours = (time.time() - os.path.getmtime(local_db)) / 3600
    print(f"\n📁 قاعدة البيانات المحلية:")
    print(f"   - الموقع: {local_db}")
    print(f"   - العمر: {age_hours:.1f} ساعة")
    print(f"   - آخر تعديل: {datetime.fromtimestamp(os.path.getmtime(local_db))}")
    print(f"   - الحجم: {os.path.getsize(local_db) / 1024:.1f} KB")
    
    conn = sqlite3.connect(local_db)
    cursor = conn.cursor()
    
    # عدد الأفلام
    movies = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    print(f"   - عدد الأفلام: {movies}")
    
    # عدد الأفلام مع ملفات
    with_files = cursor.execute("SELECT COUNT(*) FROM movies WHERE file_id IS NOT NULL").fetchone()[0]
    print(f"   - أفلام مع ملفات: {with_files}")
    
    # Check schema first
    schema = cursor.execute("PRAGMA table_info(movies)").fetchall()
    columns = [col[1] for col in schema]
    print(f"   - الأعمدة: {', '.join(columns)}")
    
    # Use correct ID column
    id_col = 'id' if 'id' in columns else 'movie_id'
    
    # آخر فيلم مسجل
    last = cursor.execute(f"SELECT {id_col}, title FROM movies ORDER BY {id_col} DESC LIMIT 1").fetchone()
    if last:
        print(f"   - آخر فيلم: {last[0]} - {last[1]}")
    
    # أول 5 أفلام
    print(f"\n   📋 أول 5 أفلام:")
    first_five = cursor.execute(f"SELECT {id_col}, title FROM movies ORDER BY {id_col} LIMIT 5").fetchall()
    for movie_id, title in first_five:
        print(f"      {movie_id}: {title}")
    
    # آخر 5 أفلام
    print(f"\n   📋 آخر 5 أفلام:")
    last_five = cursor.execute(f"SELECT {id_col}, title FROM movies ORDER BY {id_col} DESC LIMIT 5").fetchall()
    for movie_id, title in last_five:
        print(f"      {movie_id}: {title}")
    
    conn.close()
else:
    print("❌ قاعدة البيانات المحلية غير موجودة!")
    movies = 0

print("\n" + "="*60)

# 2. فحص HuggingFace Dataset
print("\n🌐 فحص HuggingFace Dataset:")
try:
    from huggingface_hub import hf_hub_download
    
    # Get token from environment
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("   ⚠️ تحذير: HF_TOKEN غير موجود في المتغيرات البيئية")
        print("   سيتم محاولة التنزيل بدون token...")
    
    print("   - جاري التنزيل من HuggingFace...")
    db_path = hf_hub_download(
        repo_id="ToolKit-backend/PopCornDB",
        filename="popcorn.db",
        repo_type="dataset",
        token=hf_token,
        force_download=True
    )
    
    print(f"   - تم التنزيل إلى: {db_path}")
    print(f"   - الحجم: {os.path.getsize(db_path) / 1024:.1f} KB")
    
    # فحص المحتوى
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    hf_count = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    print(f"   - عدد الأفلام في HuggingFace: {hf_count}")
    
    # Check schema
    schema = cursor.execute("PRAGMA table_info(movies)").fetchall()
    columns = [col[1] for col in schema]
    id_col = 'id' if 'id' in columns else 'movie_id'
    
    # آخر فيلم في HuggingFace
    last_hf = cursor.execute(f"SELECT {id_col}, title FROM movies ORDER BY {id_col} DESC LIMIT 1").fetchone()
    if last_hf:
        print(f"   - آخر فيلم في HuggingFace: {last_hf[0]} - {last_hf[1]}")
    
    conn.close()
    
except Exception as e:
    print(f"   ❌ خطأ في الاتصال بـ HuggingFace: {e}")
    hf_count = None

print("\n" + "="*60)

# 3. تحليل المشكلة
print("\n🔍 التحليل:")
if movies == 22:
    print("❌ المشكلة المؤكدة: قاعدة البيانات تحتوي على 22 فيلم فقط")
    print("\n   السبب المحتمل:")
    print("   1. تم تنزيل نسخة قديمة من HuggingFace")
    print("   2. فشل رفع النسخة الجديدة (32 فيلم)")
    print("   3. مشكلة في منطق init_db()")
    
    if hf_count:
        if hf_count == 22:
            print(f"\n   ⚠️ HuggingFace أيضاً يحتوي على {hf_count} فيلم")
            print("   المشكلة: لم يتم رفع النسخة الجديدة إلى HuggingFace")
        elif hf_count == 32:
            print(f"\n   ✅ HuggingFace يحتوي على {hf_count} فيلم")
            print("   المشكلة: init_db() لم يقم بتنزيل النسخة الصحيحة")
        else:
            print(f"\n   ⚠️ HuggingFace يحتوي على {hf_count} فيلم (عدد غير متوقع)")
            
elif movies == 32:
    print("✅ قاعدة البيانات المحلية تحتوي على 32 فيلم")
    print("   المشكلة قد تكون في Frontend أو API")
    
    if hf_count and hf_count != 32:
        print(f"\n   ⚠️ لكن HuggingFace يحتوي على {hf_count} فيلم")
        print("   يجب رفع النسخة المحلية إلى HuggingFace")
else:
    print(f"⚠️ عدد غير متوقع: {movies} فيلم")
    if hf_count:
        print(f"   HuggingFace يحتوي على: {hf_count} فيلم")

print("\n" + "="*60)

# 4. الحل المقترح
print("\n💡 الحل المقترح:")
if movies < 32:
    print("   1. حذف قاعدة البيانات المحلية")
    print("   2. تشغيل Full Scan للحصول على جميع الأفلام")
    print("   3. رفع النتيجة إلى HuggingFace")
    print("   4. تحديث منطق init_db() لتفضيل القاعدة المحلية الحديثة")
elif hf_count and hf_count < movies:
    print("   1. رفع قاعدة البيانات المحلية إلى HuggingFace")
    print("   2. التحقق من نجاح الرفع")
else:
    print("   1. التحقق من API endpoints")
    print("   2. فحص Frontend للتأكد من عرض جميع الأفلام")

print("\n" + "="*60)
print("\n✅ انتهى التشخيص")

# Made with Bob
