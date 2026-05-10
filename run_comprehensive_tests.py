#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت تشغيل الاختبارات الشاملة
Comprehensive Test Runner

يقوم بـ:
- تشغيل جميع الاختبارات بالتسلسل
- جمع النتائج في تقرير واحد
- حفظ النتائج في ملف JSON
- توليد تقرير مفصل بالعربية
"""

import asyncio
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

# إضافة مسار التطبيق
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# استيراد الأنظمة
from stress_test_suite import StressTestSuite, StressTestReport
from hf_capacity_analyzer import HFCapacityAnalyzer, CapacityReport
from performance_monitor import PerformanceMonitor


@dataclass
class ComprehensiveTestReport:
    """تقرير شامل لجميع الاختبارات"""
    test_date: str
    total_duration: float
    stress_test_results: Dict[str, Any]
    capacity_analysis: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    overall_status: str
    recommendations: List[str]
    warnings: List[str]
    next_steps: List[str]


class ComprehensiveTestRunner:
    """مشغل الاختبارات الشامل"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.start_time = time.time()
        self.results = {}
    
    async def run_stress_tests(self) -> StressTestReport:
        """تشغيل اختبارات الضغط"""
        print("\n" + "="*70)
        print("🔥 المرحلة 1: اختبارات الضغط (Stress Tests)")
        print("="*70 + "\n")
        
        suite = StressTestSuite(base_url=self.base_url)
        report = await suite.run_all_tests()
        
        # حفظ النتائج
        suite.save_report(report, "stress_test_results.json")
        
        return report
    
    def run_capacity_analysis(self) -> CapacityReport:
        """تشغيل تحليل القدرة الاستيعابية"""
        print("\n" + "="*70)
        print("📊 المرحلة 2: تحليل القدرة الاستيعابية (Capacity Analysis)")
        print("="*70 + "\n")
        
        analyzer = HFCapacityAnalyzer()
        report = analyzer.analyze()
        
        # حفظ النتائج
        analyzer.save_report(report, "capacity_analysis.json")
        analyzer.generate_markdown_report(report, "capacity_analysis.md")
        
        return report
    
    async def run_performance_monitoring(self, duration: int = 60) -> Dict[str, Any]:
        """تشغيل مراقبة الأداء"""
        print("\n" + "="*70)
        print(f"⏱️  المرحلة 3: مراقبة الأداء ({duration} ثانية)")
        print("="*70 + "\n")
        
        monitor = PerformanceMonitor(
            base_url=self.base_url,
            history_size=duration,
            update_interval=1.0
        )
        
        # مراقبة لمدة محددة
        try:
            task = asyncio.create_task(monitor.monitor_loop())
            await asyncio.sleep(duration)
            monitor.running = False
            
            # إلغاء المهمة بشكل آمن
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
        except Exception as e:
            print(f"⚠️ خطأ في المراقبة: {e}")
        
        # حفظ النتائج
        monitor.save_metrics("performance_monitoring.json")
        monitor.generate_report("performance_monitoring.md")
        
        # استخراج الملخص
        summary = {
            'duration': duration,
            'samples_collected': len(monitor.system_history),
            'avg_cpu': sum(m.cpu_percent for m in monitor.system_history) / len(monitor.system_history) if monitor.system_history else 0,
            'avg_memory': sum(m.memory_percent for m in monitor.system_history) / len(monitor.system_history) if monitor.system_history else 0,
            'max_cpu': max((m.cpu_percent for m in monitor.system_history), default=0),
            'max_memory': max((m.memory_percent for m in monitor.system_history), default=0)
        }
        
        return summary
    
    def generate_overall_recommendations(self, 
                                        stress_report: StressTestReport,
                                        capacity_report: CapacityReport,
                                        perf_summary: Dict[str, Any]) -> List[str]:
        """توليد توصيات شاملة"""
        recommendations = []
        
        # تحليل نتائج اختبارات الضغط
        success_rate = (stress_report.passed_tests / stress_report.total_tests * 100) if stress_report.total_tests > 0 else 0
        
        if success_rate < 80:
            recommendations.append("🔴 معدل نجاح الاختبارات منخفض - يحتاج تحسين عاجل")
        elif success_rate < 95:
            recommendations.append("🟡 معدل نجاح الاختبارات مقبول - يمكن تحسينه")
        else:
            recommendations.append("🟢 معدل نجاح الاختبارات ممتاز")
        
        # تحليل القدرة الاستيعابية
        max_viewers = capacity_report.capacity_estimate.max_concurrent_viewers
        
        if max_viewers < 50:
            recommendations.append("🔴 القدرة الاستيعابية منخفضة جداً - يحتاج ترقية")
        elif max_viewers < 100:
            recommendations.append("🟡 القدرة الاستيعابية محدودة - مناسبة للاستخدام الخفيف")
        elif max_viewers < 200:
            recommendations.append("🟢 القدرة الاستيعابية جيدة - مناسبة للاستخدام المتوسط")
        else:
            recommendations.append("🟢 القدرة الاستيعابية ممتازة - مناسبة للاستخدام الكثيف")
        
        # تحليل الأداء
        if perf_summary['avg_cpu'] > 70:
            recommendations.append("⚠️ استهلاك CPU مرتفع - قم بتحسين الكود")
        if perf_summary['avg_memory'] > 80:
            recommendations.append("⚠️ استهلاك الذاكرة مرتفع - قم بتحسين إدارة الذاكرة")
        
        # توصيات عامة
        recommendations.extend([
            "\n📋 توصيات عامة:",
            "✅ استخدم caching بشكل مكثف لتحسين الأداء",
            "✅ قم بتحسين استعلامات قاعدة البيانات",
            "✅ استخدم CDN لتوزيع المحتوى الثابت",
            "✅ راقب الأداء بشكل مستمر",
            "✅ قم بإجراء اختبارات دورية",
            "✅ احتفظ بنسخ احتياطية منتظمة",
            "✅ استخدم load balancing عند الحاجة"
        ])
        
        return recommendations
    
    def generate_warnings(self,
                         stress_report: StressTestReport,
                         capacity_report: CapacityReport,
                         perf_summary: Dict[str, Any]) -> List[str]:
        """توليد تحذيرات"""
        warnings = []
        
        # تحذيرات اختبارات الضغط
        if stress_report.failed_tests > 0:
            warnings.append(f"⚠️ {stress_report.failed_tests} اختبار فشل من أصل {stress_report.total_tests}")
        
        # تحذيرات القدرة الاستيعابية
        bottleneck = capacity_report.capacity_estimate.bottleneck
        warnings.append(f"⚠️ العنق الزجاجة الرئيسي: {bottleneck.upper()}")
        
        if capacity_report.capacity_estimate.max_concurrent_viewers < 50:
            warnings.append("⚠️ القدرة الاستيعابية منخفضة جداً")
        
        # تحذيرات الأداء
        if perf_summary['max_cpu'] > 90:
            warnings.append(f"⚠️ استهلاك CPU وصل إلى {perf_summary['max_cpu']:.1f}%")
        if perf_summary['max_memory'] > 90:
            warnings.append(f"⚠️ استهلاك الذاكرة وصل إلى {perf_summary['max_memory']:.1f}%")
        
        # تحذيرات HuggingFace
        warnings.extend([
            "\n⚠️ قيود HuggingFace Spaces:",
            "- قد يتم إيقاف التطبيق بعد فترة من عدم النشاط",
            "- الموارد محدودة في الخطة المجانية",
            "- يُنصح بالترقية للاستخدام الإنتاجي"
        ])
        
        return warnings
    
    def generate_next_steps(self,
                           stress_report: StressTestReport,
                           capacity_report: CapacityReport) -> List[str]:
        """توليد الخطوات التالية"""
        next_steps = []
        
        # بناءً على نتائج الاختبارات
        if stress_report.failed_tests > 0:
            next_steps.append("1. إصلاح الاختبارات الفاشلة")
        
        # بناءً على القدرة الاستيعابية
        bottleneck = capacity_report.capacity_estimate.bottleneck
        
        if bottleneck == 'bandwidth':
            next_steps.extend([
                "2. تحسين استهلاك bandwidth:",
                "   - استخدام adaptive bitrate streaming",
                "   - ضغط الفيديو بشكل أفضل",
                "   - استخدام CDN"
            ])
        elif bottleneck == 'cpu':
            next_steps.extend([
                "2. تحسين استخدام CPU:",
                "   - تحسين الكود",
                "   - استخدام caching",
                "   - استخدام async/await بشكل صحيح"
            ])
        elif bottleneck == 'ram':
            next_steps.extend([
                "2. تحسين استخدام الذاكرة:",
                "   - تقليل حجم الـ buffers",
                "   - استخدام streaming",
                "   - تنظيف الذاكرة بشكل دوري"
            ])
        elif bottleneck == 'connections':
            next_steps.extend([
                "2. تحسين إدارة الاتصالات:",
                "   - استخدام connection pooling",
                "   - تقليل عدد الاتصالات لكل مستخدم",
                "   - استخدام HTTP/2"
            ])
        
        next_steps.extend([
            "3. تطبيق التحسينات المقترحة",
            "4. إعادة تشغيل الاختبارات للتحقق من التحسينات",
            "5. مراقبة الأداء في بيئة الإنتاج",
            "6. جمع ملاحظات المستخدمين",
            "7. التخطيط للتوسع المستقبلي"
        ])
        
        return next_steps
    
    async def run_all_tests(self, monitoring_duration: int = 60) -> ComprehensiveTestReport:
        """تشغيل جميع الاختبارات"""
        print("\n" + "="*70)
        print("🚀 بدء الاختبارات الشاملة لنظام PopCorn")
        print("="*70)
        print(f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🌐 URL: {self.base_url}")
        print("="*70 + "\n")
        
        try:
            # المرحلة 1: اختبارات الضغط
            stress_report = await self.run_stress_tests()
            
            # المرحلة 2: تحليل القدرة الاستيعابية
            capacity_report = self.run_capacity_analysis()
            
            # المرحلة 3: مراقبة الأداء
            perf_summary = await self.run_performance_monitoring(monitoring_duration)
            
            # توليد التوصيات والتحذيرات
            recommendations = self.generate_overall_recommendations(
                stress_report, capacity_report, perf_summary
            )
            warnings = self.generate_warnings(
                stress_report, capacity_report, perf_summary
            )
            next_steps = self.generate_next_steps(
                stress_report, capacity_report
            )
            
            # تحديد الحالة العامة
            success_rate = (stress_report.passed_tests / stress_report.total_tests * 100) if stress_report.total_tests > 0 else 0
            
            if success_rate >= 95 and capacity_report.capacity_estimate.max_concurrent_viewers >= 100:
                overall_status = "ممتاز"
            elif success_rate >= 85 and capacity_report.capacity_estimate.max_concurrent_viewers >= 50:
                overall_status = "جيد"
            elif success_rate >= 70:
                overall_status = "مقبول"
            else:
                overall_status = "يحتاج تحسين"
            
            # إنشاء التقرير الشامل
            total_duration = time.time() - self.start_time
            
            report = ComprehensiveTestReport(
                test_date=datetime.now().isoformat(),
                total_duration=total_duration,
                stress_test_results={
                    'total_tests': stress_report.total_tests,
                    'passed_tests': stress_report.passed_tests,
                    'failed_tests': stress_report.failed_tests,
                    'success_rate': success_rate,
                    'duration': stress_report.total_duration
                },
                capacity_analysis={
                    'max_concurrent_viewers': capacity_report.capacity_estimate.max_concurrent_viewers,
                    'max_concurrent_streams': capacity_report.capacity_estimate.max_concurrent_streams,
                    'max_rooms': capacity_report.capacity_estimate.max_rooms,
                    'bottleneck': capacity_report.capacity_estimate.bottleneck,
                    'confidence_level': capacity_report.capacity_estimate.confidence_level
                },
                performance_metrics=perf_summary,
                overall_status=overall_status,
                recommendations=recommendations,
                warnings=warnings,
                next_steps=next_steps
            )
            
            return report
            
        except Exception as e:
            print(f"\n❌ خطأ في تشغيل الاختبارات: {e}")
            raise
    
    def save_comprehensive_report(self, report: ComprehensiveTestReport, 
                                  json_file: str = "comprehensive_test_report.json",
                                  md_file: str = "comprehensive_test_report.md"):
        """حفظ التقرير الشامل"""
        # حفظ JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 تم حفظ التقرير JSON في: {json_file}")
        
        # توليد تقرير Markdown
        self._generate_markdown_report(report, md_file)
    
    def _generate_markdown_report(self, report: ComprehensiveTestReport, filename: str):
        """توليد تقرير Markdown شامل"""
        md_content = f"""# تقرير الاختبارات الشاملة لنظام PopCorn

**تاريخ الاختبار:** {datetime.fromisoformat(report.test_date).strftime('%Y-%m-%d %H:%M:%S')}  
**المدة الإجمالية:** {report.total_duration:.2f} ثانية  
**الحالة العامة:** **{report.overall_status}**

---

## 📊 ملخص تنفيذي

### الحالة العامة: {report.overall_status}

| المقياس | القيمة |
|---------|--------|
| معدل نجاح الاختبارات | {report.stress_test_results['success_rate']:.1f}% |
| القدرة الاستيعابية | {report.capacity_analysis['max_concurrent_viewers']} مشاهد |
| العنق الزجاجة | {report.capacity_analysis['bottleneck'].upper()} |
| متوسط استهلاك CPU | {report.performance_metrics['avg_cpu']:.1f}% |
| متوسط استهلاك الذاكرة | {report.performance_metrics['avg_memory']:.1f}% |

---

## 🔥 نتائج اختبارات الضغط

### الإحصائيات

- **إجمالي الاختبارات:** {report.stress_test_results['total_tests']}
- **الاختبارات الناجحة:** {report.stress_test_results['passed_tests']} ✅
- **الاختبارات الفاشلة:** {report.stress_test_results['failed_tests']} ❌
- **معدل النجاح:** {report.stress_test_results['success_rate']:.1f}%
- **المدة:** {report.stress_test_results['duration']:.2f} ثانية

### التقييم

"""
        
        success_rate = report.stress_test_results['success_rate']
        if success_rate >= 95:
            md_content += "🟢 **ممتاز** - النظام يعمل بشكل مثالي تحت الضغط\n"
        elif success_rate >= 85:
            md_content += "🟡 **جيد** - النظام يعمل بشكل جيد مع بعض التحسينات الممكنة\n"
        elif success_rate >= 70:
            md_content += "🟠 **مقبول** - النظام يعمل لكن يحتاج تحسينات\n"
        else:
            md_content += "🔴 **ضعيف** - النظام يحتاج تحسينات عاجلة\n"
        
        md_content += f"""
---

## 📈 تحليل القدرة الاستيعابية

### القدرة المقدرة

| المقياس | القيمة |
|---------|--------|
| الحد الأقصى للمشاهدين المتزامنين | **{report.capacity_analysis['max_concurrent_viewers']}** |
| الحد الأقصى للبث المتزامن | **{report.capacity_analysis['max_concurrent_streams']}** |
| الحد الأقصى للغرف | **{report.capacity_analysis['max_rooms']}** |

### العنق الزجاجة

**{report.capacity_analysis['bottleneck'].upper()}** هو العامل المحدد الرئيسي للقدرة الاستيعابية.

### مستوى الثقة

{report.capacity_analysis['confidence_level']}

---

## ⏱️ نتائج مراقبة الأداء

### الإحصائيات

- **مدة المراقبة:** {report.performance_metrics['duration']} ثانية
- **عدد العينات:** {report.performance_metrics['samples_collected']}
- **متوسط استهلاك CPU:** {report.performance_metrics['avg_cpu']:.1f}%
- **أقصى استهلاك CPU:** {report.performance_metrics['max_cpu']:.1f}%
- **متوسط استهلاك الذاكرة:** {report.performance_metrics['avg_memory']:.1f}%
- **أقصى استهلاك الذاكرة:** {report.performance_metrics['max_memory']:.1f}%

### التقييم

"""
        
        if report.performance_metrics['avg_cpu'] < 60 and report.performance_metrics['avg_memory'] < 70:
            md_content += "🟢 **ممتاز** - استهلاك الموارد في المستوى المثالي\n"
        elif report.performance_metrics['avg_cpu'] < 75 and report.performance_metrics['avg_memory'] < 80:
            md_content += "🟡 **جيد** - استهلاك الموارد مقبول\n"
        else:
            md_content += "🔴 **مرتفع** - استهلاك الموارد يحتاج تحسين\n"
        
        md_content += "\n---\n\n## 💡 التوصيات\n\n"
        
        for rec in report.recommendations:
            md_content += f"{rec}\n"
        
        md_content += "\n---\n\n## ⚠️ التحذيرات\n\n"
        
        for warn in report.warnings:
            md_content += f"{warn}\n"
        
        md_content += "\n---\n\n## 📋 الخطوات التالية\n\n"
        
        for step in report.next_steps:
            md_content += f"{step}\n"
        
        md_content += """

---

## 📁 الملفات المرفقة

تم إنشاء الملفات التالية:

1. **stress_test_results.json** - نتائج اختبارات الضغط التفصيلية
2. **capacity_analysis.json** - تحليل القدرة الاستيعابية
3. **capacity_analysis.md** - تقرير القدرة الاستيعابية
4. **performance_monitoring.json** - بيانات مراقبة الأداء
5. **performance_monitoring.md** - تقرير مراقبة الأداء
6. **comprehensive_test_report.json** - التقرير الشامل (JSON)
7. **comprehensive_test_report.md** - هذا التقرير

---

## 🎯 الخلاصة

"""
        
        if report.overall_status == "ممتاز":
            md_content += """
النظام في حالة ممتازة ويمكنه التعامل مع الحمل المتوقع بكفاءة عالية. 
استمر في المراقبة الدورية وتطبيق أفضل الممارسات.
"""
        elif report.overall_status == "جيد":
            md_content += """
النظام في حالة جيدة ويعمل بشكل مقبول. هناك بعض التحسينات الممكنة 
التي يمكن أن تحسن الأداء والقدرة الاستيعابية.
"""
        elif report.overall_status == "مقبول":
            md_content += """
النظام يعمل لكن يحتاج إلى تحسينات لضمان الأداء الأمثل. 
يُنصح بتطبيق التوصيات المذكورة أعلاه.
"""
        else:
            md_content += """
النظام يحتاج إلى تحسينات عاجلة لضمان الاستقرار والأداء الجيد. 
يجب معالجة المشاكل المذكورة في التحذيرات بأولوية عالية.
"""
        
        md_content += """

---

*تم إنشاء هذا التقرير تلقائياً بواسطة ComprehensiveTestRunner*
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"📄 تم حفظ التقرير Markdown في: {filename}")
    
    def print_summary(self, report: ComprehensiveTestReport):
        """طباعة ملخص النتائج"""
        print("\n" + "="*70)
        print("📊 ملخص النتائج النهائية")
        print("="*70)
        
        print(f"\n🎯 الحالة العامة: {report.overall_status}")
        print(f"⏱️  المدة الإجمالية: {report.total_duration:.2f} ثانية")
        
        print(f"\n🔥 اختبارات الضغط:")
        print(f"   ✅ نجح: {report.stress_test_results['passed_tests']}/{report.stress_test_results['total_tests']}")
        print(f"   📈 معدل النجاح: {report.stress_test_results['success_rate']:.1f}%")
        
        print(f"\n📊 القدرة الاستيعابية:")
        print(f"   👥 الحد الأقصى للمشاهدين: {report.capacity_analysis['max_concurrent_viewers']}")
        print(f"   🎬 الحد الأقصى للبث: {report.capacity_analysis['max_concurrent_streams']}")
        print(f"   🚧 العنق الزجاجة: {report.capacity_analysis['bottleneck'].upper()}")
        
        print(f"\n⏱️  الأداء:")
        print(f"   💻 متوسط CPU: {report.performance_metrics['avg_cpu']:.1f}%")
        print(f"   💾 متوسط RAM: {report.performance_metrics['avg_memory']:.1f}%")
        
        print("\n" + "="*70)
        print("✅ تم الانتهاء من جميع الاختبارات")
        print("="*70 + "\n")


async def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PopCorn Comprehensive Test Runner')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL for testing')
    parser.add_argument('--monitoring-duration', type=int, default=60, 
                       help='Performance monitoring duration in seconds')
    parser.add_argument('--output-prefix', default='comprehensive_test_report',
                       help='Output file prefix')
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner(base_url=args.url)
    
    try:
        # تشغيل جميع الاختبارات
        report = await runner.run_all_tests(monitoring_duration=args.monitoring_duration)
        
        # حفظ التقارير
        runner.save_comprehensive_report(
            report,
            json_file=f"{args.output_prefix}.json",
            md_file=f"{args.output_prefix}.md"
        )
        
        # طباعة الملخص
        runner.print_summary(report)
        
        # عرض أهم التوصيات
        print("💡 أهم التوصيات:")
        for i, rec in enumerate(report.recommendations[:5], 1):
            print(f"   {i}. {rec}")
        
        print("\n📁 تم إنشاء جميع التقارير بنجاح!")
        
    except KeyboardInterrupt:
        print("\n\n🛑 تم إيقاف الاختبارات")
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
