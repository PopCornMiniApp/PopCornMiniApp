#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام مراقبة الأداء في الوقت الفعلي
Real-time Performance Monitoring System

يراقب:
- استهلاك CPU والذاكرة
- عدد الاتصالات النشطة
- معدل الطلبات في الثانية
- حالة البوتات
- حالة قاعدة البيانات
- إنشاء تقارير بيانية
"""

import asyncio
import aiohttp
import psutil
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import deque
import threading
import signal
import sys

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.animation import FuncAnimation
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ matplotlib not available - graphical monitoring disabled")


@dataclass
class SystemMetrics:
    """مقاييس النظام"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    active_connections: int
    open_files: int


@dataclass
class ApplicationMetrics:
    """مقاييس التطبيق"""
    timestamp: str
    active_users: int
    active_streams: int
    active_rooms: int
    requests_per_second: float
    avg_response_time: float
    error_rate: float
    cache_hit_rate: float
    database_connections: int


@dataclass
class BotMetrics:
    """مقاييس البوتات"""
    timestamp: str
    total_bots: int
    active_bots: int
    failed_bots: int
    total_messages: int
    messages_per_second: float
    avg_bot_response_time: float


@dataclass
class DatabaseMetrics:
    """مقاييس قاعدة البيانات"""
    timestamp: str
    total_movies: int
    total_series: int
    total_users: int
    database_size_mb: float
    query_count: int
    avg_query_time: float
    slow_queries: int


class PerformanceMonitor:
    """نظام مراقبة الأداء"""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 history_size: int = 300,
                 update_interval: float = 1.0):
        self.base_url = base_url
        self.history_size = history_size
        self.update_interval = update_interval
        self.running = False
        
        # تاريخ المقاييس
        self.system_history: deque = deque(maxlen=history_size)
        self.app_history: deque = deque(maxlen=history_size)
        self.bot_history: deque = deque(maxlen=history_size)
        self.db_history: deque = deque(maxlen=history_size)
        
        # إحصائيات الشبكة
        self.network_io_start = psutil.net_io_counters()
        self.last_request_count = 0
        self.last_request_time = time.time()
        
        # معالج الإشارات للإيقاف النظيف
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """معالج إشارات الإيقاف"""
        print("\n\n🛑 إيقاف المراقبة...")
        self.running = False
        sys.exit(0)
    
    def get_system_metrics(self) -> SystemMetrics:
        """الحصول على مقاييس النظام"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # إحصائيات الشبكة
        net_io = psutil.net_io_counters()
        net_sent_mb = (net_io.bytes_sent - self.network_io_start.bytes_sent) / (1024 * 1024)
        net_recv_mb = (net_io.bytes_recv - self.network_io_start.bytes_recv) / (1024 * 1024)
        
        # عدد الاتصالات النشطة
        try:
            connections = len(psutil.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            connections = 0
        
        # عدد الملفات المفتوحة
        try:
            process = psutil.Process()
            open_files = len(process.open_files())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            open_files = 0
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_percent=disk.percent,
            disk_free_gb=disk.free / (1024 * 1024 * 1024),
            network_sent_mb=net_sent_mb,
            network_recv_mb=net_recv_mb,
            active_connections=connections,
            open_files=open_files
        )
    
    async def get_application_metrics(self) -> Optional[ApplicationMetrics]:
        """الحصول على مقاييس التطبيق"""
        try:
            async with aiohttp.ClientSession() as session:
                # الحصول على إحصائيات التطبيق
                async with session.get(
                    f"{self.base_url}/api/stats",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # حساب معدل الطلبات
                        current_time = time.time()
                        time_diff = current_time - self.last_request_time
                        request_count = data.get('total_requests', 0)
                        rps = (request_count - self.last_request_count) / time_diff if time_diff > 0 else 0
                        
                        self.last_request_count = request_count
                        self.last_request_time = current_time
                        
                        return ApplicationMetrics(
                            timestamp=datetime.now().isoformat(),
                            active_users=data.get('active_users', 0),
                            active_streams=data.get('active_streams', 0),
                            active_rooms=data.get('active_rooms', 0),
                            requests_per_second=rps,
                            avg_response_time=data.get('avg_response_time', 0),
                            error_rate=data.get('error_rate', 0),
                            cache_hit_rate=data.get('cache_hit_rate', 0),
                            database_connections=data.get('db_connections', 0)
                        )
        except Exception as e:
            print(f"⚠️ خطأ في الحصول على مقاييس التطبيق: {e}")
            return None
    
    async def get_bot_metrics(self) -> Optional[BotMetrics]:
        """الحصول على مقاييس البوتات"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/bot/status",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return BotMetrics(
                            timestamp=datetime.now().isoformat(),
                            total_bots=data.get('total_bots', 10),
                            active_bots=data.get('active_bots', 0),
                            failed_bots=data.get('failed_bots', 0),
                            total_messages=data.get('total_messages', 0),
                            messages_per_second=data.get('messages_per_second', 0),
                            avg_bot_response_time=data.get('avg_response_time', 0)
                        )
        except Exception as e:
            print(f"⚠️ خطأ في الحصول على مقاييس البوتات: {e}")
            return None
    
    def get_database_metrics(self) -> Optional[DatabaseMetrics]:
        """الحصول على مقاييس قاعدة البيانات"""
        db_path = "PopCorn/popcorn.db"
        
        try:
            # حجم قاعدة البيانات
            import os
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024) if os.path.exists(db_path) else 0
            
            # الاتصال بقاعدة البيانات
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # عدد الأفلام
            cursor.execute("SELECT COUNT(*) FROM movies")
            total_movies = cursor.fetchone()[0]
            
            # عدد المسلسلات
            cursor.execute("SELECT COUNT(*) FROM series")
            total_series = cursor.fetchone()[0]
            
            # عدد المستخدمين (إذا كان الجدول موجوداً)
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                total_users = 0
            
            conn.close()
            
            return DatabaseMetrics(
                timestamp=datetime.now().isoformat(),
                total_movies=total_movies,
                total_series=total_series,
                total_users=total_users,
                database_size_mb=db_size_mb,
                query_count=0,  # يحتاج تتبع منفصل
                avg_query_time=0,  # يحتاج تتبع منفصل
                slow_queries=0  # يحتاج تتبع منفصل
            )
            
        except Exception as e:
            print(f"⚠️ خطأ في الحصول على مقاييس قاعدة البيانات: {e}")
            return None
    
    async def collect_metrics(self):
        """جمع جميع المقاييس"""
        # مقاييس النظام
        system_metrics = self.get_system_metrics()
        self.system_history.append(system_metrics)
        
        # مقاييس التطبيق
        app_metrics = await self.get_application_metrics()
        if app_metrics:
            self.app_history.append(app_metrics)
        
        # مقاييس البوتات
        bot_metrics = await self.get_bot_metrics()
        if bot_metrics:
            self.bot_history.append(bot_metrics)
        
        # مقاييس قاعدة البيانات
        db_metrics = self.get_database_metrics()
        if db_metrics:
            self.db_history.append(db_metrics)
    
    def print_current_status(self):
        """طباعة الحالة الحالية"""
        if not self.system_history:
            return
        
        system = self.system_history[-1]
        
        # مسح الشاشة (يعمل على Linux/Mac)
        print("\033[2J\033[H", end="")
        
        print("="*70)
        print(f"🔍 مراقبة الأداء - PopCorn | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # مقاييس النظام
        print(f"\n💻 النظام:")
        print(f"   CPU: {system.cpu_percent:5.1f}% | ", end="")
        print(f"RAM: {system.memory_percent:5.1f}% ({system.memory_used_mb:,.0f} MB) | ", end="")
        print(f"Disk: {system.disk_percent:5.1f}%")
        print(f"   Network: ↑ {system.network_sent_mb:.2f} MB | ↓ {system.network_recv_mb:.2f} MB")
        print(f"   Connections: {system.active_connections} | Open Files: {system.open_files}")
        
        # مقاييس التطبيق
        if self.app_history:
            app = self.app_history[-1]
            print(f"\n🌐 التطبيق:")
            print(f"   Users: {app.active_users} | Streams: {app.active_streams} | Rooms: {app.active_rooms}")
            print(f"   RPS: {app.requests_per_second:.2f} | Avg Response: {app.avg_response_time:.3f}s")
            print(f"   Error Rate: {app.error_rate:.2f}% | Cache Hit: {app.cache_hit_rate:.2f}%")
        
        # مقاييس البوتات
        if self.bot_history:
            bot = self.bot_history[-1]
            print(f"\n🤖 البوتات:")
            print(f"   Active: {bot.active_bots}/{bot.total_bots} | Failed: {bot.failed_bots}")
            print(f"   Messages: {bot.total_messages} | MPS: {bot.messages_per_second:.2f}")
            print(f"   Avg Response: {bot.avg_bot_response_time:.3f}s")
        
        # مقاييس قاعدة البيانات
        if self.db_history:
            db = self.db_history[-1]
            print(f"\n💾 قاعدة البيانات:")
            print(f"   Movies: {db.total_movies:,} | Series: {db.total_series:,} | Users: {db.total_users:,}")
            print(f"   Size: {db.database_size_mb:.2f} MB")
        
        # تحذيرات
        warnings = []
        if system.cpu_percent > 80:
            warnings.append("⚠️ استهلاك CPU مرتفع")
        if system.memory_percent > 85:
            warnings.append("⚠️ استهلاك RAM مرتفع")
        if system.disk_percent > 90:
            warnings.append("⚠️ مساحة القرص منخفضة")
        
        if self.bot_history and self.bot_history[-1].failed_bots > 2:
            warnings.append("⚠️ عدة بوتات معطلة")
        
        if warnings:
            print(f"\n⚠️ تحذيرات:")
            for warning in warnings:
                print(f"   {warning}")
        
        print("\n" + "="*70)
        print("اضغط Ctrl+C للإيقاف")
    
    async def monitor_loop(self):
        """حلقة المراقبة الرئيسية"""
        self.running = True
        
        print("🚀 بدء المراقبة...")
        print(f"📊 URL: {self.base_url}")
        print(f"⏱️  تحديث كل {self.update_interval} ثانية")
        print(f"📈 حفظ آخر {self.history_size} قراءة\n")
        
        while self.running:
            try:
                await self.collect_metrics()
                self.print_current_status()
                await asyncio.sleep(self.update_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ خطأ في المراقبة: {e}")
                await asyncio.sleep(self.update_interval)
    
    def save_metrics(self, filename: str = "performance_metrics.json"):
        """حفظ المقاييس في ملف"""
        data = {
            'system_metrics': [asdict(m) for m in self.system_history],
            'app_metrics': [asdict(m) for m in self.app_history],
            'bot_metrics': [asdict(m) for m in self.bot_history],
            'db_metrics': [asdict(m) for m in self.db_history],
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 تم حفظ المقاييس في: {filename}")
    
    def generate_report(self, filename: str = "performance_report.md"):
        """توليد تقرير الأداء"""
        if not self.system_history:
            print("⚠️ لا توجد بيانات لتوليد التقرير")
            return
        
        # حساب الإحصائيات
        cpu_values = [m.cpu_percent for m in self.system_history]
        mem_values = [m.memory_percent for m in self.system_history]
        
        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        avg_mem = sum(mem_values) / len(mem_values)
        max_mem = max(mem_values)
        
        # إنشاء التقرير
        report = f"""# تقرير أداء PopCorn

**تاريخ التقرير:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**مدة المراقبة:** {len(self.system_history) * self.update_interval:.0f} ثانية
**عدد القراءات:** {len(self.system_history)}

## 📊 ملخص الأداء

### استهلاك الموارد

| المورد | المتوسط | الحد الأقصى | الحالة |
|--------|---------|-------------|--------|
| CPU | {avg_cpu:.1f}% | {max_cpu:.1f}% | {'✅ جيد' if avg_cpu < 70 else '⚠️ مرتفع'} |
| RAM | {avg_mem:.1f}% | {max_mem:.1f}% | {'✅ جيد' if avg_mem < 80 else '⚠️ مرتفع'} |

"""
        
        # إضافة مقاييس التطبيق
        if self.app_history:
            app_data = self.app_history[-1]
            report += f"""
### مقاييس التطبيق

- **المستخدمون النشطون:** {app_data.active_users}
- **البث النشط:** {app_data.active_streams}
- **الغرف النشطة:** {app_data.active_rooms}
- **معدل الطلبات:** {app_data.requests_per_second:.2f} طلب/ثانية
- **متوسط وقت الاستجابة:** {app_data.avg_response_time:.3f} ثانية
- **معدل الأخطاء:** {app_data.error_rate:.2f}%
- **معدل إصابة الكاش:** {app_data.cache_hit_rate:.2f}%
"""
        
        # إضافة مقاييس البوتات
        if self.bot_history:
            bot_data = self.bot_history[-1]
            report += f"""
### مقاييس البوتات

- **البوتات النشطة:** {bot_data.active_bots}/{bot_data.total_bots}
- **البوتات المعطلة:** {bot_data.failed_bots}
- **إجمالي الرسائل:** {bot_data.total_messages:,}
- **معدل الرسائل:** {bot_data.messages_per_second:.2f} رسالة/ثانية
"""
        
        # إضافة مقاييس قاعدة البيانات
        if self.db_history:
            db_data = self.db_history[-1]
            report += f"""
### مقاييس قاعدة البيانات

- **الأفلام:** {db_data.total_movies:,}
- **المسلسلات:** {db_data.total_series:,}
- **المستخدمون:** {db_data.total_users:,}
- **حجم قاعدة البيانات:** {db_data.database_size_mb:.2f} MB
"""
        
        # التوصيات
        report += "\n## 💡 التوصيات\n\n"
        
        if avg_cpu > 70:
            report += "- ⚠️ استهلاك CPU مرتفع - قم بتحسين الكود أو زيادة الموارد\n"
        if avg_mem > 80:
            report += "- ⚠️ استهلاك RAM مرتفع - قم بتحسين استخدام الذاكرة\n"
        if self.bot_history and self.bot_history[-1].failed_bots > 0:
            report += "- ⚠️ بعض البوتات معطلة - تحقق من الاتصال\n"
        
        report += """
- ✅ استمر في مراقبة الأداء بشكل دوري
- ✅ قم بتحسين الاستعلامات البطيئة
- ✅ استخدم الكاش بشكل فعال
- ✅ راقب معدل الأخطاء

---

*تم إنشاء هذا التقرير تلقائياً بواسطة PerformanceMonitor*
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 تم حفظ التقرير في: {filename}")
    
    def plot_metrics(self, output_file: str = "performance_graphs.png"):
        """رسم المقاييس بيانياً"""
        if not MATPLOTLIB_AVAILABLE:
            print("⚠️ matplotlib غير متوفر - لا يمكن رسم الرسوم البيانية")
            return
        
        if not self.system_history:
            print("⚠️ لا توجد بيانات للرسم")
            return
        
        # إنشاء الرسوم البيانية
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('PopCorn Performance Metrics', fontsize=16, fontweight='bold')
        
        # استخراج البيانات
        timestamps = [datetime.fromisoformat(m.timestamp) for m in self.system_history]
        cpu_data = [m.cpu_percent for m in self.system_history]
        mem_data = [m.memory_percent for m in self.system_history]
        
        # رسم CPU
        axes[0, 0].plot(timestamps, cpu_data, 'b-', linewidth=2)
        axes[0, 0].set_title('CPU Usage (%)')
        axes[0, 0].set_ylabel('Percentage')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=80, color='r', linestyle='--', alpha=0.5, label='Warning (80%)')
        axes[0, 0].legend()
        
        # رسم Memory
        axes[0, 1].plot(timestamps, mem_data, 'g-', linewidth=2)
        axes[0, 1].set_title('Memory Usage (%)')
        axes[0, 1].set_ylabel('Percentage')
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].axhline(y=85, color='r', linestyle='--', alpha=0.5, label='Warning (85%)')
        axes[0, 1].legend()
        
        # رسم معدل الطلبات
        if self.app_history:
            app_timestamps = [datetime.fromisoformat(m.timestamp) for m in self.app_history]
            rps_data = [m.requests_per_second for m in self.app_history]
            axes[1, 0].plot(app_timestamps, rps_data, 'r-', linewidth=2)
            axes[1, 0].set_title('Requests Per Second')
            axes[1, 0].set_ylabel('RPS')
            axes[1, 0].grid(True, alpha=0.3)
        
        # رسم حالة البوتات
        if self.bot_history:
            bot_timestamps = [datetime.fromisoformat(m.timestamp) for m in self.bot_history]
            active_bots = [m.active_bots for m in self.bot_history]
            failed_bots = [m.failed_bots for m in self.bot_history]
            axes[1, 1].plot(bot_timestamps, active_bots, 'g-', linewidth=2, label='Active')
            axes[1, 1].plot(bot_timestamps, failed_bots, 'r-', linewidth=2, label='Failed')
            axes[1, 1].set_title('Bot Status')
            axes[1, 1].set_ylabel('Count')
            axes[1, 1].grid(True, alpha=0.3)
            axes[1, 1].legend()
        
        # تنسيق المحور الزمني
        for ax in axes.flat:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"📊 تم حفظ الرسوم البيانية في: {output_file}")
        plt.close()


async def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PopCorn Performance Monitor')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL')
    parser.add_argument('--interval', type=float, default=1.0, help='Update interval in seconds')
    parser.add_argument('--history', type=int, default=300, help='History size')
    parser.add_argument('--duration', type=int, default=0, help='Monitoring duration in seconds (0 = infinite)')
    parser.add_argument('--output', default='performance_metrics', help='Output file prefix')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(
        base_url=args.url,
        history_size=args.history,
        update_interval=args.interval
    )
    
    try:
        if args.duration > 0:
            # مراقبة لمدة محددة
            task = asyncio.create_task(monitor.monitor_loop())
            await asyncio.sleep(args.duration)
            monitor.running = False
            await task
        else:
            # مراقبة مستمرة
            await monitor.monitor_loop()
    
    except KeyboardInterrupt:
        print("\n\n🛑 تم إيقاف المراقبة")
    
    finally:
        # حفظ النتائج
        print("\n💾 حفظ النتائج...")
        monitor.save_metrics(f"{args.output}.json")
        monitor.generate_report(f"{args.output}.md")
        
        if MATPLOTLIB_AVAILABLE:
            monitor.plot_metrics(f"{args.output}.png")
        
        print("\n✅ تم الانتهاء")


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
