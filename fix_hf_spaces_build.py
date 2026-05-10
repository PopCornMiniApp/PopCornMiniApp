#!/usr/bin/env python3
"""
Comprehensive HuggingFace Spaces Build Fix Script
Fixes build errors across all 5 Spaces with proper error handling and monitoring
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download
import requests

# Load environment variables
load_dotenv()

class SpaceBuildFixer:
    """Comprehensive Space build fixer with monitoring and retry logic"""
    
    def __init__(self):
        self.hf_token_1 = os.getenv('HF_TOKEN_1') or os.getenv('HF_TOKEN')
        self.hf_token_2 = os.getenv('HF_TOKEN_2')
        
        if not self.hf_token_1:
            raise ValueError("❌ HF_TOKEN_1 (or HF_TOKEN) not found in environment")
        
        self.api_1 = HfApi(token=self.hf_token_1)
        self.api_2 = HfApi(token=self.hf_token_2) if self.hf_token_2 else None
        
        # Define all 5 Spaces with their tokens
        self.spaces = [
            {
                'name': 'PopCorn (Main)',
                'repo_id': 'ToolKit-backend/PopCorn',
                'api': self.api_1,
                'token': self.hf_token_1
            },
            {
                'name': 'popcorn-main',
                'repo_id': 'ToolKit-backend/popcorn-main',
                'api': self.api_1,
                'token': self.hf_token_1
            },
            {
                'name': 'popcorn-streaming',
                'repo_id': 'ToolKit-backend/popcorn-streaming',
                'api': self.api_1,
                'token': self.hf_token_1
            },
            {
                'name': 'popcorn-backup',
                'repo_id': 'rayig/popcorn-backup',
                'api': self.api_2 if self.api_2 else self.api_1,
                'token': self.hf_token_2 if self.hf_token_2 else self.hf_token_1
            },
            {
                'name': 'popcorn-analytics',
                'repo_id': 'rayig/popcorn-analytics',
                'api': self.api_2 if self.api_2 else self.api_1,
                'token': self.hf_token_2 if self.hf_token_2 else self.hf_token_1
            }
        ]
        
        self.results = {}
        self.log_file = f"build_fix_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROGRESS": "🔄"
        }.get(level, "•")
        print(f"[{timestamp}] {prefix} {message}")
    
    def check_space_status(self, space: Dict) -> Tuple[str, Optional[str]]:
        """Check current build status of a Space"""
        try:
            info = space['api'].space_info(space['repo_id'])
            status = info.runtime.stage if info.runtime else 'UNKNOWN'
            error = info.runtime.error_message if info.runtime and hasattr(info.runtime, 'error_message') else None
            return status, error
        except Exception as e:
            return 'ERROR', str(e)
    
    def diagnose_space(self, space: Dict) -> Dict:
        """Diagnose issues in a Space"""
        self.log(f"Diagnosing {space['name']}...", "PROGRESS")
        diagnosis = {
            'name': space['name'],
            'repo_id': space['repo_id'],
            'issues': [],
            'files_to_delete': [],
            'needs_requirements_fix': False,
            'needs_readme_fix': False,
            'needs_gitignore': False
        }
        
        try:
            # Check current status
            status, error = self.check_space_status(space)
            diagnosis['current_status'] = status
            diagnosis['error_message'] = error
            
            if status == 'BUILD_ERROR':
                diagnosis['issues'].append('Space is in BUILD_ERROR state')
            
            # List all files
            files = space['api'].list_repo_files(space['repo_id'], repo_type='space')
            
            # Check for __pycache__ files
            pycache_files = [f for f in files if '__pycache__' in f or '.pyc' in f]
            if pycache_files:
                diagnosis['issues'].append(f'Found {len(pycache_files)} __pycache__/pyc files')
                diagnosis['files_to_delete'].extend(pycache_files)
            
            # Check for session files
            session_files = [f for f in files if f.endswith('.session') or f.endswith('.session-journal')]
            if session_files:
                diagnosis['issues'].append(f'Found {len(session_files)} Telegram session files')
                diagnosis['files_to_delete'].extend(session_files)
            
            # Check for database files
            db_files = [f for f in files if f.endswith('.db') or f.endswith('.sqlite') or f.endswith('.sqlite3')]
            if db_files:
                diagnosis['issues'].append(f'Found {len(db_files)} database files')
                diagnosis['files_to_delete'].extend(db_files)
            
            # Check requirements.txt
            try:
                req_path = hf_hub_download(
                    repo_id=space['repo_id'],
                    filename='requirements.txt',
                    repo_type='space',
                    token=space['token']
                )
                with open(req_path, 'r') as f:
                    reqs = f.read()
                
                # Check for problematic dependencies
                if 'pyrogram' in reqs.lower() or 'tgcrypto' in reqs.lower():
                    diagnosis['issues'].append('Contains Telegram dependencies (Pyrogram/TgCrypto)')
                    diagnosis['needs_requirements_fix'] = True
                
                if 'python-telegram-bot' in reqs.lower():
                    diagnosis['issues'].append('Contains python-telegram-bot')
                    diagnosis['needs_requirements_fix'] = True
                    
            except Exception as e:
                diagnosis['issues'].append(f'Could not check requirements.txt: {e}')
                diagnosis['needs_requirements_fix'] = True
            
            # Check README.md for proper metadata
            try:
                readme_path = hf_hub_download(
                    repo_id=space['repo_id'],
                    filename='README.md',
                    repo_type='space',
                    token=space['token']
                )
                with open(readme_path, 'r') as f:
                    readme = f.read()
                
                if 'sdk: docker' not in readme.lower():
                    diagnosis['issues'].append('README.md missing proper Space metadata')
                    diagnosis['needs_readme_fix'] = True
                    
            except Exception as e:
                diagnosis['issues'].append('README.md not found or invalid')
                diagnosis['needs_readme_fix'] = True
            
            # Check for .gitignore
            if '.gitignore' not in files:
                diagnosis['issues'].append('Missing .gitignore file')
                diagnosis['needs_gitignore'] = True
            
            self.log(f"Found {len(diagnosis['issues'])} issues in {space['name']}", 
                    "WARNING" if diagnosis['issues'] else "SUCCESS")
            
        except Exception as e:
            diagnosis['issues'].append(f'Diagnosis error: {str(e)}')
            self.log(f"Error diagnosing {space['name']}: {e}", "ERROR")
        
        return diagnosis
    
    def delete_problematic_files(self, space: Dict, files: List[str]) -> int:
        """Delete problematic files from Space"""
        if not files:
            return 0
        
        self.log(f"Deleting {len(files)} problematic files from {space['name']}...", "PROGRESS")
        deleted = 0
        
        for file in files:
            try:
                space['api'].delete_file(
                    path_in_repo=file,
                    repo_id=space['repo_id'],
                    repo_type='space',
                    token=space['token'],
                    commit_message=f'🧹 Remove problematic file: {file}'
                )
                deleted += 1
                if deleted % 10 == 0:
                    self.log(f"Deleted {deleted}/{len(files)} files...", "PROGRESS")
            except Exception as e:
                self.log(f"Failed to delete {file}: {e}", "WARNING")
        
        self.log(f"Deleted {deleted}/{len(files)} files", "SUCCESS")
        return deleted
    
    def fix_requirements(self, space: Dict) -> bool:
        """Upload simplified requirements.txt for HF Spaces"""
        self.log(f"Fixing requirements.txt for {space['name']}...", "PROGRESS")
        
        # Simplified requirements without Telegram dependencies
        simplified_reqs = """fastapi==0.115.6
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
"""
        
        try:
            space['api'].upload_file(
                path_or_fileobj=simplified_reqs.encode(),
                path_in_repo='requirements.txt',
                repo_id=space['repo_id'],
                repo_type='space',
                token=space['token'],
                commit_message='🔧 Simplify requirements for HF Spaces (remove Telegram deps)'
            )
            self.log(f"requirements.txt updated successfully", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Failed to update requirements.txt: {e}", "ERROR")
            return False
    
    def fix_readme(self, space: Dict) -> bool:
        """Add proper HF Space metadata to README.md"""
        self.log(f"Fixing README.md for {space['name']}...", "PROGRESS")
        
        readme_content = f"""---
title: {space['name']}
emoji: 🍿
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# PopCorn Mini App 🍿

A FastAPI-based streaming platform for movies and series.

## Features

- 🎬 Movie and Series streaming
- 🔍 Advanced search and filtering
- 📊 Analytics and monitoring
- 🎨 Modern responsive UI
- 🔐 Secure authentication

## API Endpoints

- `/api/health` - Health check
- `/api/movies` - List movies
- `/api/series` - List series
- `/api/stats` - Platform statistics

## Environment Variables

Configure these in Space settings:
- `HF_TOKEN` - HuggingFace token for dataset access
- `SECRET_KEY` - JWT secret key

## Tech Stack

- FastAPI
- Docker
- HuggingFace Datasets
- Modern JavaScript frontend

---

Built with ❤️ for the community
"""
        
        try:
            space['api'].upload_file(
                path_or_fileobj=readme_content.encode(),
                path_in_repo='README.md',
                repo_id=space['repo_id'],
                repo_type='space',
                token=space['token'],
                commit_message='📝 Add proper HF Space metadata to README'
            )
            self.log(f"README.md updated successfully", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Failed to update README.md: {e}", "ERROR")
            return False
    
    def add_gitignore(self, space: Dict) -> bool:
        """Add comprehensive .gitignore"""
        self.log(f"Adding .gitignore to {space['name']}...", "PROGRESS")
        
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/

# Virtual environments
.env
.venv
env/
venv/
ENV/

# Databases
*.db
*.sqlite
*.sqlite3
*.db-journal
*.db-shm
*.db-wal

# Telegram
*.session
*.session-journal

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp
"""
        
        try:
            space['api'].upload_file(
                path_or_fileobj=gitignore_content.encode(),
                path_in_repo='.gitignore',
                repo_id=space['repo_id'],
                repo_type='space',
                token=space['token'],
                commit_message='🚫 Add comprehensive .gitignore'
            )
            self.log(f".gitignore added successfully", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Failed to add .gitignore: {e}", "ERROR")
            return False
    
    def restart_space(self, space: Dict) -> bool:
        """Restart Space to trigger rebuild"""
        self.log(f"Restarting {space['name']}...", "PROGRESS")
        
        try:
            space['api'].restart_space(space['repo_id'], token=space['token'])
            self.log(f"Space restarted successfully", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Failed to restart Space: {e}", "ERROR")
            return False
    
    def monitor_build(self, space: Dict, timeout: int = 300) -> Tuple[bool, str]:
        """Monitor Space build progress"""
        self.log(f"Monitoring build for {space['name']}...", "PROGRESS")
        
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            try:
                status, error = self.check_space_status(space)
                
                if status != last_status:
                    self.log(f"Build status: {status}", "INFO")
                    last_status = status
                
                if status == 'RUNNING':
                    self.log(f"Build successful! Space is RUNNING", "SUCCESS")
                    return True, status
                elif status == 'BUILD_ERROR':
                    self.log(f"Build failed with error: {error}", "ERROR")
                    return False, status
                elif status in ['STOPPED', 'PAUSED']:
                    self.log(f"Space is {status}, attempting restart...", "WARNING")
                    self.restart_space(space)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.log(f"Error monitoring build: {e}", "WARNING")
                time.sleep(10)
        
        self.log(f"Build monitoring timeout after {timeout}s", "WARNING")
        return False, "TIMEOUT"
    
    def verify_health(self, space: Dict) -> bool:
        """Verify Space health endpoint"""
        self.log(f"Verifying health endpoint for {space['name']}...", "PROGRESS")
        
        try:
            # Get Space URL
            info = space['api'].space_info(space['repo_id'])
            space_url = f"https://{info.id.replace('/', '-')}.hf.space"
            
            # Try health endpoint
            response = requests.get(f"{space_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                self.log(f"Health check passed!", "SUCCESS")
                return True
            else:
                self.log(f"Health check failed with status {response.status_code}", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Could not verify health: {e}", "WARNING")
            return False
    
    def fix_space(self, space: Dict, diagnosis: Dict) -> Dict:
        """Apply all fixes to a Space"""
        self.log(f"\n{'='*70}", "INFO")
        self.log(f"FIXING SPACE: {space['name']}", "INFO")
        self.log(f"{'='*70}", "INFO")
        
        result = {
            'name': space['name'],
            'repo_id': space['repo_id'],
            'initial_status': diagnosis['current_status'],
            'issues_found': len(diagnosis['issues']),
            'fixes_applied': [],
            'success': False,
            'final_status': None,
            'health_check': False
        }
        
        try:
            # Step 1: Delete problematic files
            if diagnosis['files_to_delete']:
                deleted = self.delete_problematic_files(space, diagnosis['files_to_delete'])
                result['fixes_applied'].append(f"Deleted {deleted} problematic files")
                time.sleep(2)
            
            # Step 2: Fix requirements.txt
            if diagnosis['needs_requirements_fix']:
                if self.fix_requirements(space):
                    result['fixes_applied'].append("Fixed requirements.txt")
                time.sleep(2)
            
            # Step 3: Fix README.md
            if diagnosis['needs_readme_fix']:
                if self.fix_readme(space):
                    result['fixes_applied'].append("Fixed README.md")
                time.sleep(2)
            
            # Step 4: Add .gitignore
            if diagnosis['needs_gitignore']:
                if self.add_gitignore(space):
                    result['fixes_applied'].append("Added .gitignore")
                time.sleep(2)
            
            # Step 5: Restart Space
            if self.restart_space(space):
                result['fixes_applied'].append("Restarted Space")
                time.sleep(5)
            
            # Step 6: Monitor build
            self.log(f"\nMonitoring build progress (this may take 5-10 minutes)...", "INFO")
            build_success, final_status = self.monitor_build(space, timeout=600)
            result['final_status'] = final_status
            result['success'] = build_success
            
            # Step 7: Verify health (if build succeeded)
            if build_success:
                time.sleep(10)  # Wait for app to fully start
                result['health_check'] = self.verify_health(space)
            
            if result['success']:
                self.log(f"\n✅ {space['name']} FIXED SUCCESSFULLY!", "SUCCESS")
            else:
                self.log(f"\n❌ {space['name']} FIX INCOMPLETE", "ERROR")
            
        except Exception as e:
            self.log(f"Error fixing {space['name']}: {e}", "ERROR")
            result['error'] = str(e)
        
        return result
    
    def run(self, skip_diagnosis: bool = False, spaces_to_fix: Optional[List[str]] = None):
        """Run the complete fix process"""
        self.log("\n" + "="*70, "INFO")
        self.log("HUGGINGFACE SPACES BUILD FIX SCRIPT", "INFO")
        self.log("="*70 + "\n", "INFO")
        
        # Filter spaces if specified
        spaces_to_process = self.spaces
        if spaces_to_fix:
            spaces_to_process = [s for s in self.spaces if s['name'] in spaces_to_fix or s['repo_id'] in spaces_to_fix]
        
        self.log(f"Processing {len(spaces_to_process)} Space(s)...\n", "INFO")
        
        # Phase 1: Diagnosis
        diagnoses = {}
        if not skip_diagnosis:
            self.log("PHASE 1: DIAGNOSIS", "INFO")
            self.log("-" * 70 + "\n", "INFO")
            
            for space in spaces_to_process:
                diagnosis = self.diagnose_space(space)
                diagnoses[space['repo_id']] = diagnosis
                
                self.log(f"\nDiagnosis for {space['name']}:", "INFO")
                self.log(f"  Status: {diagnosis['current_status']}", "INFO")
                self.log(f"  Issues: {len(diagnosis['issues'])}", "INFO")
                for issue in diagnosis['issues']:
                    self.log(f"    - {issue}", "WARNING")
                
                time.sleep(1)
        
        # Phase 2: Apply Fixes
        self.log("\n" + "="*70, "INFO")
        self.log("PHASE 2: APPLYING FIXES", "INFO")
        self.log("="*70 + "\n", "INFO")
        
        for space in spaces_to_process:
            diagnosis = diagnoses.get(space['repo_id'], {'issues': [], 'files_to_delete': [], 
                                                         'needs_requirements_fix': True,
                                                         'needs_readme_fix': True,
                                                         'needs_gitignore': True,
                                                         'current_status': 'UNKNOWN'})
            
            result = self.fix_space(space, diagnosis)
            self.results[space['repo_id']] = result
            
            # Wait between spaces to avoid rate limits
            if space != spaces_to_process[-1]:
                self.log("\n⏳ Waiting 30 seconds before next Space...\n", "INFO")
                time.sleep(30)
        
        # Phase 3: Summary
        self.generate_summary()
        
        # Save results
        self.save_results()
    
    def generate_summary(self):
        """Generate and display summary report"""
        self.log("\n" + "="*70, "INFO")
        self.log("FINAL SUMMARY", "INFO")
        self.log("="*70 + "\n", "INFO")
        
        total = len(self.results)
        successful = sum(1 for r in self.results.values() if r['success'])
        failed = total - successful
        
        self.log(f"Total Spaces Processed: {total}", "INFO")
        self.log(f"Successfully Fixed: {successful}", "SUCCESS")
        self.log(f"Failed: {failed}", "ERROR" if failed > 0 else "INFO")
        
        self.log("\nDetailed Results:", "INFO")
        self.log("-" * 70, "INFO")
        
        for repo_id, result in self.results.items():
            status_icon = "✅" if result['success'] else "❌"
            self.log(f"\n{status_icon} {result['name']}", "INFO")
            self.log(f"   Repo: {result['repo_id']}", "INFO")
            self.log(f"   Initial Status: {result['initial_status']}", "INFO")
            self.log(f"   Final Status: {result['final_status']}", "INFO")
            self.log(f"   Issues Found: {result['issues_found']}", "INFO")
            self.log(f"   Fixes Applied: {len(result['fixes_applied'])}", "INFO")
            for fix in result['fixes_applied']:
                self.log(f"     - {fix}", "INFO")
            if result.get('health_check'):
                self.log(f"   Health Check: ✅ PASSED", "SUCCESS")
            elif result['success']:
                self.log(f"   Health Check: ⚠️  Could not verify", "WARNING")
        
        self.log("\n" + "="*70, "INFO")
        
        if successful == total:
            self.log("🎉 ALL SPACES FIXED SUCCESSFULLY!", "SUCCESS")
        elif successful > 0:
            self.log(f"⚠️  {successful}/{total} Spaces fixed. Check failed ones manually.", "WARNING")
        else:
            self.log("❌ All fixes failed. Check logs and try manual intervention.", "ERROR")
        
        self.log("="*70 + "\n", "INFO")
    
    def save_results(self):
        """Save results to JSON file"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': self.results
                }, f, indent=2)
            self.log(f"Results saved to: {self.log_file}", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to save results: {e}", "ERROR")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix HuggingFace Spaces build errors')
    parser.add_argument('--skip-diagnosis', action='store_true', 
                       help='Skip diagnosis phase and apply all fixes')
    parser.add_argument('--spaces', nargs='+', 
                       help='Specific spaces to fix (by name or repo_id)')
    parser.add_argument('--monitor-only', action='store_true',
                       help='Only monitor build status without applying fixes')
    
    args = parser.parse_args()
    
    try:
        fixer = SpaceBuildFixer()
        
        if args.monitor_only:
            print("\n🔍 Monitoring Space Status...\n")
            for space in fixer.spaces:
                status, error = fixer.check_space_status(space)
                print(f"{space['name']}: {status}")
                if error:
                    print(f"  Error: {error}")
        else:
            fixer.run(skip_diagnosis=args.skip_diagnosis, spaces_to_fix=args.spaces)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

# Made with Bob
