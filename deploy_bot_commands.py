#!/usr/bin/env python3
"""Deploy bot_commands.py to HuggingFace"""
import os
from huggingface_hub import HfApi

# Read token from .env file manually
token = None
space_name = 'ToolKit-backend/PopCorn'

if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            if line.startswith('HF_TOKEN='):
                token = line.split('=', 1)[1].strip().strip('"').strip("'")
            elif line.startswith('HF_SPACE_NAME='):
                space_name = line.split('=', 1)[1].strip().strip('"').strip("'")

if not token:
    print("❌ HF_TOKEN not found in .env file")
    exit(1)

api = HfApi(token=token)

print(f"🚀 Deploying bot_commands.py to {space_name}...")

try:
    result = api.upload_file(
        path_or_fileobj="app/bot_commands.py",
        path_in_repo="app/bot_commands.py",
        repo_id=space_name,
        repo_type="space",
        commit_message="🔧 CRITICAL FIX: Merge bot.py and bot_commands.py\n\nAdded all required functions:\n- cmd_start, cmd_app, cmd_help, cmd_new, cmd_top, cmd_stats, cmd_admin\n- get_callback_handlers()\n- All user browsing functions\n- All admin panel functions\n- Fixed database calls (no limit/offset)\n- Maintained Arabic interface"
    )
    
    print("✅ bot_commands.py deployed successfully!")
    print(f"📦 Commit: {result}")
    print(f"🌐 Space: https://huggingface.co/spaces/{space_name}")
    print("\n🎯 The bot should now start successfully!")
    
except Exception as e:
    print(f"❌ Deployment failed: {e}")
    import traceback
    traceback.print_exc()

# Made with Bob
