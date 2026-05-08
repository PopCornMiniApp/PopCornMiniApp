#!/usr/bin/env python3
"""
Upload local database to HuggingFace Dataset.
This script uploads /tmp/popcorn.db to HuggingFace to sync the latest data.
"""
import os
import sys
from pathlib import Path
from huggingface_hub import HfApi

# Configuration
HF_TOKEN = os.environ.get("HF_TOKEN")
HF_DATASET = "ToolKit-backend/PopCornDB"
LOCAL_DB = "/tmp/popcorn.db"

if not HF_TOKEN:
    print("❌ Error: HF_TOKEN environment variable not set")
    print("Please set HF_TOKEN before running this script:")
    print("export HF_TOKEN='your_token_here'")
    sys.exit(1)

def upload_database():
    """Upload local database to HuggingFace"""
    print("🍿 PopCorn Database Upload to HuggingFace")
    print("=" * 60)
    
    # Check if local database exists
    if not os.path.exists(LOCAL_DB):
        print(f"❌ Error: Local database not found at {LOCAL_DB}")
        sys.exit(1)
    
    # Get database info
    import sqlite3
    conn = sqlite3.connect(LOCAL_DB)
    cursor = conn.cursor()
    movie_count = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    conn.close()
    
    db_size = os.path.getsize(LOCAL_DB) / 1024
    print(f"\n📁 Local Database Info:")
    print(f"   - Path: {LOCAL_DB}")
    print(f"   - Size: {db_size:.1f} KB")
    print(f"   - Movies: {movie_count}")
    
    # Initialize HuggingFace API
    print(f"\n🌐 Uploading to HuggingFace Dataset: {HF_DATASET}")
    api = HfApi(token=HF_TOKEN)
    
    try:
        # Upload the database
        api.upload_file(
            path_or_fileobj=LOCAL_DB,
            path_in_repo="popcorn.db",
            repo_id=HF_DATASET,
            repo_type="dataset",
            token=HF_TOKEN,
            commit_message=f"Update database: {movie_count} movies"
        )
        
        print(f"\n✅ Upload successful!")
        print(f"   - Movies uploaded: {movie_count}")
        print(f"   - Dataset URL: https://huggingface.co/datasets/{HF_DATASET}")
        
        # Verify upload
        print(f"\n🔍 Verifying upload...")
        from huggingface_hub import hf_hub_download
        
        downloaded_db = hf_hub_download(
            repo_id=HF_DATASET,
            filename="popcorn.db",
            repo_type="dataset",
            token=HF_TOKEN,
            force_download=True
        )
        
        conn = sqlite3.connect(downloaded_db)
        cursor = conn.cursor()
        hf_count = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        conn.close()
        
        if hf_count == movie_count:
            print(f"✅ Verification successful: {hf_count} movies in HuggingFace")
        else:
            print(f"⚠️  Warning: Count mismatch!")
            print(f"   - Local: {movie_count}")
            print(f"   - HuggingFace: {hf_count}")
        
    except Exception as e:
        print(f"\n❌ Upload failed: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Database sync complete!")

if __name__ == "__main__":
    upload_database()

# Made with Bob
