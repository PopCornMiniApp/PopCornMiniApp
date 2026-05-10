#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محلل القدرة الاستيعابية لـ HuggingFace Spaces
HuggingFace Spaces Capacity Analyzer

يحلل:
- مواصفات العتاد المجاني
- حدود الـ bandwidth
- قيود الـ concurrent connections
- حساب العدد الأقصى النظري للمشاهدين
- توصيات للتحسين
"""

import json
import psutil
import platform
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
import math


@dataclass
class HardwareSpecs:
    """مواصفات العتاد"""
    cpu_cores: int
    cpu_freq_mhz: float
    total_ram_gb: float
    available_ram_gb: float
    total_disk_gb: float
    available_disk_gb: float
    platform: str
    architecture: str


@dataclass
class HuggingFaceSpecs:
    """مواصفات HuggingFace Spaces المجانية"""
    # المواصفات المعروفة للخطة المجانية
    cpu_cores: int = 2
    ram_gb: float = 16.0
    disk_gb: float = 50.0
    bandwidth_limit_gb_month: float = 100.0  # تقديري
    max_concurrent_connections: int = 100  # تقديري
    max_request_size_mb: float = 10.0
    timeout_seconds: int = 60
    
    # قيود إضافية
    max_websocket_connections: int = 50
    max_file_size_mb: float = 100.0
    rate_limit_per_minute: int = 60


@dataclass
class StreamingRequirements:
    """متطلبات البث"""
    video_bitrate_kbps: float = 2500  # 2.5 Mbps for HD
    audio_bitrate_kbps: float = 128
    overhead_percent: float = 20  # Protocol overhead
    
    @property
    def total_bitrate_kbps(self) -> float:
        """إجمالي معدل البت مع الـ overhead"""
        base = self.video_bitrate_kbps + self.audio_bitrate_kbps
        return base * (1 + self.overhead_percent / 100)
    
    @property
    def bandwidth_per_viewer_mbps(self) -> float:
        """استهلاك bandwidth لكل مشاهد (Mbps)"""
        return self.total_bitrate_kbps / 1000


@dataclass
class CapacityEstimate:
    """تقدير القدرة الاستيعابية"""
    max_concurrent_viewers: int
    max_concurrent_streams: int
    max_rooms: int
    max_users_per_room: int
    bandwidth_limited_viewers: int
    cpu_limited_viewers: int
    ram_limited_viewers: int
    connection_limited_viewers: int
    bottleneck: str
    confidence_level: str


@dataclass
class CapacityReport:
    """تقرير القدرة الاستيعابية الشامل"""
    hardware_specs: HardwareSpecs
    hf_specs: HuggingFaceSpecs
    streaming_requirements: StreamingRequirements
    capacity_estimate: CapacityEstimate
    recommendations: List[str]
    optimizations: List[str]
    warnings: List[str]
    timestamp: str


class HFCapacityAnalyzer:
    """محلل القدرة الاستيعابية لـ HuggingFace"""
    
    def __init__(self):
        self.current_hardware = self._get_current_hardware()
        self.hf_specs = HuggingFaceSpecs()
        self.streaming_reqs = StreamingRequirements()
    
    def _get_current_hardware(self) -> HardwareSpecs:
        """الحصول على مواصفات العتاد الحالي"""
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return HardwareSpecs(
            cpu_cores=psutil.cpu_count(logical=False) or psutil.cpu_count(),
            cpu_freq_mhz=cpu_freq.current if cpu_freq else 0,
            total_ram_gb=memory.total / (1024**3),
            available_ram_gb=memory.available / (1024**3),
            total_disk_gb=disk.total / (1024**3),
            available_disk_gb=disk.free / (1024**3),
            platform=platform.system(),
            architecture=platform.machine()
        )
    
    def calculate_bandwidth_capacity(self) -> int:
        """حساب القدرة بناءً على bandwidth"""
        # تحويل الحد الشهري إلى معدل في الثانية
        monthly_gb = self.hf_specs.bandwidth_limit_gb_month
        seconds_per_month = 30 * 24 * 60 * 60
        
        # معدل البيانات المتاح في الثانية (Mbps)
        available_mbps = (monthly_gb * 1024 * 8) / seconds_per_month
        
        # عدد المشاهدين بناءً على bandwidth
        viewers = int(available_mbps / self.streaming_reqs.bandwidth_per_viewer_mbps)
        
        return max(1, viewers)
    
    def calculate_cpu_capacity(self) -> int:
        """حساب القدرة بناءً على CPU"""
        # تقدير: كل core يمكنه خدمة 10-15 مشاهد متزامن
        # مع الأخذ في الاعتبار معالجة الطلبات والبث
        viewers_per_core = 12
        
        # استخدام 80% من الـ cores للبث، 20% للنظام
        usable_cores = self.hf_specs.cpu_cores * 0.8
        
        viewers = int(usable_cores * viewers_per_core)
        
        return max(1, viewers)
    
    def calculate_ram_capacity(self) -> int:
        """حساب القدرة بناءً على RAM"""
        # تقدير استهلاك الذاكرة:
        # - نظام التشغيل والتطبيق: 2 GB
        # - قاعدة البيانات والكاش: 2 GB
        # - كل مشاهد: ~50 MB (اتصال، buffer، session)
        
        system_overhead_gb = 4.0
        available_ram = self.hf_specs.ram_gb - system_overhead_gb
        
        ram_per_viewer_mb = 50
        viewers = int((available_ram * 1024) / ram_per_viewer_mb)
        
        return max(1, viewers)
    
    def calculate_connection_capacity(self) -> int:
        """حساب القدرة بناءً على عدد الاتصالات"""
        # كل مشاهد يحتاج:
        # - 1 HTTP connection للبيانات
        # - 1 WebSocket للتحديثات الفورية
        # - 1 streaming connection
        
        connections_per_viewer = 3
        max_viewers = self.hf_specs.max_concurrent_connections // connections_per_viewer
        
        return max(1, max_viewers)
    
    def calculate_bot_capacity(self, num_bots: int = 10) -> Dict[str, int]:
        """حساب القدرة بناءً على عدد البوتات"""
        # كل بوت يمكنه خدمة عدد معين من المشاهدين
        # بناءً على قيود Telegram
        
        # قيود Telegram Bot API:
        # - حد معدل الطلبات: 30 msg/sec per bot
        # - حد حجم الملف: 2 GB
        # - حد عدد الاتصالات المتزامنة: ~100 per bot
        
        viewers_per_bot = 100
        total_capacity = num_bots * viewers_per_bot
        
        return {
            'total_capacity': total_capacity,
            'viewers_per_bot': viewers_per_bot,
            'num_bots': num_bots,
            'failover_capacity': (num_bots - 1) * viewers_per_bot  # مع فشل بوت واحد
        }
    
    def calculate_room_capacity(self) -> Dict[str, int]:
        """حساب قدرة غرف المشاهدة الجماعية"""
        # قيود غرف المشاهدة:
        # - كل غرفة تحتاج WebSocket connections
        # - كل غرفة تحتاج معالجة رسائل فورية
        # - كل غرفة تحتاج مزامنة
        
        max_websocket = self.hf_specs.max_websocket_connections
        
        # تخصيص 70% للغرف، 30% لاستخدامات أخرى
        available_for_rooms = int(max_websocket * 0.7)
        
        # سيناريوهات مختلفة
        scenarios = {
            'small_rooms': {
                'users_per_room': 5,
                'max_rooms': available_for_rooms // 5,
                'total_users': available_for_rooms
            },
            'medium_rooms': {
                'users_per_room': 10,
                'max_rooms': available_for_rooms // 10,
                'total_users': available_for_rooms
            },
            'large_rooms': {
                'users_per_room': 20,
                'max_rooms': available_for_rooms // 20,
                'total_users': available_for_rooms
            }
        }
        
        return scenarios
    
    def estimate_capacity(self) -> CapacityEstimate:
        """تقدير القدرة الاستيعابية الشاملة"""
        # حساب القدرة من جميع الجوانب
        bandwidth_viewers = self.calculate_bandwidth_capacity()
        cpu_viewers = self.calculate_cpu_capacity()
        ram_viewers = self.calculate_ram_capacity()
        connection_viewers = self.calculate_connection_capacity()
        
        # تحديد العنق الزجاجة
        capacities = {
            'bandwidth': bandwidth_viewers,
            'cpu': cpu_viewers,
            'ram': ram_viewers,
            'connections': connection_viewers
        }
        
        bottleneck = min(capacities, key=capacities.get)
        max_viewers = capacities[bottleneck]
        
        # حساب قدرة البوتات
        bot_capacity = self.calculate_bot_capacity()
        
        # حساب قدرة الغرف
        room_capacity = self.calculate_room_capacity()
        
        # تحديد مستوى الثقة
        if max_viewers < 50:
            confidence = "منخفض - يحتاج تحسين"
        elif max_viewers < 100:
            confidence = "متوسط - مقبول للاستخدام الخفيف"
        elif max_viewers < 200:
            confidence = "جيد - مناسب للاستخدام المتوسط"
        else:
            confidence = "عالي - مناسب للاستخدام الكثيف"
        
        return CapacityEstimate(
            max_concurrent_viewers=max_viewers,
            max_concurrent_streams=min(10, max_viewers // 10),  # 10 بوتات كحد أقصى
            max_rooms=room_capacity['medium_rooms']['max_rooms'],
            max_users_per_room=room_capacity['medium_rooms']['users_per_room'],
            bandwidth_limited_viewers=bandwidth_viewers,
            cpu_limited_viewers=cpu_viewers,
            ram_limited_viewers=ram_viewers,
            connection_limited_viewers=connection_viewers,
            bottleneck=bottleneck,
            confidence_level=confidence
        )
    
    def generate_recommendations(self, estimate: CapacityEstimate) -> List[str]:
        """توليد توصيات للتحسين"""
        recommendations = []
        
        # توصيات بناءً على العنق الزجاجة
        if estimate.bottleneck == 'bandwidth':
            recommendations.extend([
                "🌐 Bandwidth هو العنق الزجاجة الرئيسي",
                "💡 استخدم adaptive bitrate streaming لتقليل استهلاك bandwidth",
                "💡 قم بضغط الفيديو بشكل أفضل (H.265 بدلاً من H.264)",
                "💡 استخدم CDN لتوزيع الحمل",
                "💡 قلل جودة البث للمستخدمين ذوي الاتصال البطيء",
                "💡 استخدم P2P streaming لتقليل الحمل على السيرفر"
            ])
        
        elif estimate.bottleneck == 'cpu':
            recommendations.extend([
                "⚙️ CPU هو العنق الزجاجة الرئيسي",
                "💡 استخدم hardware acceleration للترميز",
                "💡 قم بتحسين الكود وتقليل العمليات الحسابية",
                "💡 استخدم caching بشكل مكثف",
                "💡 انقل المعالجة الثقيلة إلى background workers",
                "💡 استخدم async/await بشكل صحيح"
            ])
        
        elif estimate.bottleneck == 'ram':
            recommendations.extend([
                "💾 RAM هو العنق الزجاجة الرئيسي",
                "💡 قلل حجم الـ buffers والـ cache",
                "💡 استخدم streaming بدلاً من تحميل الملفات كاملة",
                "💡 قم بتنظيف الذاكرة بشكل دوري",
                "💡 استخدم database connection pooling",
                "💡 قلل عدد الـ sessions المحفوظة في الذاكرة"
            ])
        
        elif estimate.bottleneck == 'connections':
            recommendations.extend([
                "🔌 عدد الاتصالات هو العنق الزجاجة الرئيسي",
                "💡 استخدم connection pooling",
                "💡 قلل عدد الاتصالات لكل مستخدم",
                "💡 استخدم HTTP/2 أو HTTP/3",
                "💡 قم بإغلاق الاتصالات غير النشطة",
                "💡 استخدم load balancing"
            ])
        
        # توصيات عامة
        recommendations.extend([
            "\n📊 توصيات عامة:",
            "✅ استخدم Redis للكاش الموزع",
            "✅ قم بتحسين استعلامات قاعدة البيانات",
            "✅ استخدم rate limiting لحماية النظام",
            "✅ راقب الأداء بشكل مستمر",
            "✅ قم بإجراء اختبارات ضغط دورية",
            "✅ استخدم auto-scaling إذا أمكن",
            "✅ قم بتوزيع الحمل على عدة خوادم"
        ])
        
        return recommendations
    
    def generate_optimizations(self, estimate: CapacityEstimate) -> List[str]:
        """توليد تحسينات محددة"""
        optimizations = []
        
        # تحسينات البث
        optimizations.extend([
            "🎬 تحسينات البث:",
            "- استخدم HLS أو DASH للبث التكيفي",
            "- قم بإنشاء عدة جودات للفيديو (360p, 480p, 720p, 1080p)",
            "- استخدم segment caching للأجزاء المشاهدة بكثرة",
            "- قم بـ pre-loading للأجزاء القادمة",
            "- استخدم thumbnail previews بدلاً من تحميل الفيديو كاملاً"
        ])
        
        # تحسينات قاعدة البيانات
        optimizations.extend([
            "\n💾 تحسينات قاعدة البيانات:",
            "- أضف indexes على الأعمدة المستخدمة في البحث",
            "- استخدم prepared statements",
            "- قم بـ batch operations بدلاً من عمليات فردية",
            "- استخدم read replicas للقراءة",
            "- قم بأرشفة البيانات القديمة"
        ])
        
        # تحسينات الشبكة
        optimizations.extend([
            "\n🌐 تحسينات الشبكة:",
            "- استخدم gzip compression للـ API responses",
            "- قم بتفعيل HTTP caching headers",
            "- استخدم WebSocket بدلاً من polling",
            "- قلل حجم الـ payloads",
            "- استخدم binary protocols (protobuf) بدلاً من JSON"
        ])
        
        # تحسينات الكود
        optimizations.extend([
            "\n⚡ تحسينات الكود:",
            "- استخدم async/await في جميع العمليات I/O",
            "- قم بـ lazy loading للبيانات",
            "- استخدم generators بدلاً من lists للبيانات الكبيرة",
            "- قم بتحسين الـ algorithms المستخدمة",
            "- استخدم profiling لتحديد الـ bottlenecks"
        ])
        
        return optimizations
    
    def generate_warnings(self, estimate: CapacityEstimate) -> List[str]:
        """توليد تحذيرات"""
        warnings = []
        
        if estimate.max_concurrent_viewers < 50:
            warnings.append("⚠️ القدرة الاستيعابية منخفضة جداً (<50 مشاهد)")
        
        if estimate.max_concurrent_viewers < 100:
            warnings.append("⚠️ القدرة الاستيعابية محدودة (<100 مشاهد)")
        
        if estimate.bottleneck == 'bandwidth':
            warnings.append("⚠️ Bandwidth محدود - قد يؤثر على جودة البث")
        
        if estimate.max_rooms < 5:
            warnings.append("⚠️ عدد الغرف المتاحة محدود جداً")
        
        if estimate.max_users_per_room < 10:
            warnings.append("⚠️ عدد المستخدمين لكل غرفة محدود")
        
        # تحذيرات HuggingFace Spaces
        warnings.extend([
            "\n⚠️ قيود HuggingFace Spaces المجانية:",
            "- قد يتم إيقاف التطبيق بعد فترة من عدم النشاط",
            "- لا يوجد ضمان للـ uptime",
            "- قد تكون هناك قيود على الـ bandwidth غير موثقة",
            "- الأداء قد يتأثر بالاستخدام الكثيف",
            "- يُنصح بالترقية للخطة المدفوعة للاستخدام الإنتاجي"
        ])
        
        return warnings
    
    def analyze(self) -> CapacityReport:
        """تحليل شامل للقدرة الاستيعابية"""
        print("\n" + "="*60)
        print("🔍 تحليل القدرة الاستيعابية لـ HuggingFace Spaces")
        print("="*60 + "\n")
        
        # تقدير القدرة
        estimate = self.estimate_capacity()
        
        # توليد التوصيات
        recommendations = self.generate_recommendations(estimate)
        optimizations = self.generate_optimizations(estimate)
        warnings = self.generate_warnings(estimate)
        
        # إنشاء التقرير
        report = CapacityReport(
            hardware_specs=self.current_hardware,
            hf_specs=self.hf_specs,
            streaming_requirements=self.streaming_reqs,
            capacity_estimate=estimate,
            recommendations=recommendations,
            optimizations=optimizations,
            warnings=warnings,
            timestamp=datetime.now().isoformat()
        )
        
        # عرض النتائج
        self._print_report(report)
        
        return report
    
    def _print_report(self, report: CapacityReport):
        """عرض التقرير"""
        est = report.capacity_estimate
        
        print("📊 نتائج التحليل:")
        print(f"\n🎯 القدرة الاستيعابية المقدرة:")
        print(f"   • الحد الأقصى للمشاهدين المتزامنين: {est.max_concurrent_viewers}")
        print(f"   • الحد الأقصى للبث المتزامن: {est.max_concurrent_streams}")
        print(f"   • الحد الأقصى للغرف: {est.max_rooms}")
        print(f"   • الحد الأقصى للمستخدمين لكل غرفة: {est.max_users_per_room}")
        
        print(f"\n🔍 تحليل العنق الزجاجة:")
        print(f"   • العنق الزجاجة الرئيسي: {est.bottleneck.upper()}")
        print(f"   • محدود بـ Bandwidth: {est.bandwidth_limited_viewers} مشاهد")
        print(f"   • محدود بـ CPU: {est.cpu_limited_viewers} مشاهد")
        print(f"   • محدود بـ RAM: {est.ram_limited_viewers} مشاهد")
        print(f"   • محدود بـ Connections: {est.connection_limited_viewers} مشاهد")
        
        print(f"\n📈 مستوى الثقة: {est.confidence_level}")
        
        print("\n" + "="*60)
    
    def save_report(self, report: CapacityReport, filename: str = "capacity_report.json"):
        """حفظ التقرير"""
        report_dict = {
            'hardware_specs': asdict(report.hardware_specs),
            'hf_specs': asdict(report.hf_specs),
            'streaming_requirements': asdict(report.streaming_requirements),
            'capacity_estimate': asdict(report.capacity_estimate),
            'recommendations': report.recommendations,
            'optimizations': report.optimizations,
            'warnings': report.warnings,
            'timestamp': report.timestamp
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 تم حفظ التقرير في: {filename}")
    
    def generate_markdown_report(self, report: CapacityReport, filename: str = "capacity_report.md"):
        """توليد تقرير بصيغة Markdown"""
        est = report.capacity_estimate
        
        md_content = f"""# تقرير القدرة الاستيعابية لـ PopCorn على HuggingFace Spaces

**تاريخ التحليل:** {report.timestamp}

## 📊 ملخص تنفيذي

### القدرة الاستيعابية المقدرة

| المقياس | القيمة |
|---------|--------|
| الحد الأقصى للمشاهدين المتزامنين | **{est.max_concurrent_viewers}** |
| الحد الأقصى للبث المتزامن | **{est.max_concurrent_streams}** |
| الحد الأقصى للغرف | **{est.max_rooms}** |
| الحد الأقصى للمستخدمين لكل غرفة | **{est.max_users_per_room}** |

### العنق الزجاجة الرئيسي

**{est.bottleneck.upper()}** هو العامل المحدد للقدرة الاستيعابية.

### تحليل القيود

| القيد | عدد المشاهدين المحتمل |
|-------|----------------------|
| Bandwidth | {est.bandwidth_limited_viewers} |
| CPU | {est.cpu_limited_viewers} |
| RAM | {est.ram_limited_viewers} |
| Connections | {est.connection_limited_viewers} |

### مستوى الثقة

**{est.confidence_level}**

---

## 🔧 مواصفات العتاد

### العتاد الحالي

- **CPU Cores:** {report.hardware_specs.cpu_cores}
- **CPU Frequency:** {report.hardware_specs.cpu_freq_mhz:.0f} MHz
- **Total RAM:** {report.hardware_specs.total_ram_gb:.2f} GB
- **Available RAM:** {report.hardware_specs.available_ram_gb:.2f} GB
- **Total Disk:** {report.hardware_specs.total_disk_gb:.2f} GB
- **Available Disk:** {report.hardware_specs.available_disk_gb:.2f} GB
- **Platform:** {report.hardware_specs.platform}
- **Architecture:** {report.hardware_specs.architecture}

### مواصفات HuggingFace Spaces (المجانية)

- **CPU Cores:** {report.hf_specs.cpu_cores}
- **RAM:** {report.hf_specs.ram_gb} GB
- **Disk:** {report.hf_specs.disk_gb} GB
- **Bandwidth Limit:** {report.hf_specs.bandwidth_limit_gb_month} GB/month
- **Max Concurrent Connections:** {report.hf_specs.max_concurrent_connections}
- **Max WebSocket Connections:** {report.hf_specs.max_websocket_connections}

---

## 🎬 متطلبات البث

- **Video Bitrate:** {report.streaming_requirements.video_bitrate_kbps} kbps
- **Audio Bitrate:** {report.streaming_requirements.audio_bitrate_kbps} kbps
- **Total Bitrate (with overhead):** {report.streaming_requirements.total_bitrate_kbps:.0f} kbps
- **Bandwidth per Viewer:** {report.streaming_requirements.bandwidth_per_viewer_mbps:.2f} Mbps

---

## 💡 التوصيات

"""
        
        for rec in report.recommendations:
            md_content += f"{rec}\n"
        
        md_content += "\n---\n\n## ⚡ التحسينات المقترحة\n\n"
        
        for opt in report.optimizations:
            md_content += f"{opt}\n"
        
        md_content += "\n---\n\n## ⚠️ التحذيرات\n\n"
        
        for warn in report.warnings:
            md_content += f"{warn}\n"
        
        md_content += """

---

## 📈 خطة التوسع

### المرحلة 1: التحسين الأولي (0-50 مستخدم)
- تطبيق التحسينات الأساسية
- إضافة caching
- تحسين استعلامات قاعدة البيانات

### المرحلة 2: التوسع المتوسط (50-100 مستخدم)
- إضافة CDN
- تحسين البث
- استخدام Redis للكاش الموزع

### المرحلة 3: التوسع الكبير (100+ مستخدم)
- الترقية للخطة المدفوعة
- استخدام load balancing
- توزيع الحمل على عدة خوادم

---

## 🎯 الخلاصة

بناءً على التحليل، النظام الحالي يمكنه دعم **{est.max_concurrent_viewers} مشاهد متزامن** 
في ظل الظروف المثالية. العنق الزجاجة الرئيسي هو **{est.bottleneck}**.

للحصول على أفضل أداء، يُنصح بتطبيق التحسينات المقترحة والمراقبة المستمرة للنظام.

---

*تم إنشاء هذا التقرير تلقائياً بواسطة HFCapacityAnalyzer*
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"📄 تم حفظ التقرير Markdown في: {filename}")


def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HuggingFace Capacity Analyzer')
    parser.add_argument('--json', default='capacity_report.json', help='JSON output file')
    parser.add_argument('--markdown', default='capacity_report.md', help='Markdown output file')
    
    args = parser.parse_args()
    
    analyzer = HFCapacityAnalyzer()
    report = analyzer.analyze()
    
    # حفظ التقارير
    analyzer.save_report(report, args.json)
    analyzer.generate_markdown_report(report, args.markdown)
    
    # عرض التوصيات
    print("\n" + "="*60)
    print("💡 التوصيات الرئيسية:")
    print("="*60)
    for i, rec in enumerate(report.recommendations[:10], 1):
        print(f"{i}. {rec}")
    
    # عرض التحذيرات
    if report.warnings:
        print("\n" + "="*60)
        print("⚠️ التحذيرات:")
        print("="*60)
        for warn in report.warnings[:5]:
            print(f"   {warn}")


if __name__ == "__main__":
    main()

# Made with Bob
