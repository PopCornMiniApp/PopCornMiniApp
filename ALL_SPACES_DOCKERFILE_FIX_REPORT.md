
================================================================================
DOCKERFILE FIX DEPLOYMENT REPORT - ALL 5 SPACES
================================================================================

Execution Mode: LIVE DEPLOYMENT
Start Time: 2026-05-09T09:41:58.685319
End Time: 2026-05-09T09:43:28.275114
Duration: 89.6 seconds

SUMMARY:
--------
Total Spaces: 5
Successful Uploads: 5/5
Successful Builds: 1/5
Failed: 4/5

DETAILED RESULTS:
-----------------

1. ✅ ToolKit-backend/PopCorn
   Description: Main PopCorn Space
   Token: HF_TOKEN_1
   Upload: ✅ Success
   Build: ✅ Success
   Final Status: RUNNING
   Timestamp: 2026-05-09T09:41:58.685342

2. ❌ ToolKit-backend/popcorn-main
   Description: PopCorn Main Space
   Token: HF_TOKEN_1
   Upload: ✅ Success
   Build: ❌ Failed
   Final Status: BUILD_ERROR
   Timestamp: 2026-05-09T09:42:08.230881

3. ❌ ToolKit-backend/popcorn-streaming
   Description: PopCorn Streaming Space (Currently Failing)
   Token: HF_TOKEN_1
   Upload: ✅ Success
   Build: ❌ Failed
   Final Status: BUILD_ERROR
   Timestamp: 2026-05-09T09:42:27.926702

4. ❌ rayig/popcorn-backup
   Description: PopCorn Backup Space
   Token: HF_TOKEN_2
   Upload: ✅ Success
   Build: ❌ Failed
   Final Status: BUILD_ERROR
   Timestamp: 2026-05-09T09:42:47.922823

5. ❌ rayig/popcorn-analytics
   Description: PopCorn Analytics Space
   Token: HF_TOKEN_2
   Upload: ✅ Success
   Build: ❌ Failed
   Final Status: BUILD_ERROR
   Timestamp: 2026-05-09T09:43:08.214745

================================================================================
⚠️  PARTIAL SUCCESS: 1/5 Spaces built successfully
================================================================================
