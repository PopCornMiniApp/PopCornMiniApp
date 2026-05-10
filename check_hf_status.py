#!/usr/bin/env python3
"""
Check HuggingFace Space Status
Verifies if the space has been rebuilt and is running
"""
import requests
import time
from datetime import datetime

SPACE_URL = "https://huggingface.co/spaces/ToolKit-backend/PopCorn"
API_URL = "https://toolkit-backend-popcorn.hf.space"

def check_space_status():
    print("🔍 Checking HuggingFace Space Status\n")
    
    # Check if API is responding
    print("1. Testing API endpoint...")
    try:
        response = requests.get(f"{API_URL}/api/movies", timeout=10)
        if response.status_code == 200:
            data = response.json()
            movies_count = len(data.get("movies", []))
            print(f"   ✅ API is responding")
            print(f"   📊 Movies count: {movies_count}")
        else:
            print(f"   ⚠️  API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API not responding: {e}")
        print(f"   ℹ️  Space might still be building...")
        return False
    
    # Check series endpoint
    print("\n2. Testing series endpoint...")
    try:
        response = requests.get(f"{API_URL}/api/series", timeout=10)
        if response.status_code == 200:
            data = response.json()
            series_count = len(data.get("series", []))
            print(f"   ✅ Series API is responding")
            print(f"   📊 Series count: {series_count}")
            
            if series_count >= 9:
                print(f"   🎉 SUCCESS! All {series_count} series are available!")
                return True
            else:
                print(f"   ⚠️  Only {series_count} series found (expected 9)")
                return False
        else:
            print(f"   ⚠️  Series API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Series API not responding: {e}")
        return False

def main():
    print(f"🌐 HuggingFace Space: {SPACE_URL}")
    print(f"🔗 API URL: {API_URL}\n")
    
    max_attempts = 10
    attempt = 1
    
    while attempt <= max_attempts:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Attempt {attempt}/{max_attempts}")
        print("-" * 50)
        
        if check_space_status():
            print("\n" + "="*50)
            print("✅ VERIFICATION SUCCESSFUL!")
            print("="*50)
            print(f"\n🎉 The update has been deployed successfully!")
            print(f"🌐 Visit: {SPACE_URL}")
            return True
        
        if attempt < max_attempts:
            print(f"\n⏳ Waiting 30 seconds before next attempt...\n")
            time.sleep(30)
        
        attempt += 1
    
    print("\n" + "="*50)
    print("⚠️  VERIFICATION INCOMPLETE")
    print("="*50)
    print(f"\nThe Space might still be building.")
    print(f"Please check manually: {SPACE_URL}")
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

# Made with Bob
