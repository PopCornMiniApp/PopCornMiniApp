#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام اختبار الضغط الشامل لتطبيق PopCorn
Comprehensive Stress Testing Suite for PopCorn Application

يتضمن:
- اختبارات الأداء الأساسية
- اختبارات الحمل الثقيل
- اختبارات البث المتزامن
- اختبارات التزامن
- اختبارات معالجة الأخطاء
- اختبارات قاعدة البيانات
- اختبارات الأمان
"""

import asyncio
import aiohttp
import time
import psutil
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import string
import sqlite3
from dataclasses import dataclass, asdict
import sys
import os

# إضافة مسار التطبيق
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class TestResult:
    """نتيجة اختبار واحد"""
    test_name: str
    success: bool
    duration: float
    metrics: Dict[str, Any]
    errors: List[str]
    timestamp: str


@dataclass
class StressTestReport:
    """تقرير شامل لاختبارات الضغط"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    total_duration: float
    results: List[TestResult]
    system_metrics: Dict[str, Any]
    recommendations: List[str]


class PerformanceMetrics:
    """مقاييس الأداء"""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.success_count: int = 0
        self.failure_count: int = 0
        self.start_time: float = 0
        self.end_time: float = 0
        
    def add_response(self, duration: float, success: bool):
        """إضافة نتيجة استجابة"""
        self.response_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """حساب الإحصائيات"""
        if not self.response_times:
            return {}
        
        return {
            'min_response_time': min(self.response_times),
            'max_response_time': max(self.response_times),
            'avg_response_time': statistics.mean(self.response_times),
            'median_response_time': statistics.median(self.response_times),
            'std_dev': statistics.stdev(self.response_times) if len(self.response_times) > 1 else 0,
            'success_rate': (self.success_count / (self.success_count + self.failure_count)) * 100,
            'total_requests': self.success_count + self.failure_count,
            'requests_per_second': (self.success_count + self.failure_count) / (self.end_time - self.start_time) if self.end_time > self.start_time else 0
        }


class StressTestSuite:
    """مجموعة اختبارات الضغط الشاملة"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.start_time = time.time()
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """الحصول على مقاييس النظام الحالية"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': memory.available / (1024 * 1024),
            'memory_used_mb': memory.used / (1024 * 1024),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024 * 1024 * 1024),
            'timestamp': datetime.now().isoformat()
        }
    
    # ==================== اختبارات الأداء الأساسية ====================
    
    async def test_api_endpoints_performance(self) -> TestResult:
        """اختبار أداء جميع نقاط النهاية API"""
        print("🔍 اختبار أداء API endpoints...")
        
        endpoints = [
            '/api/movies',
            '/api/series',
            '/api/search',
            '/api/genres',
            '/api/trending',
            '/api/popular',
            '/api/latest',
            '/api/rooms',
            '/api/health',
            '/api/stats'
        ]
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                try:
                    start = time.time()
                    async with session.get(f"{self.base_url}{endpoint}", timeout=10) as response:
                        duration = time.time() - start
                        success = response.status == 200
                        metrics.add_response(duration, success)
                        
                        if not success:
                            errors.append(f"{endpoint}: Status {response.status}")
                except Exception as e:
                    duration = time.time() - start
                    metrics.add_response(duration, False)
                    errors.append(f"{endpoint}: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="API Endpoints Performance",
            success=metrics.failure_count == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    async def test_database_performance(self) -> TestResult:
        """اختبار أداء قاعدة البيانات"""
        print("🔍 اختبار أداء قاعدة البيانات...")
        
        db_path = "PopCorn/popcorn.db"
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # اختبار القراءة
            for _ in range(100):
                start = time.time()
                cursor.execute("SELECT COUNT(*) FROM movies")
                cursor.fetchone()
                duration = time.time() - start
                metrics.add_response(duration, True)
            
            # اختبار البحث
            for _ in range(50):
                start = time.time()
                cursor.execute("SELECT * FROM movies WHERE title LIKE ? LIMIT 10", ('%test%',))
                cursor.fetchall()
                duration = time.time() - start
                metrics.add_response(duration, True)
            
            conn.close()
            
        except Exception as e:
            errors.append(f"Database error: {str(e)}")
            metrics.add_response(0, False)
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="Database Performance",
            success=len(errors) == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    async def test_search_and_filter_performance(self) -> TestResult:
        """اختبار أداء البحث والفلترة"""
        print("🔍 اختبار أداء البحث والفلترة...")
        
        search_queries = [
            'action', 'comedy', 'drama', 'thriller', 'horror',
            'the', 'love', 'war', 'life', 'death'
        ]
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        async with aiohttp.ClientSession() as session:
            for query in search_queries:
                try:
                    start = time.time()
                    async with session.get(
                        f"{self.base_url}/api/search",
                        params={'q': query},
                        timeout=10
                    ) as response:
                        duration = time.time() - start
                        success = response.status == 200
                        metrics.add_response(duration, success)
                        
                        if not success:
                            errors.append(f"Search '{query}': Status {response.status}")
                except Exception as e:
                    duration = time.time() - start
                    metrics.add_response(duration, False)
                    errors.append(f"Search '{query}': {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="Search and Filter Performance",
            success=metrics.failure_count == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== اختبارات الحمل الثقيل ====================
    
    async def test_concurrent_users(self, num_users: int = 100) -> TestResult:
        """اختبار المستخدمين المتزامنين"""
        print(f"🔍 اختبار {num_users} مستخدم متزامن...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        async def simulate_user(session, user_id):
            """محاكاة مستخدم واحد"""
            endpoints = ['/api/movies', '/api/series', '/api/trending']
            
            for endpoint in endpoints:
                try:
                    start = time.time()
                    async with session.get(f"{self.base_url}{endpoint}", timeout=15) as response:
                        duration = time.time() - start
                        metrics.add_response(duration, response.status == 200)
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"User {user_id}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [simulate_user(session, i) for i in range(num_users)]
            await asyncio.gather(*tasks)
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name=f"Concurrent Users Test ({num_users} users)",
            success=metrics.failure_count < num_users * 0.1,  # 10% failure tolerance
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors[:10],  # First 10 errors only
            timestamp=datetime.now().isoformat()
        )
    
    async def test_requests_per_second(self, target_rps: int = 100, duration_seconds: int = 10) -> TestResult:
        """اختبار عدد الطلبات في الثانية"""
        print(f"🔍 اختبار {target_rps} طلب/ثانية لمدة {duration_seconds} ثانية...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        async def make_request(session):
            try:
                start = time.time()
                async with session.get(f"{self.base_url}/api/health", timeout=5) as response:
                    duration = time.time() - start
                    metrics.add_response(duration, response.status == 200)
            except Exception as e:
                metrics.add_response(0, False)
                errors.append(str(e))
        
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                batch_start = time.time()
                tasks = [make_request(session) for _ in range(target_rps)]
                await asyncio.gather(*tasks)
                
                # Wait to maintain target RPS
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    await asyncio.sleep(1.0 - elapsed)
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name=f"Requests Per Second Test ({target_rps} RPS)",
            success=metrics.success_rate > 90,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors[:10],
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== اختبارات البث ====================
    
    async def test_streaming_capacity(self, num_streams: int = 10) -> TestResult:
        """اختبار قدرة البث المتزامن"""
        print(f"🔍 اختبار {num_streams} بث متزامن...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        bandwidth_usage = []
        
        async def simulate_stream(session, stream_id):
            """محاكاة بث واحد"""
            try:
                start = time.time()
                bytes_received = 0
                
                # محاكاة طلب بث
                async with session.get(
                    f"{self.base_url}/api/stream/test_{stream_id}",
                    timeout=30
                ) as response:
                    if response.status == 200:
                        # قراءة البيانات بشكل تدريجي
                        async for chunk in response.content.iter_chunked(8192):
                            bytes_received += len(chunk)
                            if bytes_received > 1024 * 1024:  # 1MB limit for test
                                break
                    
                    duration = time.time() - start
                    metrics.add_response(duration, response.status == 200)
                    bandwidth_usage.append(bytes_received / duration if duration > 0 else 0)
                    
            except Exception as e:
                duration = time.time() - start
                metrics.add_response(duration, False)
                errors.append(f"Stream {stream_id}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [simulate_stream(session, i) for i in range(num_streams)]
            await asyncio.gather(*tasks)
        
        metrics.end_time = time.time()
        
        avg_bandwidth = statistics.mean(bandwidth_usage) if bandwidth_usage else 0
        
        return TestResult(
            test_name=f"Streaming Capacity Test ({num_streams} streams)",
            success=metrics.failure_count < num_streams * 0.2,
            duration=metrics.end_time - metrics.start_time,
            metrics={
                **metrics.get_statistics(),
                'avg_bandwidth_bps': avg_bandwidth,
                'total_bandwidth_mbps': (avg_bandwidth * num_streams) / (1024 * 1024)
            },
            errors=errors[:10],
            timestamp=datetime.now().isoformat()
        )
    
    async def test_bot_failover(self) -> TestResult:
        """اختبار التبديل التلقائي بين البوتات"""
        print("🔍 اختبار التبديل التلقائي بين البوتات...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        # محاكاة فشل بوتات متعددة
        bot_scenarios = [
            {'active_bots': 10, 'failed_bots': 0},
            {'active_bots': 9, 'failed_bots': 1},
            {'active_bots': 7, 'failed_bots': 3},
            {'active_bots': 5, 'failed_bots': 5},
        ]
        
        async with aiohttp.ClientSession() as session:
            for scenario in bot_scenarios:
                try:
                    start = time.time()
                    async with session.get(
                        f"{self.base_url}/api/bot/status",
                        timeout=10
                    ) as response:
                        duration = time.time() - start
                        success = response.status == 200
                        metrics.add_response(duration, success)
                        
                        if success:
                            data = await response.json()
                            # التحقق من قدرة النظام على التعامل مع الفشل
                            if data.get('available_bots', 0) < scenario['active_bots']:
                                errors.append(f"Insufficient bots: {data.get('available_bots')} < {scenario['active_bots']}")
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"Scenario {scenario}: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="Bot Failover Test",
            success=len(errors) == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== اختبارات التزامن ====================
    
    async def test_watch_rooms_concurrency(self, num_rooms: int = 10, users_per_room: int = 20) -> TestResult:
        """اختبار غرف المشاهدة الجماعية"""
        print(f"🔍 اختبار {num_rooms} غرفة مع {users_per_room} مستخدم لكل غرفة...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        async def simulate_room_user(session, room_id, user_id):
            """محاكاة مستخدم في غرفة"""
            try:
                # الانضمام للغرفة
                start = time.time()
                async with session.post(
                    f"{self.base_url}/api/rooms/{room_id}/join",
                    json={'user_id': user_id},
                    timeout=10
                ) as response:
                    duration = time.time() - start
                    metrics.add_response(duration, response.status in [200, 201])
                
                # إرسال رسائل
                for _ in range(5):
                    start = time.time()
                    async with session.post(
                        f"{self.base_url}/api/rooms/{room_id}/message",
                        json={'user_id': user_id, 'message': 'test'},
                        timeout=10
                    ) as response:
                        duration = time.time() - start
                        metrics.add_response(duration, response.status == 200)
                        
            except Exception as e:
                metrics.add_response(0, False)
                errors.append(f"Room {room_id}, User {user_id}: {str(e)}")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for room_id in range(num_rooms):
                for user_id in range(users_per_room):
                    tasks.append(simulate_room_user(session, room_id, user_id))
            
            await asyncio.gather(*tasks)
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name=f"Watch Rooms Concurrency ({num_rooms} rooms, {users_per_room} users/room)",
            success=metrics.success_rate > 85,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors[:20],
            timestamp=datetime.now().isoformat()
        )
    
    async def test_websocket_connections(self, num_connections: int = 100) -> TestResult:
        """اختبار اتصالات WebSocket"""
        print(f"🔍 اختبار {num_connections} اتصال WebSocket...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        successful_connections = 0
        
        # Note: This is a simplified test - actual WebSocket testing would require more setup
        async with aiohttp.ClientSession() as session:
            for i in range(num_connections):
                try:
                    start = time.time()
                    # محاكاة طلب اتصال WebSocket
                    async with session.get(
                        f"{self.base_url}/api/ws/test",
                        timeout=5
                    ) as response:
                        duration = time.time() - start
                        success = response.status in [200, 101]  # 101 = Switching Protocols
                        metrics.add_response(duration, success)
                        if success:
                            successful_connections += 1
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"Connection {i}: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name=f"WebSocket Connections Test ({num_connections} connections)",
            success=successful_connections > num_connections * 0.8,
            duration=metrics.end_time - metrics.start_time,
            metrics={
                **metrics.get_statistics(),
                'successful_connections': successful_connections,
                'connection_rate': successful_connections / num_connections * 100
            },
            errors=errors[:10],
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== اختبارات معالجة الأخطاء ====================
    
    async def test_error_recovery(self) -> TestResult:
        """اختبار استرجاع النظام من الأخطاء"""
        print("🔍 اختبار استرجاع النظام من الأخطاء...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        recovery_times = []
        
        error_scenarios = [
            {'endpoint': '/api/invalid', 'expected_status': 404},
            {'endpoint': '/api/movies/99999999', 'expected_status': 404},
            {'endpoint': '/api/search', 'expected_status': 400},  # Missing query
        ]
        
        async with aiohttp.ClientSession() as session:
            for scenario in error_scenarios:
                try:
                    # إرسال طلب خاطئ
                    start = time.time()
                    async with session.get(
                        f"{self.base_url}{scenario['endpoint']}",
                        timeout=10
                    ) as response:
                        error_duration = time.time() - start
                        
                        # التحقق من معالجة الخطأ بشكل صحيح
                        if response.status == scenario['expected_status']:
                            metrics.add_response(error_duration, True)
                        else:
                            metrics.add_response(error_duration, False)
                            errors.append(f"{scenario['endpoint']}: Expected {scenario['expected_status']}, got {response.status}")
                    
                    # اختبار الاسترجاع - طلب صحيح بعد الخطأ
                    start = time.time()
                    async with session.get(f"{self.base_url}/api/health", timeout=10) as response:
                        recovery_time = time.time() - start
                        recovery_times.append(recovery_time)
                        metrics.add_response(recovery_time, response.status == 200)
                        
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"Error scenario {scenario}: {str(e)}")
        
        metrics.end_time = time.time()
        
        avg_recovery = statistics.mean(recovery_times) if recovery_times else 0
        
        return TestResult(
            test_name="Error Recovery Test",
            success=len(errors) == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics={
                **metrics.get_statistics(),
                'avg_recovery_time': avg_recovery,
                'max_recovery_time': max(recovery_times) if recovery_times else 0
            },
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    async def test_connection_resilience(self) -> TestResult:
        """اختبار مرونة الاتصال"""
        print("🔍 اختبار مرونة الاتصال...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        # محاكاة انقطاعات متعددة
        async with aiohttp.ClientSession() as session:
            for attempt in range(10):
                try:
                    # محاولة الاتصال مع timeout قصير
                    start = time.time()
                    async with session.get(
                        f"{self.base_url}/api/health",
                        timeout=aiohttp.ClientTimeout(total=2)
                    ) as response:
                        duration = time.time() - start
                        metrics.add_response(duration, response.status == 200)
                    
                    # انتظار عشوائي لمحاكاة ظروف الشبكة
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    
                except asyncio.TimeoutError:
                    metrics.add_response(2.0, False)
                    errors.append(f"Attempt {attempt}: Timeout")
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"Attempt {attempt}: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="Connection Resilience Test",
            success=metrics.success_rate > 70,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== اختبارات قاعدة البيانات ====================
    
    async def test_database_heavy_load(self, num_operations: int = 10000) -> TestResult:
        """اختبار قاعدة البيانات تحت حمل ثقيل"""
        print(f"🔍 اختبار قاعدة البيانات مع {num_operations} عملية...")
        
        db_path = "PopCorn/popcorn.db"
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # عمليات قراءة مكثفة
            for i in range(num_operations // 2):
                start = time.time()
                cursor.execute("SELECT * FROM movies LIMIT 10")
                cursor.fetchall()
                duration = time.time() - start
                metrics.add_response(duration, True)
            
            # عمليات بحث مكثفة
            for i in range(num_operations // 2):
                start = time.time()
                search_term = f"%{random.choice(string.ascii_lowercase)}%"
                cursor.execute("SELECT * FROM movies WHERE title LIKE ? LIMIT 5", (search_term,))
                cursor.fetchall()
                duration = time.time() - start
                metrics.add_response(duration, True)
            
            conn.close()
            
        except Exception as e:
            errors.append(f"Database heavy load error: {str(e)}")
            metrics.add_response(0, False)
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name=f"Database Heavy Load Test ({num_operations} operations)",
            success=len(errors) == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    async def test_database_concurrency(self, num_threads: int = 20) -> TestResult:
        """اختبار التزامن في قاعدة البيانات"""
        print(f"🔍 اختبار التزامن في قاعدة البيانات مع {num_threads} thread...")
        
        db_path = "PopCorn/popcorn.db"
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        def db_operation(thread_id):
            """عملية قاعدة بيانات في thread منفصل"""
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                for _ in range(50):
                    start = time.time()
                    cursor.execute("SELECT COUNT(*) FROM movies")
                    cursor.fetchone()
                    duration = time.time() - start
                    metrics.add_response(duration, True)
                
                conn.close()
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
                metrics.add_response(0, False)
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(db_operation, i) for i in range(num_threads)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    errors.append(f"Thread execution error: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name=f"Database Concurrency Test ({num_threads} threads)",
            success=len(errors) == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== اختبارات الأمان ====================
    
    async def test_rate_limiting(self) -> TestResult:
        """اختبار حدود معدل الطلبات"""
        print("🔍 اختبار rate limiting...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        rate_limited_count = 0
        
        async with aiohttp.ClientSession() as session:
            # إرسال طلبات سريعة جداً
            for i in range(200):
                try:
                    start = time.time()
                    async with session.get(f"{self.base_url}/api/movies", timeout=5) as response:
                        duration = time.time() - start
                        
                        if response.status == 429:  # Too Many Requests
                            rate_limited_count += 1
                            metrics.add_response(duration, True)  # Rate limiting working correctly
                        elif response.status == 200:
                            metrics.add_response(duration, True)
                        else:
                            metrics.add_response(duration, False)
                            errors.append(f"Request {i}: Unexpected status {response.status}")
                            
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"Request {i}: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="Rate Limiting Test",
            success=rate_limited_count > 0,  # Should have some rate limiting
            duration=metrics.end_time - metrics.start_time,
            metrics={
                **metrics.get_statistics(),
                'rate_limited_requests': rate_limited_count,
                'rate_limit_percentage': (rate_limited_count / 200) * 100
            },
            errors=errors[:10],
            timestamp=datetime.now().isoformat()
        )
    
    async def test_admin_permissions(self) -> TestResult:
        """اختبار صلاحيات المسؤول"""
        print("🔍 اختبار صلاحيات المسؤول...")
        
        metrics = PerformanceMetrics()
        metrics.start_time = time.time()
        errors = []
        
        admin_endpoints = [
            '/api/admin/users',
            '/api/admin/stats',
            '/api/admin/logs',
            '/api/admin/settings'
        ]
        
        async with aiohttp.ClientSession() as session:
            # محاولة الوصول بدون صلاحيات
            for endpoint in admin_endpoints:
                try:
                    start = time.time()
                    async with session.get(f"{self.base_url}{endpoint}", timeout=10) as response:
                        duration = time.time() - start
                        
                        # يجب أن يرفض الوصول (401 أو 403)
                        if response.status in [401, 403]:
                            metrics.add_response(duration, True)
                        else:
                            metrics.add_response(duration, False)
                            errors.append(f"{endpoint}: Expected 401/403, got {response.status}")
                            
                except Exception as e:
                    metrics.add_response(0, False)
                    errors.append(f"{endpoint}: {str(e)}")
        
        metrics.end_time = time.time()
        
        return TestResult(
            test_name="Admin Permissions Test",
            success=len(errors) == 0,
            duration=metrics.end_time - metrics.start_time,
            metrics=metrics.get_statistics(),
            errors=errors,
            timestamp=datetime.now().isoformat()
        )
    
    # ==================== تشغيل جميع الاختبارات ====================
    
    async def run_all_tests(self) -> StressTestReport:
        """تشغيل جميع الاختبارات"""
        print("\n" + "="*60)
        print("🚀 بدء اختبارات الضغط الشاملة")
        print("="*60 + "\n")
        
        # الحصول على مقاييس النظام الأولية
        initial_metrics = self.get_system_metrics()
        
        # قائمة الاختبارات
        tests = [
            # اختبارات الأداء الأساسية
            self.test_api_endpoints_performance(),
            self.test_database_performance(),
            self.test_search_and_filter_performance(),
            
            # اختبارات الحمل الثقيل
            self.test_concurrent_users(50),
            self.test_concurrent_users(100),
            self.test_requests_per_second(50, 5),
            self.test_requests_per_second(100, 5),
            
            # اختبارات البث
            self.test_streaming_capacity(5),
            self.test_streaming_capacity(10),
            self.test_bot_failover(),
            
            # اختبارات التزامن
            self.test_watch_rooms_concurrency(5, 10),
            self.test_websocket_connections(50),
            
            # اختبارات معالجة الأخطاء
            self.test_error_recovery(),
            self.test_connection_resilience(),
            
            # اختبارات قاعدة البيانات
            self.test_database_heavy_load(5000),
            self.test_database_concurrency(10),
            
            # اختبارات الأمان
            self.test_rate_limiting(),
            self.test_admin_permissions(),
        ]
        
        # تشغيل الاختبارات
        for test in tests:
            try:
                result = await test
                self.results.append(result)
                
                status = "✅ نجح" if result.success else "❌ فشل"
                print(f"{status} - {result.test_name} ({result.duration:.2f}s)")
                
            except Exception as e:
                error_result = TestResult(
                    test_name="Unknown Test",
                    success=False,
                    duration=0,
                    metrics={},
                    errors=[str(e)],
                    timestamp=datetime.now().isoformat()
                )
                self.results.append(error_result)
                print(f"❌ خطأ في الاختبار: {str(e)}")
        
        # الحصول على مقاييس النظام النهائية
        final_metrics = self.get_system_metrics()
        
        # حساب الإحصائيات
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - passed_tests
        total_duration = time.time() - self.start_time
        
        # توصيات
        recommendations = self._generate_recommendations()
        
        report = StressTestReport(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            total_duration=total_duration,
            results=self.results,
            system_metrics={
                'initial': initial_metrics,
                'final': final_metrics
            },
            recommendations=recommendations
        )
        
        print("\n" + "="*60)
        print(f"📊 النتائج النهائية:")
        print(f"   إجمالي الاختبارات: {total_tests}")
        print(f"   ✅ نجح: {passed_tests}")
        print(f"   ❌ فشل: {failed_tests}")
        print(f"   ⏱️  المدة الإجمالية: {total_duration:.2f}s")
        print(f"   📈 معدل النجاح: {(passed_tests/total_tests)*100:.1f}%")
        print("="*60 + "\n")
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """توليد توصيات بناءً على النتائج"""
        recommendations = []
        
        # تحليل النتائج
        failed_tests = [r for r in self.results if not r.success]
        
        if failed_tests:
            recommendations.append("⚠️ يوجد اختبارات فاشلة تحتاج إلى معالجة")
        
        # تحليل أوقات الاستجابة
        avg_response_times = []
        for result in self.results:
            if 'avg_response_time' in result.metrics:
                avg_response_times.append(result.metrics['avg_response_time'])
        
        if avg_response_times:
            overall_avg = statistics.mean(avg_response_times)
            if overall_avg > 1.0:
                recommendations.append(f"⚠️ متوسط وقت الاستجابة مرتفع ({overall_avg:.2f}s) - يحتاج تحسين")
            elif overall_avg > 0.5:
                recommendations.append(f"⚡ متوسط وقت الاستجابة مقبول ({overall_avg:.2f}s) - يمكن تحسينه")
            else:
                recommendations.append(f"✅ متوسط وقت الاستجابة ممتاز ({overall_avg:.2f}s)")
        
        # تحليل معدلات النجاح
        success_rates = []
        for result in self.results:
            if 'success_rate' in result.metrics:
                success_rates.append(result.metrics['success_rate'])
        
        if success_rates:
            overall_success = statistics.mean(success_rates)
            if overall_success < 90:
                recommendations.append(f"⚠️ معدل النجاح منخفض ({overall_success:.1f}%) - يحتاج تحسين الاستقرار")
            elif overall_success < 95:
                recommendations.append(f"⚡ معدل النجاح جيد ({overall_success:.1f}%) - يمكن تحسينه")
            else:
                recommendations.append(f"✅ معدل النجاح ممتاز ({overall_success:.1f}%)")
        
        # توصيات عامة
        recommendations.extend([
            "💡 استخدم caching لتحسين الأداء",
            "💡 قم بتحسين استعلامات قاعدة البيانات",
            "💡 استخدم connection pooling للاتصالات",
            "💡 راقب استهلاك الموارد بشكل مستمر",
            "💡 قم بإجراء اختبارات دورية تحت الضغط"
        ])
        
        return recommendations
    
    def save_report(self, report: StressTestReport, filename: str = "stress_test_report.json"):
        """حفظ التقرير في ملف JSON"""
        report_dict = {
            'total_tests': report.total_tests,
            'passed_tests': report.passed_tests,
            'failed_tests': report.failed_tests,
            'total_duration': report.total_duration,
            'success_rate': (report.passed_tests / report.total_tests * 100) if report.total_tests > 0 else 0,
            'results': [asdict(r) for r in report.results],
            'system_metrics': report.system_metrics,
            'recommendations': report.recommendations,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        print(f"💾 تم حفظ التقرير في: {filename}")


async def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PopCorn Stress Test Suite')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL for testing')
    parser.add_argument('--output', default='stress_test_report.json', help='Output file for report')
    
    args = parser.parse_args()
    
    suite = StressTestSuite(base_url=args.url)
    report = await suite.run_all_tests()
    suite.save_report(report, args.output)
    
    # عرض التوصيات
    print("\n📋 التوصيات:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"   {i}. {rec}")


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
