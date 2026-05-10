#!/usr/bin/env python3
"""
سكريبت اختبار شامل للتطبيق محلياً قبل الرفع إلى HuggingFace
"""
import os
import sys
import time
import json
import asyncio
import subprocess
import requests
from datetime import datetime

# ألوان للطباعة
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

class LocalAppTester:
    def __init__(self):
        self.base_url = "http://localhost:7860"
        self.api_url = f"{self.base_url}/api"
        self.app_process = None
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
    
    def check_env_file(self):
        """التحقق من وجود ملف .env"""
        print_header("1. التحقق من ملف التكوين")
        
        if not os.path.exists(".env"):
            print_error("ملف .env غير موجود!")
            print_info("يرجى نسخ .env.example إلى .env وتعبئة البيانات المطلوبة")
            return False
        
        print_success("ملف .env موجود")
        
        # التحقق من المتغيرات الأساسية
        required_vars = [
            "MAIN_BOT_TOKEN",
            "ADMIN_ID",
            "HF_TOKEN",
            "TMDB_API_KEY"
        ]
        
        from dotenv import load_dotenv
        load_dotenv()
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print_warning(f"متغيرات مفقودة: {', '.join(missing_vars)}")
            return False
        
        print_success("جميع المتغيرات الأساسية موجودة")
        return True
    
    def start_app(self):
        """تشغيل التطبيق"""
        print_header("2. تشغيل التطبيق")
        
        try:
            print_info("جاري تشغيل التطبيق...")
            self.app_process = subprocess.Popen(
                ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # انتظار بدء التطبيق
            print_info("انتظار بدء التطبيق (30 ثانية)...")
            time.sleep(30)
            
            # التحقق من أن العملية لا تزال تعمل
            if self.app_process.poll() is not None:
                print_error("فشل تشغيل التطبيق!")
                stderr = self.app_process.stderr.read()
                print_error(f"الخطأ: {stderr[:500]}")
                return False
            
            print_success("التطبيق يعمل الآن")
            return True
            
        except Exception as e:
            print_error(f"خطأ في تشغيل التطبيق: {str(e)}")
            return False
    
    def test_health_endpoint(self):
        """اختبار نقطة الصحة"""
        print_header("3. اختبار نقطة الصحة (Health Check)")
        
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print_success(f"الخادم يعمل بشكل صحيح")
                print_info(f"الحالة: {data.get('status', 'N/A')}")
                self.test_results["tests"]["health"] = {"status": "passed", "data": data}
                return True
            else:
                print_error(f"فشل الاختبار: {response.status_code}")
                self.test_results["tests"]["health"] = {"status": "failed", "code": response.status_code}
                return False
                
        except Exception as e:
            print_error(f"خطأ في الاتصال: {str(e)}")
            self.test_results["tests"]["health"] = {"status": "error", "error": str(e)}
            return False
    
    def test_stats_endpoint(self):
        """اختبار نقطة الإحصائيات"""
        print_header("4. اختبار نقطة الإحصائيات")
        
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print_success("تم جلب الإحصائيات بنجاح")
                print_info(f"عدد الأفلام: {data.get('movies_count', 0)}")
                print_info(f"عدد المسلسلات: {data.get('series_count', 0)}")
                print_info(f"عدد الحلقات: {data.get('episodes_count', 0)}")
                self.test_results["tests"]["stats"] = {"status": "passed", "data": data}
                return True
            else:
                print_error(f"فشل الاختبار: {response.status_code}")
                self.test_results["tests"]["stats"] = {"status": "failed", "code": response.status_code}
                return False
                
        except Exception as e:
            print_error(f"خطأ: {str(e)}")
            self.test_results["tests"]["stats"] = {"status": "error", "error": str(e)}
            return False
    
    def test_movies_endpoint(self):
        """اختبار نقطة الأفلام"""
        print_header("5. اختبار نقطة الأفلام")
        
        try:
            response = requests.get(f"{self.api_url}/movies?page=1&limit=10", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                movies_count = len(data.get('movies', []))
                print_success(f"تم جلب {movies_count} فيلم")
                
                if movies_count > 0:
                    first_movie = data['movies'][0]
                    print_info(f"مثال: {first_movie.get('title', 'N/A')}")
                
                self.test_results["tests"]["movies"] = {"status": "passed", "count": movies_count}
                return True
            else:
                print_error(f"فشل الاختبار: {response.status_code}")
                self.test_results["tests"]["movies"] = {"status": "failed", "code": response.status_code}
                return False
                
        except Exception as e:
            print_error(f"خطأ: {str(e)}")
            self.test_results["tests"]["movies"] = {"status": "error", "error": str(e)}
            return False
    
    def test_series_endpoint(self):
        """اختبار نقطة المسلسلات"""
        print_header("6. اختبار نقطة المسلسلات")
        
        try:
            response = requests.get(f"{self.api_url}/series?page=1&limit=10", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                series_count = len(data.get('series', []))
                print_success(f"تم جلب {series_count} مسلسل")
                
                if series_count > 0:
                    first_series = data['series'][0]
                    print_info(f"مثال: {first_series.get('title', 'N/A')}")
                
                self.test_results["tests"]["series"] = {"status": "passed", "count": series_count}
                return True
            else:
                print_error(f"فشل الاختبار: {response.status_code}")
                self.test_results["tests"]["series"] = {"status": "failed", "code": response.status_code}
                return False
                
        except Exception as e:
            print_error(f"خطأ: {str(e)}")
            self.test_results["tests"]["series"] = {"status": "error", "error": str(e)}
            return False
    
    def test_frontend(self):
        """اختبار الفرونت إند"""
        print_header("7. اختبار الفرونت إند")
        
        try:
            response = requests.get(self.base_url, timeout=10)
            
            if response.status_code == 200:
                print_success("صفحة الفرونت إند تعمل بشكل صحيح")
                
                # التحقق من وجود العناصر الأساسية
                content = response.text
                checks = {
                    "HTML": "<html" in content.lower(),
                    "Title": "<title>" in content.lower(),
                    "Body": "<body" in content.lower(),
                }
                
                for check, result in checks.items():
                    if result:
                        print_success(f"{check} موجود")
                    else:
                        print_warning(f"{check} مفقود")
                
                self.test_results["tests"]["frontend"] = {"status": "passed", "checks": checks}
                return True
            else:
                print_error(f"فشل الاختبار: {response.status_code}")
                self.test_results["tests"]["frontend"] = {"status": "failed", "code": response.status_code}
                return False
                
        except Exception as e:
            print_error(f"خطأ: {str(e)}")
            self.test_results["tests"]["frontend"] = {"status": "error", "error": str(e)}
            return False
    
    def generate_report(self):
        """إنشاء تقرير الاختبار"""
        print_header("8. تقرير الاختبار النهائي")
        
        passed = sum(1 for test in self.test_results["tests"].values() if test.get("status") == "passed")
        failed = sum(1 for test in self.test_results["tests"].values() if test.get("status") == "failed")
        errors = sum(1 for test in self.test_results["tests"].values() if test.get("status") == "error")
        total = len(self.test_results["tests"])
        
        self.test_results["summary"] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        }
        
        print_info(f"إجمالي الاختبارات: {total}")
        print_success(f"نجح: {passed}")
        print_error(f"فشل: {failed}")
        print_warning(f"أخطاء: {errors}")
        print_info(f"نسبة النجاح: {self.test_results['summary']['success_rate']}")
        
        # حفظ التقرير
        report_file = "local_test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print_success(f"تم حفظ التقرير في: {report_file}")
        
        return passed == total
    
    def cleanup(self):
        """تنظيف وإيقاف التطبيق"""
        print_header("9. التنظيف")
        
        if self.app_process:
            print_info("إيقاف التطبيق...")
            self.app_process.terminate()
            try:
                self.app_process.wait(timeout=10)
                print_success("تم إيقاف التطبيق بنجاح")
            except subprocess.TimeoutExpired:
                print_warning("فشل الإيقاف الطبيعي، إجبار الإيقاف...")
                self.app_process.kill()
                print_success("تم إيقاف التطبيق بالقوة")
    
    def run_all_tests(self):
        """تشغيل جميع الاختبارات"""
        try:
            # 1. التحقق من ملف .env
            if not self.check_env_file():
                print_error("فشل التحقق من ملف التكوين")
                return False
            
            # 2. تشغيل التطبيق
            if not self.start_app():
                print_error("فشل تشغيل التطبيق")
                return False
            
            # 3. اختبار نقاط النهاية
            self.test_health_endpoint()
            self.test_stats_endpoint()
            self.test_movies_endpoint()
            self.test_series_endpoint()
            self.test_frontend()
            
            # 4. إنشاء التقرير
            success = self.generate_report()
            
            return success
            
        except KeyboardInterrupt:
            print_warning("\nتم إيقاف الاختبار بواسطة المستخدم")
            return False
        except Exception as e:
            print_error(f"خطأ غير متوقع: {str(e)}")
            return False
        finally:
            self.cleanup()

def main():
    print_header("🍿 PopCorn - اختبار التطبيق محلياً")
    print_info("هذا السكريبت سيقوم بـ:")
    print_info("1. التحقق من ملف التكوين")
    print_info("2. تشغيل التطبيق محلياً")
    print_info("3. اختبار جميع نقاط النهاية")
    print_info("4. إنشاء تقرير شامل")
    print()
    
    tester = LocalAppTester()
    success = tester.run_all_tests()
    
    if success:
        print_header("✅ جميع الاختبارات نجحت!")
        print_success("التطبيق جاهز للرفع إلى HuggingFace")
        return 0
    else:
        print_header("❌ بعض الاختبارات فشلت")
        print_error("يرجى مراجعة التقرير وإصلاح المشاكل قبل الرفع")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
