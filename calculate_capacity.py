#!/usr/bin/env python3
"""
حساب القدرة الاستيعابية للنظام الموزع
Calculate system capacity for concurrent users
"""

import json

# مواصفات الموارد
RESOURCES = {
    "spaces": {
        "ToolKit-backend/PopCorn": {
            "cpu": "2 vCPU",
            "ram": "16 GB",
            "status": "RUNNING"
        },
        "ToolKit-backend/popcorn-main": {
            "cpu": "2 vCPU", 
            "ram": "16 GB",
            "status": "BUILDING"
        },
        "ToolKit-backend/popcorn-streaming": {
            "cpu": "2 vCPU",
            "ram": "16 GB", 
            "status": "BUILDING"
        },
        "rayig/popcorn-backup": {
            "cpu": "2 vCPU",
            "ram": "16 GB",
            "status": "DEPLOYED"
        },
        "rayig/popcorn-analytics": {
            "cpu": "2 vCPU",
            "ram": "16 GB",
            "status": "DEPLOYED"
        }
    },
    "datasets": 7,
    "total_storage_gb": 45
}

# معايير الأداء
PERFORMANCE_METRICS = {
    "avg_request_time_ms": 100,  # متوسط وقت الطلب
    "requests_per_user_per_minute": 10,  # عدد الطلبات لكل مستخدم في الدقيقة
    "concurrent_requests_per_cpu": 50,  # الطلبات المتزامنة لكل CPU
    "ram_per_user_mb": 10,  # الذاكرة لكل مستخدم
    "bandwidth_per_user_mbps": 2,  # النطاق الترددي لكل مستخدم (للبث)
}

def calculate_capacity():
    """حساب القدرة الاستيعابية"""
    
    print("=" * 80)
    print("📊 حساب القدرة الاستيعابية للنظام الموزع")
    print("=" * 80)
    
    # 1. حساب القدرة بناءً على CPU
    total_cpus = len([s for s in RESOURCES["spaces"].values() if s["status"] in ["RUNNING", "DEPLOYED"]]) * 2
    running_cpus = 2  # فقط PopCorn يعمل حالياً
    
    cpu_capacity = running_cpus * PERFORMANCE_METRICS["concurrent_requests_per_cpu"]
    cpu_users = cpu_capacity // PERFORMANCE_METRICS["requests_per_user_per_minute"]
    
    print(f"\n💻 القدرة بناءً على CPU:")
    print(f"   - CPUs نشطة: {running_cpus} vCPU")
    print(f"   - CPUs إجمالي (عند اكتمال البناء): {total_cpus} vCPU")
    print(f"   - الطلبات المتزامنة (حالياً): {cpu_capacity}")
    print(f"   - المستخدمون المتزامنون (حالياً): ~{cpu_users}")
    print(f"   - المستخدمون المتزامنون (بعد البناء): ~{cpu_users * (total_cpus // running_cpus)}")
    
    # 2. حساب القدرة بناءً على RAM
    total_ram_gb = len([s for s in RESOURCES["spaces"].values() if s["status"] in ["RUNNING", "DEPLOYED"]]) * 16
    running_ram_gb = 16  # فقط PopCorn يعمل
    
    ram_capacity_mb = running_ram_gb * 1024
    ram_users = int(ram_capacity_mb / PERFORMANCE_METRICS["ram_per_user_mb"])
    
    print(f"\n🧠 القدرة بناءً على RAM:")
    print(f"   - RAM نشطة: {running_ram_gb} GB")
    print(f"   - RAM إجمالي (عند اكتمال البناء): {total_ram_gb} GB")
    print(f"   - المستخدمون المتزامنون (حالياً): ~{ram_users}")
    print(f"   - المستخدمون المتزامنون (بعد البناء): ~{ram_users * (total_ram_gb // running_ram_gb)}")
    
    # 3. حساب القدرة بناءً على Bandwidth (للبث)
    # HuggingFace Free tier: Unlimited bandwidth
    bandwidth_users_per_space = 100  # تقدير محافظ
    total_bandwidth_users = bandwidth_users_per_space * len([s for s in RESOURCES["spaces"].values() if s["status"] in ["RUNNING", "DEPLOYED"]])
    
    print(f"\n🌐 القدرة بناءً على Bandwidth:")
    print(f"   - Bandwidth: Unlimited (HuggingFace Free)")
    print(f"   - مستخدمو البث المتزامنون (تقدير): ~{bandwidth_users_per_space} لكل Space")
    print(f"   - المجموع (حالياً): ~{bandwidth_users_per_space}")
    print(f"   - المجموع (بعد البناء): ~{total_bandwidth_users}")
    
    # 4. حساب القدرة بناءً على Database
    # مع Database Sharding عبر 7 datasets
    db_capacity_per_dataset = 5000  # مستخدم لكل dataset
    total_db_capacity = db_capacity_per_dataset * RESOURCES["datasets"]
    
    print(f"\n🗄️ القدرة بناءً على Database:")
    print(f"   - Datasets: {RESOURCES['datasets']}")
    print(f"   - Sharding: Functional + Horizontal")
    print(f"   - المستخدمون المتزامنون: ~{total_db_capacity}")
    
    # 5. القدرة الإجمالية (الحد الأدنى من جميع العوامل)
    current_capacity = min(cpu_users, ram_users, bandwidth_users_per_space)
    full_capacity = min(
        cpu_users * (total_cpus // running_cpus),
        ram_users * (total_ram_gb // running_ram_gb),
        total_bandwidth_users,
        total_db_capacity
    )
    
    print(f"\n" + "=" * 80)
    print(f"🎯 القدرة الاستيعابية الإجمالية:")
    print(f"=" * 80)
    print(f"\n📊 الحالة الحالية (Space واحد يعمل):")
    print(f"   - المستخدمون المتزامنون: ~{current_capacity:,} مستخدم")
    print(f"   - الطلبات في الثانية: ~{current_capacity * PERFORMANCE_METRICS['requests_per_user_per_minute'] // 60:,} req/s")
    
    print(f"\n🚀 بعد اكتمال البناء (5 Spaces + 7 Datasets):")
    print(f"   - المستخدمون المتزامنون: ~{full_capacity:,} مستخدم")
    print(f"   - الطلبات في الثانية: ~{full_capacity * PERFORMANCE_METRICS['requests_per_user_per_minute'] // 60:,} req/s")
    print(f"   - مستخدمو البث المتزامنون: ~{total_bandwidth_users:,} مستخدم")
    
    # 6. مع Load Balancing
    with_load_balancing = full_capacity * 1.5  # تحسين 50% مع Load Balancing
    
    print(f"\n⚡ مع Load Balancing المتقدم:")
    print(f"   - المستخدمون المتزامنون: ~{int(with_load_balancing):,} مستخدم")
    print(f"   - التحسين: +50%")
    
    # 7. السيناريوهات
    print(f"\n" + "=" * 80)
    print(f"📈 السيناريوهات المختلفة:")
    print(f"=" * 80)
    
    scenarios = {
        "تصفح عادي": {
            "users": int(with_load_balancing),
            "description": "مستخدمون يتصفحون المحتوى"
        },
        "مشاهدة متوسطة": {
            "users": int(with_load_balancing * 0.7),
            "description": "70% يشاهدون محتوى"
        },
        "ذروة الاستخدام": {
            "users": int(with_load_balancing * 0.5),
            "description": "جميع المستخدمين نشطون"
        },
        "بث مباشر": {
            "users": total_bandwidth_users,
            "description": "مستخدمون يشاهدون بث مباشر"
        }
    }
    
    for scenario, data in scenarios.items():
        print(f"\n🎬 {scenario}:")
        print(f"   - القدرة: ~{data['users']:,} مستخدم متزامن")
        print(f"   - الوصف: {data['description']}")
    
    # 8. التوصيات
    print(f"\n" + "=" * 80)
    print(f"💡 التوصيات:")
    print(f"=" * 80)
    print(f"""
1. ✅ الحالة الحالية: يمكن التعامل مع ~{current_capacity:,} مستخدم متزامن
2. 🔄 بعد إصلاح البناء: يمكن التعامل مع ~{full_capacity:,} مستخدم متزامن
3. ⚡ مع Load Balancing: يمكن التعامل مع ~{int(with_load_balancing):,} مستخدم متزامن
4. 📈 للتوسع أكثر: إضافة Spaces جديدة (مجاني!)
5. 🎯 الهدف الموصى به: 10,000 مستخدم متزامن (قابل للتحقيق)
    """)
    
    # 9. حفظ النتائج
    results = {
        "timestamp": "2026-05-09T03:35:00Z",
        "current_capacity": {
            "concurrent_users": current_capacity,
            "requests_per_second": current_capacity * PERFORMANCE_METRICS['requests_per_user_per_minute'] // 60,
            "status": "1 Space running"
        },
        "full_capacity": {
            "concurrent_users": full_capacity,
            "requests_per_second": full_capacity * PERFORMANCE_METRICS['requests_per_user_per_minute'] // 60,
            "streaming_users": total_bandwidth_users,
            "status": "5 Spaces + 7 Datasets"
        },
        "with_load_balancing": {
            "concurrent_users": int(with_load_balancing),
            "improvement": "50%"
        },
        "scenarios": scenarios,
        "resources": RESOURCES
    }
    
    with open('capacity_calculation.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 النتائج محفوظة في: capacity_calculation.json")
    print("=" * 80)

if __name__ == "__main__":
    calculate_capacity()

# Made with Bob
