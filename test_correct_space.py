#!/usr/bin/env python3
import requests
import json

API_BASE = "https://toolkit-backend-popcorn.hf.space"

print("="*80)
print("  Testing PopCorn Space APIs")
print("="*80)

endpoints = {
    "Stats": "/api/stats",
    "Movies": "/api/movies",
    "Series": "/api/series",
    "Health": "/health"
}

for name, endpoint in endpoints.items():
    url = f"{API_BASE}{endpoint}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"✅ {name}: OK - {len(data)} items")
            elif isinstance(data, dict):
                print(f"✅ {name}: OK - {len(data)} keys")
            else:
                print(f"✅ {name}: OK")
        else:
            print(f"❌ {name}: Status {response.status_code}")
    except Exception as e:
        print(f"❌ {name}: {str(e)}")

print("\n" + "="*80)
print("  Testing Web Interface")
print("="*80)

try:
    response = requests.get(API_BASE, timeout=10)
    if response.status_code == 200 and "PopCorn" in response.text:
        print("✅ Web Interface: OK")
    else:
        print(f"⚠️  Web Interface: Status {response.status_code}")
except Exception as e:
    print(f"❌ Web Interface: {str(e)}")
