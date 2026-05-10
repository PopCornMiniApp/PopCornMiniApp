# HuggingFace Spaces Build Fix Guide 🔧

## Overview

The `fix_hf_spaces_build.py` script is a comprehensive solution for diagnosing and fixing build errors across all 5 HuggingFace Spaces. It handles common issues like `__pycache__` files, incorrect dependencies, missing metadata, and more.

## Features

✅ **Comprehensive Diagnosis**
- Checks build status of all Spaces
- Identifies problematic files (__pycache__, .pyc, .session, .db)
- Validates requirements.txt
- Checks README.md metadata
- Verifies .gitignore presence

✅ **Automatic Fixes**
- Removes all problematic files
- Simplifies requirements.txt (removes Telegram dependencies)
- Adds proper HF Space metadata to README.md
- Creates comprehensive .gitignore
- Restarts Spaces to trigger rebuild

✅ **Build Monitoring**
- Real-time build status tracking
- Timeout handling (10 minutes per Space)
- Health endpoint verification
- Detailed logging with timestamps

✅ **Multi-Space Support**
- Handles all 5 Spaces with proper token management
- Supports both ToolKit-backend and rayig accounts
- Rate limit protection with delays between operations

## Spaces Managed

1. **ToolKit-backend/PopCorn** (Main Space)
2. **ToolKit-backend/popcorn-main**
3. **ToolKit-backend/popcorn-streaming**
4. **rayig/popcorn-backup** (requires HF_TOKEN_2)
5. **rayig/popcorn-analytics** (requires HF_TOKEN_2)

## Prerequisites

### Environment Variables

Create a `.env` file in the PopCorn directory:

```bash
# Primary HuggingFace token (for ToolKit-backend spaces)
HF_TOKEN_1=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Secondary HuggingFace token (for rayig spaces)
HF_TOKEN_2=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Alternative: Use HF_TOKEN if you only have one token
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Python Dependencies

```bash
pip install huggingface-hub python-dotenv requests
```

## Usage

### 1. Basic Usage (Fix All Spaces)

Run the complete fix process for all 5 Spaces:

```bash
cd PopCorn
python3 fix_hf_spaces_build.py
```

This will:
1. Diagnose all Spaces
2. Apply necessary fixes
3. Monitor build progress
4. Verify health endpoints
5. Generate a summary report

### 2. Monitor Only Mode

Check current status without applying fixes:

```bash
python3 fix_hf_spaces_build.py --monitor-only
```

Output example:
```
🔍 Monitoring Space Status...

PopCorn (Main): RUNNING
popcorn-main: BUILD_ERROR
popcorn-streaming: BUILDING
popcorn-backup: STOPPED
popcorn-analytics: RUNNING
```

### 3. Fix Specific Spaces

Fix only selected Spaces:

```bash
# By name
python3 fix_hf_spaces_build.py --spaces "popcorn-main" "popcorn-streaming"

# By repo_id
python3 fix_hf_spaces_build.py --spaces "ToolKit-backend/popcorn-main"
```

### 4. Skip Diagnosis (Fast Mode)

Apply all fixes without diagnosis phase:

```bash
python3 fix_hf_spaces_build.py --skip-diagnosis
```

⚠️ **Warning**: This applies all fixes blindly. Use only if you know what needs fixing.

### 5. Help

View all available options:

```bash
python3 fix_hf_spaces_build.py --help
```

## What Gets Fixed

### 1. Problematic Files Removed

- `**/__pycache__/**` - Python cache directories
- `*.pyc` - Compiled Python files
- `*.session` - Telegram session files
- `*.session-journal` - Telegram session journals
- `*.db`, `*.sqlite`, `*.sqlite3` - Local database files

### 2. Requirements.txt Simplified

**Before** (causes build errors):
```txt
fastapi==0.115.6
pyrogram==2.0.106        # ❌ Requires Telegram credentials
TgCrypto==1.2.5          # ❌ Requires Telegram credentials
python-telegram-bot==21.9 # ❌ Requires Telegram credentials
...
```

**After** (HF Spaces compatible):
```txt
fastapi==0.115.6
uvicorn[standard]==0.32.1
httpx==0.28.1
huggingface-hub==0.27.1
aiofiles==24.1.0
python-multipart==0.0.20
pydantic==2.10.4
aiohttp==3.11.11
python-dotenv==1.0.1
cachetools==5.5.0
requests==2.31.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### 3. README.md Metadata Added

Proper HF Space configuration:
```yaml
---
title: PopCorn
emoji: 🍿
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
license: mit
app_port: 7860
---
```

### 4. .gitignore Created

Prevents future uploads of problematic files:
```gitignore
__pycache__/
*.py[cod]
*.db
*.sqlite*
*.session
.env
```

## Output and Logging

### Console Output

The script provides detailed, color-coded output:

```
[2026-05-09 05:13:45] ℹ️ Processing 5 Space(s)...

======================================================================
PHASE 1: DIAGNOSIS
----------------------------------------------------------------------

[2026-05-09 05:13:46] 🔄 Diagnosing popcorn-main...
[2026-05-09 05:13:47] ⚠️  Found 3 issues in popcorn-main

======================================================================
PHASE 2: APPLYING FIXES
======================================================================

======================================================================
FIXING SPACE: popcorn-main
======================================================================

[2026-05-09 05:13:50] 🔄 Deleting 48 problematic files from popcorn-main...
[2026-05-09 05:13:55] ✅ Deleted 48/48 files
[2026-05-09 05:13:57] 🔄 Fixing requirements.txt for popcorn-main...
[2026-05-09 05:13:58] ✅ requirements.txt updated successfully
[2026-05-09 05:14:00] 🔄 Restarting popcorn-main...
[2026-05-09 05:14:01] ✅ Space restarted successfully

[2026-05-09 05:14:01] ℹ️ Monitoring build progress (this may take 5-10 minutes)...
[2026-05-09 05:14:11] ℹ️ Build status: BUILDING
[2026-05-09 05:15:21] ℹ️ Build status: RUNNING
[2026-05-09 05:15:21] ✅ Build successful! Space is RUNNING

✅ popcorn-main FIXED SUCCESSFULLY!
```

### JSON Log File

Results are saved to a timestamped JSON file:

```json
{
  "timestamp": "2026-05-09T05:15:30.123456",
  "results": {
    "ToolKit-backend/popcorn-main": {
      "name": "popcorn-main",
      "repo_id": "ToolKit-backend/popcorn-main",
      "initial_status": "BUILD_ERROR",
      "final_status": "RUNNING",
      "issues_found": 3,
      "fixes_applied": [
        "Deleted 48 problematic files",
        "Fixed requirements.txt",
        "Fixed README.md",
        "Added .gitignore",
        "Restarted Space"
      ],
      "success": true,
      "health_check": true
    }
  }
}
```

## Troubleshooting

### Issue: "HF_TOKEN_1 not found"

**Solution**: Create a `.env` file with your HuggingFace token:
```bash
echo "HF_TOKEN_1=hf_your_token_here" > .env
```

### Issue: "Failed to delete file: 403 Forbidden"

**Solution**: Check token permissions. The token needs write access to the Space.

### Issue: Build still fails after fixes

**Possible causes**:
1. **Missing environment variables in Space settings**
   - Go to Space Settings → Variables
   - Add required variables (HF_TOKEN, SECRET_KEY, etc.)

2. **Dockerfile issues**
   - Check if Dockerfile exists and is valid
   - Verify port 7860 is exposed
   - Ensure CMD starts the app correctly

3. **App code errors**
   - Check Space logs for Python errors
   - Verify all imports are in requirements.txt
   - Test locally with Docker first

### Issue: "Build monitoring timeout"

**Solution**: 
- Builds can take 10-15 minutes for large Spaces
- Check Space manually on HuggingFace
- Re-run with `--monitor-only` to check status

### Issue: Health check fails but Space is RUNNING

**Possible causes**:
1. App takes time to start (wait 30-60 seconds)
2. Health endpoint not implemented
3. Port mismatch (should be 7860)

## Best Practices

### Before Running

1. ✅ Backup important data from Spaces
2. ✅ Test locally with Docker first
3. ✅ Check Space logs for specific errors
4. ✅ Verify tokens have proper permissions

### After Running

1. ✅ Check all Spaces are RUNNING
2. ✅ Test API endpoints manually
3. ✅ Verify health checks pass
4. ✅ Monitor for 24 hours for stability

### Regular Maintenance

1. Run `--monitor-only` daily to check status
2. Keep requirements.txt minimal
3. Never commit __pycache__ or .session files
4. Use .gitignore properly
5. Set up Space secrets for sensitive data

## Advanced Usage

### Custom Fixes

Edit the script to add custom fixes:

```python
def custom_fix(self, space: Dict) -> bool:
    """Add your custom fix logic"""
    # Your code here
    pass
```

### Integration with CI/CD

```bash
# In your CI/CD pipeline
python3 fix_hf_spaces_build.py --skip-diagnosis --spaces "popcorn-main"
```

### Scheduled Monitoring

```bash
# Add to crontab for daily checks
0 9 * * * cd /path/to/PopCorn && python3 fix_hf_spaces_build.py --monitor-only
```

## Success Criteria

A successful fix should result in:

✅ All Spaces in `RUNNING` state
✅ Health checks passing
✅ No __pycache__ files in repos
✅ Simplified requirements.txt
✅ Proper README.md metadata
✅ .gitignore in place

## Support

If issues persist after running this script:

1. Check the generated JSON log file
2. Review Space logs on HuggingFace
3. Test Dockerfile locally
4. Verify environment variables in Space settings
5. Check HuggingFace status page for platform issues

## Script Architecture

```
fix_hf_spaces_build.py
├── SpaceBuildFixer (Main Class)
│   ├── __init__() - Initialize APIs and tokens
│   ├── diagnose_space() - Identify issues
│   ├── delete_problematic_files() - Clean repo
│   ├── fix_requirements() - Update dependencies
│   ├── fix_readme() - Add metadata
│   ├── add_gitignore() - Prevent future issues
│   ├── restart_space() - Trigger rebuild
│   ├── monitor_build() - Track progress
│   ├── verify_health() - Test endpoints
│   ├── fix_space() - Orchestrate all fixes
│   └── run() - Main execution flow
└── main() - CLI entry point
```

## Timeline

Expected execution time per Space:
- Diagnosis: 30 seconds
- File deletion: 1-2 minutes (depends on file count)
- Requirements update: 10 seconds
- README update: 10 seconds
- .gitignore creation: 10 seconds
- Build monitoring: 5-10 minutes
- Health verification: 30 seconds

**Total per Space**: ~7-15 minutes
**Total for all 5 Spaces**: ~35-75 minutes

## Version History

- **v1.0** (2026-05-09): Initial comprehensive version
  - Multi-space support
  - Build monitoring
  - Health checks
  - Detailed logging

---

**Made with ❤️ by Bob**