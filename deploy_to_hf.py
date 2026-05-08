"""
Deploy PopCorn project to HuggingFace Space.
Run: python deploy_to_hf.py
"""
import os
import subprocess
import sys
from pathlib import Path

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_SPACE = "ToolKit-backend/PopCorn"
HF_DATASET = "ToolKit-backend/PopCornDB"
SCRIPT_DIR = Path(__file__).parent
MINI_APP_URL = "https://toolkit-backend-popcorn.hf.space"


def run(cmd, cwd=None):
    print(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd or SCRIPT_DIR)
    if r.returncode != 0:
        print(f"ERROR: command failed with code {r.returncode}")
        sys.exit(r.returncode)


def build_frontend():
    print("\n=== Building React Frontend ===")
    frontend_dir = SCRIPT_DIR / "frontend"
    run("npm install", cwd=frontend_dir)
    run("npm run build", cwd=frontend_dir)
    # Copy built files to static/
    import shutil
    dist = frontend_dir / "dist"
    static = SCRIPT_DIR / "static"
    if static.exists():
        shutil.rmtree(static)
    shutil.copytree(dist, static)
    print("✅ Frontend built and copied to static/")


def push_to_space():
    print("\n=== Pushing to HuggingFace Space ===")
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)

    print(f"Uploading to {HF_SPACE}...")
    api.upload_folder(
        folder_path=str(SCRIPT_DIR),
        repo_id=HF_SPACE,
        repo_type="space",
        token=HF_TOKEN,
        ignore_patterns=[
            "*.pyc", "__pycache__", ".git", "node_modules",
            "frontend/src", "frontend/node_modules", "frontend/public",
            ".env", "*.egg-info", "deploy_to_hf.py", "dataset_readme.md",
            "frontend/dist",
        ],
        commit_message="🍿 PopCorn v3.1 — bug fixes & streaming improvements",
    )
    print(f"✅ Pushed to https://huggingface.co/spaces/{HF_SPACE}")


def init_dataset():
    print("\n=== Initializing HuggingFace Dataset ===")
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)
    try:
        api.repo_info(repo_id=HF_DATASET, repo_type="dataset", token=HF_TOKEN)
        print(f"Dataset {HF_DATASET} already exists")
    except Exception:
        api.create_repo(repo_id=HF_DATASET, repo_type="dataset", private=True, token=HF_TOKEN)
        print(f"✅ Created dataset: {HF_DATASET}")

    readme = """---
license: mit
---
# PopCorn DB

SQLite database for PopCorn Telegram Mini App.
Contains movies, series, and episodes synced from Telegram private group.
"""
    readme_path = SCRIPT_DIR / "dataset_readme.md"
    readme_path.write_text(readme)
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=HF_DATASET,
        repo_type="dataset",
        token=HF_TOKEN,
        commit_message="Initialize dataset",
    )
    readme_path.unlink(missing_ok=True)
    print(f"✅ Dataset ready: https://huggingface.co/datasets/{HF_DATASET}")


def set_space_secrets():
    print("\n=== Setting Space Secrets ===")
    secrets = {
        "HF_TOKEN":           HF_TOKEN,
        "HF_DATASET_NAME":    HF_DATASET,
        "HF_SPACE_NAME":      HF_SPACE,
        "MAIN_BOT_TOKEN":     os.environ.get("MAIN_BOT_TOKEN", ""),
        "STREAM_BOT_1":       os.environ.get("STREAM_BOT_1", ""),
        "STREAM_BOT_2":       os.environ.get("STREAM_BOT_2", ""),
        "TMDB_API_KEY":       os.environ.get("TMDB_API_KEY", ""),
        "ADMIN_ID":           os.environ.get("ADMIN_ID", ""),
        "ADMIN_USERNAME":     os.environ.get("ADMIN_USERNAME", ""),
        "PRIVATE_GROUP_ID":   os.environ.get("PRIVATE_GROUP_ID") or os.environ.get("PRIVATE_GROUPE_1_ID", ""),
        "PUBLIC_CHANNEL_ID":  os.environ.get("PUBLIC_CHANNEL_ID", ""),
        "SESSION_1_API_ID":   os.environ.get("SESSION_1_API_ID", ""),
        "SESSION_1_API_HASH": os.environ.get("SESSION_1_API_HASH", ""),
        "SESSION_2_API_ID":   os.environ.get("SESSION_2_API_ID", ""),
        "SESSION_2_API_HASH": os.environ.get("SESSION_2_API_HASH", ""),
    }
    from huggingface_hub import HfApi
    api = HfApi(token=HF_TOKEN)
    for key, value in secrets.items():
        if value:
            try:
                api.add_space_secret(repo_id=HF_SPACE, key=key, value=value, token=HF_TOKEN)
                print(f"  ✅ Secret set: {key}")
            except Exception as e:
                print(f"  ⚠️  Could not set {key}: {e}")


if __name__ == "__main__":
    print("🍿 PopCorn — HuggingFace Deployment v3.1")
    print("=" * 45)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        run("pip install huggingface_hub")
        from huggingface_hub import HfApi

    build_frontend()
    init_dataset()
    set_space_secrets()
    push_to_space()

    print("\n" + "=" * 45)
    print("🎉 Deployment complete!")
    print(f"🌐 Mini App URL: {MINI_APP_URL}")
    print(f"🤖 Set this URL in BotFather as the Mini App URL")
    print("=" * 45)
