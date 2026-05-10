#!/usr/bin/env python3
"""
Final Build Monitoring and Verification Script
Monitors HuggingFace Space build status and performs comprehensive testing
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

class FinalVerification:
    def __init__(self):
        self.space_url = "https://huggingface.co/spaces/jamalmohamad1/PopCorn"
        self.api_base = "https://jamalmohamad1-popcorn.hf.space"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "build_status": None,
            "api_tests": {},
            "errors": [],
            "warnings": [],
            "success": False
        }
    
    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f"  {text}")
        print("="*80 + "\n")
    
    def print_status(self, status: str, message: str):
        """Print status message"""
        symbols = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "progress": "🔄"
        }
        symbol = symbols.get(status, "•")
        print(f"{symbol} {message}")
    
    def check_space_status(self) -> Dict:
        """Check HuggingFace Space status"""
        self.print_header("Checking HuggingFace Space Status")
        
        try:
            # Try to access the Space API
            response = requests.get(f"{self.api_base}/api/stats", timeout=10)
            
            if response.status_code == 200:
                self.print_status("success", "Space is running and accessible")
                return {
                    "status": "running",
                    "accessible": True,
                    "response_time": response.elapsed.total_seconds()
                }
            else:
                self.print_status("warning", f"Space returned status code: {response.status_code}")
                return {
                    "status": "running_with_issues",
                    "accessible": True,
                    "status_code": response.status_code
                }
        
        except requests.exceptions.ConnectionError:
            self.print_status("warning", "Space is not accessible yet (building or starting)")
            return {
                "status": "building_or_starting",
                "accessible": False
            }
        
        except Exception as e:
            self.print_status("error", f"Error checking Space: {str(e)}")
            return {
                "status": "error",
                "accessible": False,
                "error": str(e)
            }
    
    def wait_for_build(self, max_wait: int = 180) -> bool:
        """Wait for Space to become accessible"""
        self.print_header("Waiting for Space to Build and Start")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait:
            attempt += 1
            elapsed = int(time.time() - start_time)
            
            self.print_status("progress", f"Attempt {attempt} - Elapsed: {elapsed}s / {max_wait}s")
            
            status = self.check_space_status()
            
            if status["accessible"]:
                self.print_status("success", f"Space is accessible after {elapsed} seconds")
                return True
            
            # Wait before next attempt
            time.sleep(10)
        
        self.print_status("error", f"Space did not become accessible within {max_wait} seconds")
        return False
    
    def test_api_endpoint(self, endpoint: str, name: str) -> Dict:
        """Test a specific API endpoint"""
        url = f"{self.api_base}{endpoint}"
        
        try:
            response = requests.get(url, timeout=15)
            
            result = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["data_received"] = True
                    result["data_size"] = len(str(data))
                    
                    # Analyze data structure
                    if isinstance(data, dict):
                        result["data_keys"] = list(data.keys())
                    elif isinstance(data, list):
                        result["data_count"] = len(data)
                    
                    self.print_status("success", f"{name}: OK ({result['response_time']:.2f}s)")
                except:
                    result["data_received"] = False
                    self.print_status("warning", f"{name}: Response not JSON")
            else:
                result["success"] = False
                self.print_status("error", f"{name}: Status {response.status_code}")
            
            return result
        
        except Exception as e:
            self.print_status("error", f"{name}: {str(e)}")
            return {
                "endpoint": endpoint,
                "success": False,
                "error": str(e)
            }
    
    def test_all_apis(self) -> Dict:
        """Test all API endpoints"""
        self.print_header("Testing API Endpoints")
        
        endpoints = {
            "stats": "/api/stats",
            "movies": "/api/movies",
            "series": "/api/series",
            "health": "/health"
        }
        
        results = {}
        
        for name, endpoint in endpoints.items():
            results[name] = self.test_api_endpoint(endpoint, name.capitalize())
            time.sleep(1)  # Small delay between requests
        
        return results
    
    def check_for_errors(self) -> List[str]:
        """Check for common deployment errors"""
        self.print_header("Checking for Common Errors")
        
        errors = []
        
        # Check if we can access the main page
        try:
            response = requests.get(self.api_base, timeout=10)
            if response.status_code != 200:
                errors.append(f"Main page returned status {response.status_code}")
                self.print_status("error", errors[-1])
        except Exception as e:
            errors.append(f"Cannot access main page: {str(e)}")
            self.print_status("error", errors[-1])
        
        # Check API endpoints for ImportError indicators
        try:
            response = requests.get(f"{self.api_base}/api/stats", timeout=10)
            if "ImportError" in response.text or "ModuleNotFoundError" in response.text:
                errors.append("ImportError detected in API response")
                self.print_status("error", errors[-1])
        except:
            pass
        
        if not errors:
            self.print_status("success", "No common errors detected")
        
        return errors
    
    def generate_report(self) -> str:
        """Generate comprehensive verification report"""
        self.print_header("Generating Final Report")
        
        report = []
        report.append("# 🎬 PopCorn Final Verification Report")
        report.append(f"\n**Generated:** {self.results['timestamp']}")
        report.append(f"\n**Space URL:** {self.space_url}")
        report.append(f"**API Base:** {self.api_base}")
        
        # Build Status
        report.append("\n## 🏗️ Build Status")
        if self.results["build_status"]:
            status = self.results["build_status"]
            report.append(f"- **Status:** {status.get('status', 'Unknown')}")
            report.append(f"- **Accessible:** {'✅ Yes' if status.get('accessible') else '❌ No'}")
            if "response_time" in status:
                report.append(f"- **Response Time:** {status['response_time']:.2f}s")
        
        # API Tests
        report.append("\n## 🔌 API Endpoint Tests")
        if self.results["api_tests"]:
            for name, result in self.results["api_tests"].items():
                status_icon = "✅" if result.get("success") else "❌"
                report.append(f"\n### {status_icon} {name.upper()}")
                report.append(f"- **Endpoint:** `{result.get('endpoint', 'N/A')}`")
                report.append(f"- **Status Code:** {result.get('status_code', 'N/A')}")
                
                if "response_time" in result:
                    report.append(f"- **Response Time:** {result['response_time']:.2f}s")
                
                if "data_count" in result:
                    report.append(f"- **Items Returned:** {result['data_count']}")
                
                if "error" in result:
                    report.append(f"- **Error:** {result['error']}")
        
        # Errors
        if self.results["errors"]:
            report.append("\n## ❌ Errors Found")
            for error in self.results["errors"]:
                report.append(f"- {error}")
        
        # Warnings
        if self.results["warnings"]:
            report.append("\n## ⚠️ Warnings")
            for warning in self.results["warnings"]:
                report.append(f"- {warning}")
        
        # Overall Status
        report.append("\n## 📊 Overall Status")
        if self.results["success"]:
            report.append("### ✅ DEPLOYMENT SUCCESSFUL")
            report.append("\nAll systems are operational and ready for use!")
        else:
            report.append("### ⚠️ DEPLOYMENT NEEDS ATTENTION")
            report.append("\nSome issues were detected that need to be addressed.")
        
        # User Testing Guide
        report.append("\n## 🧪 User Testing Guide")
        report.append("\n### Web Interface Testing")
        report.append(f"1. Visit: {self.api_base}")
        report.append("2. Browse movies and series")
        report.append("3. Test search functionality")
        report.append("4. Try video playback")
        
        report.append("\n### API Testing")
        report.append(f"- **Stats:** {self.api_base}/api/stats")
        report.append(f"- **Movies:** {self.api_base}/api/movies")
        report.append(f"- **Series:** {self.api_base}/api/series")
        
        report.append("\n### Telegram Bot Testing")
        report.append("1. Start the bot: `/start`")
        report.append("2. Search for content: `/search movie_name`")
        report.append("3. Browse categories: Use inline buttons")
        report.append("4. Test tracking: `/mystats`")
        
        # Next Steps
        report.append("\n## 📋 Next Steps")
        if self.results["success"]:
            report.append("1. ✅ Perform user acceptance testing")
            report.append("2. ✅ Monitor performance metrics")
            report.append("3. ✅ Collect user feedback")
            report.append("4. ✅ Plan feature enhancements")
        else:
            report.append("1. ❌ Review and fix reported errors")
            report.append("2. ❌ Re-deploy corrected files")
            report.append("3. ❌ Re-run verification")
        
        return "\n".join(report)
    
    def run_full_verification(self):
        """Run complete verification process"""
        self.print_header("🎬 PopCorn Final Verification")
        
        print("This script will:")
        print("1. Check HuggingFace Space status")
        print("2. Wait for build to complete (if needed)")
        print("3. Test all API endpoints")
        print("4. Check for errors")
        print("5. Generate comprehensive report")
        
        input("\nPress Enter to start verification...")
        
        # Step 1: Initial status check
        initial_status = self.check_space_status()
        self.results["build_status"] = initial_status
        
        # Step 2: Wait for build if needed
        if not initial_status.get("accessible"):
            self.print_status("info", "Space is not accessible, waiting for build...")
            if not self.wait_for_build():
                self.results["errors"].append("Space did not become accessible in time")
                self.results["success"] = False
                return self.generate_report()
            
            # Update status after waiting
            self.results["build_status"] = self.check_space_status()
        
        # Step 3: Test APIs
        self.results["api_tests"] = self.test_all_apis()
        
        # Step 4: Check for errors
        errors = self.check_for_errors()
        self.results["errors"].extend(errors)
        
        # Step 5: Determine overall success
        api_success = all(
            result.get("success", False) 
            for result in self.results["api_tests"].values()
        )
        
        self.results["success"] = (
            self.results["build_status"].get("accessible", False) and
            api_success and
            len(self.results["errors"]) == 0
        )
        
        # Generate and save report
        report = self.generate_report()
        
        # Save to file
        report_file = "FINAL_VERIFICATION_REPORT.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        self.print_status("success", f"Report saved to {report_file}")
        
        # Save JSON results
        json_file = "verification_results.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)
        
        self.print_status("success", f"JSON results saved to {json_file}")
        
        # Print report
        print("\n" + report)
        
        return report

def main():
    """Main execution"""
    verifier = FinalVerification()
    verifier.run_full_verification()

if __name__ == "__main__":
    main()

# Made with Bob
