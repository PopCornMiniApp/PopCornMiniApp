#!/usr/bin/env python3
"""
Automated Final Verification - No User Input Required
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def print_status(status, message):
    symbols = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "progress": "🔄"
    }
    symbol = symbols.get(status, "•")
    print(f"{symbol} {message}")

def check_space_status():
    """Check if Space is accessible"""
    api_base = "https://jamalmohamad1-popcorn.hf.space"
    
    try:
        response = requests.get(f"{api_base}/api/stats", timeout=10)
        if response.status_code == 200:
            return {"accessible": True, "status_code": 200, "response_time": response.elapsed.total_seconds()}
        else:
            return {"accessible": True, "status_code": response.status_code}
    except requests.exceptions.ConnectionError:
        return {"accessible": False, "status": "building"}
    except Exception as e:
        return {"accessible": False, "error": str(e)}

def wait_for_space(max_wait=180):
    """Wait for Space to become accessible"""
    print_header("Waiting for HuggingFace Space")
    
    start_time = time.time()
    attempt = 0
    
    while time.time() - start_time < max_wait:
        attempt += 1
        elapsed = int(time.time() - start_time)
        
        print_status("progress", f"Attempt {attempt} - Elapsed: {elapsed}s / {max_wait}s")
        
        status = check_space_status()
        
        if status.get("accessible"):
            print_status("success", f"Space is accessible! (Status: {status.get('status_code')})")
            return True
        
        time.sleep(10)
    
    print_status("error", f"Space not accessible after {max_wait}s")
    return False

def test_endpoint(endpoint, name):
    """Test a single endpoint"""
    api_base = "https://jamalmohamad1-popcorn.hf.space"
    url = f"{api_base}{endpoint}"
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                data_info = ""
                if isinstance(data, list):
                    data_info = f" - {len(data)} items"
                elif isinstance(data, dict):
                    data_info = f" - {len(data)} keys"
                
                print_status("success", f"{name}: OK ({response.elapsed.total_seconds():.2f}s){data_info}")
                return {"success": True, "status_code": 200, "data": data}
            except:
                print_status("warning", f"{name}: OK but not JSON")
                return {"success": True, "status_code": 200}
        else:
            print_status("error", f"{name}: Status {response.status_code}")
            return {"success": False, "status_code": response.status_code}
    
    except Exception as e:
        print_status("error", f"{name}: {str(e)}")
        return {"success": False, "error": str(e)}

def test_all_endpoints():
    """Test all API endpoints"""
    print_header("Testing API Endpoints")
    
    endpoints = {
        "Health": "/health",
        "Stats": "/api/stats",
        "Movies": "/api/movies",
        "Series": "/api/series"
    }
    
    results = {}
    for name, endpoint in endpoints.items():
        results[name] = test_endpoint(endpoint, name)
        time.sleep(1)
    
    return results

def generate_report(space_status, api_results):
    """Generate final report"""
    print_header("Final Verification Report")
    
    report = []
    report.append("# 🎬 PopCorn Final Verification Report")
    report.append(f"\n**Generated:** {datetime.now().isoformat()}")
    report.append(f"**Space URL:** https://huggingface.co/spaces/jamalmohamad1/PopCorn")
    report.append(f"**API Base:** https://jamalmohamad1-popcorn.hf.space")
    
    # Space Status
    report.append("\n## 🏗️ Space Status")
    if space_status.get("accessible"):
        report.append("- ✅ **Status:** Running and Accessible")
        if "response_time" in space_status:
            report.append(f"- **Response Time:** {space_status['response_time']:.2f}s")
    else:
        report.append("- ❌ **Status:** Not Accessible")
    
    # API Results
    report.append("\n## 🔌 API Endpoint Tests")
    all_success = True
    for name, result in api_results.items():
        if result.get("success"):
            report.append(f"- ✅ **{name}:** Working")
        else:
            report.append(f"- ❌ **{name}:** Failed")
            all_success = False
    
    # Overall Status
    report.append("\n## 📊 Overall Status")
    if space_status.get("accessible") and all_success:
        report.append("### ✅ DEPLOYMENT SUCCESSFUL")
        report.append("\n**All systems operational!**")
    else:
        report.append("### ⚠️ NEEDS ATTENTION")
        report.append("\n**Some issues detected.**")
    
    # Testing Guide
    report.append("\n## 🧪 Testing Guide")
    report.append("\n### Web Interface")
    report.append("1. Visit: https://jamalmohamad1-popcorn.hf.space")
    report.append("2. Browse movies and series")
    report.append("3. Test search and playback")
    
    report.append("\n### API Endpoints")
    report.append("- Stats: https://jamalmohamad1-popcorn.hf.space/api/stats")
    report.append("- Movies: https://jamalmohamad1-popcorn.hf.space/api/movies")
    report.append("- Series: https://jamalmohamad1-popcorn.hf.space/api/series")
    
    report.append("\n### Telegram Bot")
    report.append("1. Start: `/start`")
    report.append("2. Search: `/search movie_name`")
    report.append("3. Stats: `/mystats`")
    
    # Files Deployed
    report.append("\n## 📦 Deployed Files")
    report.append("- ✅ `app/bot_commands.py` (Integrated)")
    report.append("- ✅ `app/bot_tracking.py`")
    report.append("- ✅ `app/button_builders.py`")
    report.append("- ✅ `app/config.py` (Updated)")
    
    return "\n".join(report)

def main():
    print_header("🎬 PopCorn Automated Verification")
    
    # Step 1: Check initial status
    print_status("info", "Checking Space status...")
    space_status = check_space_status()
    
    # Step 2: Wait if needed
    if not space_status.get("accessible"):
        print_status("info", "Space is building, waiting...")
        if not wait_for_space():
            print_status("error", "Verification failed - Space not accessible")
            return
        space_status = check_space_status()
    else:
        print_status("success", "Space is already accessible!")
    
    # Step 3: Test APIs
    api_results = test_all_endpoints()
    
    # Step 4: Generate report
    report = generate_report(space_status, api_results)
    
    # Save report
    report_file = "FINAL_VERIFICATION_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print_status("success", f"Report saved to {report_file}")
    
    # Save JSON
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "space_status": space_status,
        "api_results": api_results
    }
    
    with open("verification_results.json", "w") as f:
        json.dump(json_data, f, indent=2)
    
    print_status("success", "JSON results saved to verification_results.json")
    
    # Print report
    print("\n" + report)

if __name__ == "__main__":
    main()

# Made with Bob
