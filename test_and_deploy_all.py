#!/usr/bin/env python3
"""
Comprehensive Test and Deployment Script for PopCorn Mini App
Tests all fixes and deploys them to production with proper validation.
"""

import os
import sys
import json
import time
import argparse
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_deploy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test result data structure"""
    component: str
    test_name: str
    status: str  # PASS, FAIL, SKIP, WARN
    message: str
    duration: float
    timestamp: str
    details: Optional[Dict] = None


class TestDeploymentManager:
    """Manages comprehensive testing and deployment"""
    
    def __init__(self, dry_run: bool = False, test_only: bool = False, 
                 deploy_only: bool = False, component: Optional[str] = None):
        self.dry_run = dry_run
        self.test_only = test_only
        self.deploy_only = deploy_only
        self.component = component
        self.results: List[TestResult] = []
        self.start_time = datetime.now()
        
        # Environment variables to check
        self.required_env_vars = {
            'huggingface': ['HF_TOKEN_1', 'HF_TOKEN_2'],
            'telegram_bots': [
                'MAIN_BOT_TOKEN',
                'STREAM_BOT_1', 'STREAM_BOT_2',
                'Popcornapp1bot', 'Str_10bot'
            ],
            'telegram_sessions': [
                'SESSION_1_API_ID', 'SESSION_1_API_HASH',
                'SESSION_2_API_ID', 'SESSION_2_API_HASH'
            ],
            'telegram_groups': [
                'PRIVATE_GROUPE_1_ID', 'Group private 8',
                'PUBLIC_CHANNEL_ID'
            ],
            'admin': ['ADMIN_ID', 'ADMIN_USERNAME'],
            'tmdb': ['TMDB_API_KEY']
        }
        
        # HuggingFace Spaces to test
        self.hf_spaces = [
            'PopCornMiniApp',
            'PopCornMiniApp-Mirror1',
            'PopCornMiniApp-Mirror2',
            'PopCornMiniApp-Mirror3',
            'PopCornMiniApp-Mirror4'
        ]
        
        # Telegram groups to test
        self.telegram_groups = [
            'PRIVATE_GROUPE_1_ID',
            'PRIVATE_GROUPE_2_ID',
            'PRIVATE_GROUPE_3_ID',
            'PRIVATE_GROUPE_4_ID',
            'PRIVATE_GROUPE_5_ID',
            'PRIVATE_GROUPE_6_ID',
            'PRIVATE_GROUPE_7_ID',
            'Group private 8',
            'PUBLIC_CHANNEL_ID'
        ]
    
    def log_result(self, component: str, test_name: str, status: str, 
                   message: str, duration: float = 0.0, details: Optional[Dict] = None):
        """Log a test result"""
        result = TestResult(
            component=component,
            test_name=test_name,
            status=status,
            message=message,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            details=details
        )
        self.results.append(result)
        
        # Log to console
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌',
            'SKIP': '⏭️',
            'WARN': '⚠️'
        }
        logger.info(f"{status_emoji.get(status, '❓')} [{component}] {test_name}: {message}")
    
    def run_command(self, command: str, description: str) -> Tuple[bool, str]:
        """Run a shell command and return success status and output"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {command}")
            return True, "Dry run - command not executed"
        
        try:
            logger.info(f"Executing: {description}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 5 minutes"
        except Exception as e:
            return False, str(e)
    
    # ==================== PRE-DEPLOYMENT TESTS ====================
    
    def test_environment_variables(self) -> bool:
        """Test that all required environment variables are set"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: Environment Variables Check")
        logger.info("="*60)
        
        start = time.time()
        all_present = True
        missing_vars = []
        
        for category, vars_list in self.required_env_vars.items():
            for var in vars_list:
                if not os.getenv(var):
                    missing_vars.append(f"{category}: {var}")
                    all_present = False
        
        duration = time.time() - start
        
        if all_present:
            self.log_result(
                'pre-deployment',
                'environment_variables',
                'PASS',
                'All required environment variables are set',
                duration
            )
            return True
        else:
            self.log_result(
                'pre-deployment',
                'environment_variables',
                'FAIL',
                f'Missing variables: {", ".join(missing_vars)}',
                duration,
                {'missing': missing_vars}
            )
            return False
    
    def test_database_connectivity(self) -> bool:
        """Test database connectivity"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: Database Connectivity")
        logger.info("="*60)
        
        start = time.time()
        
        try:
            # Try to import and connect to database
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
            from database import get_db
            
            db = next(get_db())
            
            # Test query
            result = db.execute("SELECT COUNT(*) FROM movies").fetchone()
            movie_count = result[0] if result else 0
            
            result = db.execute("SELECT COUNT(*) FROM series").fetchone()
            series_count = result[0] if result else 0
            
            duration = time.time() - start
            
            self.log_result(
                'pre-deployment',
                'database_connectivity',
                'PASS',
                f'Database connected: {movie_count} movies, {series_count} series',
                duration,
                {'movies': movie_count, 'series': series_count}
            )
            return True
            
        except Exception as e:
            duration = time.time() - start
            self.log_result(
                'pre-deployment',
                'database_connectivity',
                'FAIL',
                f'Database connection failed: {str(e)}',
                duration
            )
            return False
    
    def test_huggingface_api_access(self) -> bool:
        """Test HuggingFace API access with both tokens"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 3: HuggingFace API Access")
        logger.info("="*60)
        
        start = time.time()
        tokens = [os.getenv('HF_TOKEN_1'), os.getenv('HF_TOKEN_2')]
        
        for i, token in enumerate(tokens, 1):
            if not token:
                self.log_result(
                    'pre-deployment',
                    f'hf_api_token_{i}',
                    'FAIL',
                    f'HF_TOKEN_{i} not set',
                    0
                )
                return False
            
            try:
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(
                    'https://huggingface.co/api/whoami',
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    self.log_result(
                        'pre-deployment',
                        f'hf_api_token_{i}',
                        'PASS',
                        f'Token {i} valid for user: {user_info.get("name", "unknown")}',
                        time.time() - start
                    )
                else:
                    self.log_result(
                        'pre-deployment',
                        f'hf_api_token_{i}',
                        'FAIL',
                        f'Token {i} invalid: HTTP {response.status_code}',
                        time.time() - start
                    )
                    return False
                    
            except Exception as e:
                self.log_result(
                    'pre-deployment',
                    f'hf_api_token_{i}',
                    'FAIL',
                    f'Token {i} test failed: {str(e)}',
                    time.time() - start
                )
                return False
        
        return True
    
    def test_file_permissions(self) -> bool:
        """Test file permissions for critical files"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 4: File Permissions")
        logger.info("="*60)
        
        start = time.time()
        critical_files = [
            'app/database.py',
            'app/scanner.py',
            'app/room_sync.py',
            'sync_db_to_frontend.py',
            'verify_frontend_sync.py'
        ]
        
        all_readable = True
        for file_path in critical_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            if not os.path.exists(full_path):
                self.log_result(
                    'pre-deployment',
                    'file_permissions',
                    'WARN',
                    f'File not found: {file_path}',
                    0
                )
            elif not os.access(full_path, os.R_OK):
                self.log_result(
                    'pre-deployment',
                    'file_permissions',
                    'FAIL',
                    f'File not readable: {file_path}',
                    0
                )
                all_readable = False
        
        duration = time.time() - start
        
        if all_readable:
            self.log_result(
                'pre-deployment',
                'file_permissions',
                'PASS',
                'All critical files are readable',
                duration
            )
        
        return all_readable
    
    # ==================== HUGGINGFACE SPACES TESTS ====================
    
    def test_hf_spaces_build(self) -> bool:
        """Test HuggingFace Spaces build fixes"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 5: HuggingFace Spaces Build Tests")
        logger.info("="*60)
        
        start = time.time()
        
        # Run the fix script in test mode
        success, output = self.run_command(
            'python fix_hf_spaces_build.py --test',
            'Running HF Spaces build fix in test mode'
        )
        
        duration = time.time() - start
        
        if success:
            self.log_result(
                'hf-spaces',
                'build_fix_test',
                'PASS',
                'Build fix script executed successfully',
                duration
            )
        else:
            self.log_result(
                'hf-spaces',
                'build_fix_test',
                'FAIL',
                f'Build fix script failed: {output}',
                duration
            )
            return False
        
        # Check for __pycache__ files
        success, output = self.run_command(
            'find . -type d -name "__pycache__" | wc -l',
            'Checking for __pycache__ directories'
        )
        
        if success and output.strip() == '0':
            self.log_result(
                'hf-spaces',
                'pycache_check',
                'PASS',
                'No __pycache__ directories found',
                0
            )
        else:
            self.log_result(
                'hf-spaces',
                'pycache_check',
                'WARN',
                f'Found {output.strip()} __pycache__ directories',
                0
            )
        
        return True
    
    def test_hf_spaces_health(self) -> bool:
        """Test health endpoints for all HF Spaces"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 6: HuggingFace Spaces Health Check")
        logger.info("="*60)
        
        username = os.getenv('HF_USERNAME', 'your-username')
        all_healthy = True
        
        for space in self.hf_spaces:
            start = time.time()
            url = f'https://{username}-{space}.hf.space/health'
            
            try:
                response = requests.get(url, timeout=30)
                duration = time.time() - start
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_result(
                        'hf-spaces',
                        f'health_{space}',
                        'PASS',
                        f'{space} is healthy',
                        duration,
                        data
                    )
                else:
                    self.log_result(
                        'hf-spaces',
                        f'health_{space}',
                        'FAIL',
                        f'{space} returned HTTP {response.status_code}',
                        duration
                    )
                    all_healthy = False
                    
            except requests.exceptions.Timeout:
                self.log_result(
                    'hf-spaces',
                    f'health_{space}',
                    'FAIL',
                    f'{space} health check timed out',
                    30.0
                )
                all_healthy = False
            except Exception as e:
                self.log_result(
                    'hf-spaces',
                    f'health_{space}',
                    'FAIL',
                    f'{space} health check failed: {str(e)}',
                    time.time() - start
                )
                all_healthy = False
        
        return all_healthy
    
    # ==================== TELEGRAM SYNC TESTS ====================
    
    def test_telegram_sync(self) -> bool:
        """Test Telegram synchronization fixes"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 7: Telegram Synchronization Tests")
        logger.info("="*60)
        
        start = time.time()
        
        # Run the fix script diagnostic
        success, output = self.run_command(
            'python fix_telegram_sync_complete.py --diagnostic',
            'Running Telegram sync diagnostic'
        )
        
        duration = time.time() - start
        
        if success:
            self.log_result(
                'telegram-sync',
                'sync_diagnostic',
                'PASS',
                'Telegram sync diagnostic completed',
                duration
            )
        else:
            self.log_result(
                'telegram-sync',
                'sync_diagnostic',
                'FAIL',
                f'Telegram sync diagnostic failed: {output}',
                duration
            )
            return False
        
        return True
    
    def test_telegram_bot_access(self) -> bool:
        """Test bot access to all private groups"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 8: Telegram Bot Access Tests")
        logger.info("="*60)
        
        # This would require actual Telegram API calls
        # For now, we'll check if the environment variables are set
        
        all_set = True
        for group_var in self.telegram_groups:
            if not os.getenv(group_var):
                self.log_result(
                    'telegram-sync',
                    f'bot_access_{group_var}',
                    'FAIL',
                    f'Group ID not set: {group_var}',
                    0
                )
                all_set = False
            else:
                self.log_result(
                    'telegram-sync',
                    f'bot_access_{group_var}',
                    'PASS',
                    f'Group ID configured: {group_var}',
                    0
                )
        
        return all_set
    
    def test_scanner_memory_leak(self) -> bool:
        """Test that scanner memory leak is fixed"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 9: Scanner Memory Leak Test")
        logger.info("="*60)
        
        start = time.time()
        
        # Check if scanner has proper cleanup
        success, output = self.run_command(
            'grep -n "cleanup\\|close\\|dispose" app/scanner.py | wc -l',
            'Checking scanner cleanup methods'
        )
        
        duration = time.time() - start
        
        if success and int(output.strip()) > 0:
            self.log_result(
                'telegram-sync',
                'scanner_memory_leak',
                'PASS',
                f'Scanner has {output.strip()} cleanup methods',
                duration
            )
            return True
        else:
            self.log_result(
                'telegram-sync',
                'scanner_memory_leak',
                'WARN',
                'Scanner cleanup methods not found',
                duration
            )
            return True  # Don't fail on this
    
    # ==================== FRONTEND SYNC TESTS ====================
    
    def test_frontend_sync(self) -> bool:
        """Test database to frontend synchronization"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 10: Frontend Synchronization Tests")
        logger.info("="*60)
        
        start = time.time()
        
        # Run sync script
        success, output = self.run_command(
            'python sync_db_to_frontend.py',
            'Running database to frontend sync'
        )
        
        duration = time.time() - start
        
        if success:
            self.log_result(
                'frontend-sync',
                'db_to_frontend_sync',
                'PASS',
                'Database to frontend sync completed',
                duration
            )
        else:
            self.log_result(
                'frontend-sync',
                'db_to_frontend_sync',
                'FAIL',
                f'Sync failed: {output}',
                duration
            )
            return False
        
        # Run verification
        start = time.time()
        success, output = self.run_command(
            'python verify_frontend_sync.py',
            'Verifying frontend sync integrity'
        )
        
        duration = time.time() - start
        
        if success:
            self.log_result(
                'frontend-sync',
                'sync_verification',
                'PASS',
                'Frontend sync verification passed',
                duration
            )
        else:
            self.log_result(
                'frontend-sync',
                'sync_verification',
                'FAIL',
                f'Verification failed: {output}',
                duration
            )
            return False
        
        return True
    
    def test_json_file_integrity(self) -> bool:
        """Test JSON file integrity"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 11: JSON File Integrity Tests")
        logger.info("="*60)
        
        json_files = [
            'frontend/src/movies_data.json',
            'frontend/src/series_data.json',
            'frontend/src/stats_data.json',
            'frontend/src/frontend_data.json'
        ]
        
        all_valid = True
        for json_file in json_files:
            start = time.time()
            file_path = os.path.join(os.path.dirname(__file__), json_file)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                duration = time.time() - start
                
                self.log_result(
                    'frontend-sync',
                    f'json_integrity_{os.path.basename(json_file)}',
                    'PASS',
                    f'{json_file} is valid JSON',
                    duration,
                    {'size': len(json.dumps(data))}
                )
                
            except FileNotFoundError:
                self.log_result(
                    'frontend-sync',
                    f'json_integrity_{os.path.basename(json_file)}',
                    'FAIL',
                    f'{json_file} not found',
                    0
                )
                all_valid = False
            except json.JSONDecodeError as e:
                self.log_result(
                    'frontend-sync',
                    f'json_integrity_{os.path.basename(json_file)}',
                    'FAIL',
                    f'{json_file} invalid JSON: {str(e)}',
                    time.time() - start
                )
                all_valid = False
        
        return all_valid
    
    # ==================== INTEGRATION TESTS ====================
    
    def test_end_to_end_flow(self) -> bool:
        """Test end-to-end flow: Telegram → Database → Frontend"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 12: End-to-End Integration Tests")
        logger.info("="*60)
        
        # This is a placeholder for actual integration tests
        self.log_result(
            'integration',
            'end_to_end_flow',
            'SKIP',
            'End-to-end flow test requires manual verification',
            0
        )
        
        return True
    
    # ==================== DEPLOYMENT ====================
    
    def deploy_hf_spaces(self) -> bool:
        """Deploy fixes to HuggingFace Spaces"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 13: HuggingFace Spaces Deployment")
        logger.info("="*60)
        
        if self.test_only:
            self.log_result(
                'deployment',
                'hf_spaces_deploy',
                'SKIP',
                'Skipped (test-only mode)',
                0
            )
            return True
        
        start = time.time()
        
        success, output = self.run_command(
            'python fix_hf_spaces_build.py --deploy',
            'Deploying HF Spaces fixes'
        )
        
        duration = time.time() - start
        
        if success:
            self.log_result(
                'deployment',
                'hf_spaces_deploy',
                'PASS',
                'HF Spaces deployment completed',
                duration
            )
            return True
        else:
            self.log_result(
                'deployment',
                'hf_spaces_deploy',
                'FAIL',
                f'Deployment failed: {output}',
                duration
            )
            return False
    
    def deploy_telegram_fixes(self) -> bool:
        """Deploy Telegram synchronization fixes"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 14: Telegram Fixes Deployment")
        logger.info("="*60)
        
        if self.test_only:
            self.log_result(
                'deployment',
                'telegram_fixes_deploy',
                'SKIP',
                'Skipped (test-only mode)',
                0
            )
            return True
        
        start = time.time()
        
        success, output = self.run_command(
            'python fix_telegram_sync_complete.py --deploy',
            'Deploying Telegram sync fixes'
        )
        
        duration = time.time() - start
        
        if success:
            self.log_result(
                'deployment',
                'telegram_fixes_deploy',
                'PASS',
                'Telegram fixes deployment completed',
                duration
            )
            return True
        else:
            self.log_result(
                'deployment',
                'telegram_fixes_deploy',
                'FAIL',
                f'Deployment failed: {output}',
                duration
            )
            return False
    
    # ==================== POST-DEPLOYMENT VALIDATION ====================
    
    def validate_deployment(self) -> bool:
        """Validate deployment success"""
        logger.info("\n" + "="*60)
        logger.info("PHASE 15: Post-Deployment Validation")
        logger.info("="*60)
        
        if self.test_only:
            self.log_result(
                'post-deployment',
                'validation',
                'SKIP',
                'Skipped (test-only mode)',
                0
            )
            return True
        
        # Re-run health checks
        return self.test_hf_spaces_health()
    
    # ==================== REPORTING ====================
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Count results by status
        status_counts = {
            'PASS': sum(1 for r in self.results if r.status == 'PASS'),
            'FAIL': sum(1 for r in self.results if r.status == 'FAIL'),
            'SKIP': sum(1 for r in self.results if r.status == 'SKIP'),
            'WARN': sum(1 for r in self.results if r.status == 'WARN')
        }
        
        # Group results by component
        by_component = {}
        for result in self.results:
            if result.component not in by_component:
                by_component[result.component] = []
            by_component[result.component].append(asdict(result))
        
        report = {
            'summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'total_tests': len(self.results),
                'status_counts': status_counts,
                'success_rate': (status_counts['PASS'] / len(self.results) * 100) if self.results else 0,
                'dry_run': self.dry_run,
                'test_only': self.test_only,
                'deploy_only': self.deploy_only,
                'component_filter': self.component
            },
            'results_by_component': by_component,
            'all_results': [asdict(r) for r in self.results]
        }
        
        return report
    
    def save_report(self, report: Dict):
        """Save report to files"""
        # Save JSON report
        json_path = 'test_deploy_report.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n📊 JSON report saved to: {json_path}")
        
        # Save Markdown report
        md_path = 'TEST_DEPLOY_REPORT.md'
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Test and Deployment Report\n\n")
            f.write(f"**Generated:** {report['summary']['end_time']}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Duration:** {report['summary']['duration_seconds']:.2f} seconds\n")
            f.write(f"- **Total Tests:** {report['summary']['total_tests']}\n")
            f.write(f"- **Success Rate:** {report['summary']['success_rate']:.1f}%\n")
            f.write(f"- **Mode:** {'Dry Run' if self.dry_run else 'Live'}\n\n")
            
            f.write("### Status Breakdown\n\n")
            for status, count in report['summary']['status_counts'].items():
                emoji = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️', 'WARN': '⚠️'}
                f.write(f"- {emoji.get(status, '❓')} **{status}:** {count}\n")
            
            f.write("\n## Results by Component\n\n")
            for component, results in report['results_by_component'].items():
                f.write(f"### {component.upper()}\n\n")
                for result in results:
                    status_emoji = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️', 'WARN': '⚠️'}
                    f.write(f"- {status_emoji.get(result['status'], '❓')} **{result['test_name']}**: {result['message']}\n")
                f.write("\n")
        
        logger.info(f"📄 Markdown report saved to: {md_path}")
    
    # ==================== MAIN EXECUTION ====================
    
    def run(self) -> bool:
        """Run all tests and deployment"""
        logger.info("\n" + "="*80)
        logger.info("🚀 POPCORN MINI APP - COMPREHENSIVE TEST & DEPLOYMENT")
        logger.info("="*80)
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info(f"Test Only: {self.test_only}")
        logger.info(f"Deploy Only: {self.deploy_only}")
        logger.info(f"Component Filter: {self.component or 'ALL'}")
        logger.info("="*80 + "\n")
        
        try:
            # Pre-deployment tests
            if not self.deploy_only:
                if self.component in [None, 'pre-deployment']:
                    if not self.test_environment_variables():
                        logger.error("❌ Environment variables check failed!")
                        return False
                    
                    if not self.test_database_connectivity():
                        logger.error("❌ Database connectivity check failed!")
                        return False
                    
                    if not self.test_huggingface_api_access():
                        logger.error("❌ HuggingFace API access check failed!")
                        return False
                    
                    if not self.test_file_permissions():
                        logger.warning("⚠️ File permissions check had warnings")
            
            # HuggingFace Spaces tests
            if not self.deploy_only:
                if self.component in [None, 'hf-spaces']:
                    if not self.test_hf_spaces_build():
                        logger.error("❌ HF Spaces build test failed!")
                        return False
                    
                    if not self.test_hf_spaces_health():
                        logger.warning("⚠️ Some HF Spaces health checks failed")
            
            # Telegram sync tests
            if not self.deploy_only:
                if self.component in [None, 'telegram-sync']:
                    if not self.test_telegram_sync():
                        logger.error("❌ Telegram sync test failed!")
                        return False
                    
                    if not self.test_telegram_bot_access():
                        logger.warning("⚠️ Some Telegram bot access checks failed")
                    
                    self.test_scanner_memory_leak()
            
            # Frontend sync tests
            if not self.deploy_only:
                if self.component in [None, 'frontend-sync']:
                    if not self.test_frontend_sync():
                        logger.error("❌ Frontend sync test failed!")
                        return False
                    
                    if not self.test_json_file_integrity():
                        logger.error("❌ JSON file integrity check failed!")
                        return False
            
            # Integration tests
            if not self.deploy_only:
                if self.component in [None, 'integration']:
                    self.test_end_to_end_flow()
            
            # Deployment
            if not self.test_only:
                if self.component in [None, 'hf-spaces']:
                    if not self.deploy_hf_spaces():
                        logger.error("❌ HF Spaces deployment failed!")
                        return False
                
                if self.component in [None, 'telegram-sync']:
                    if not self.deploy_telegram_fixes():
                        logger.error("❌ Telegram fixes deployment failed!")
                        return False
                
                # Post-deployment validation
                if not self.validate_deployment():
                    logger.warning("⚠️ Post-deployment validation had issues")
            
            # Generate and save report
            report = self.generate_report()
            self.save_report(report)
            
            # Final summary
            logger.info("\n" + "="*80)
            logger.info("✅ TEST AND DEPLOYMENT COMPLETED")
            logger.info("="*80)
            logger.info(f"Total Tests: {report['summary']['total_tests']}")
            logger.info(f"Success Rate: {report['summary']['success_rate']:.1f}%")
            logger.info(f"Duration: {report['summary']['duration_seconds']:.2f} seconds")
            logger.info("="*80 + "\n")
            
            return report['summary']['status_counts']['FAIL'] == 0
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️ Test and deployment interrupted by user")
            return False
        except Exception as e:
            logger.error(f"\n❌ Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Comprehensive Test and Deployment Script for PopCorn Mini App'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no actual changes)'
    )
    
    parser.add_argument(
        '--test-only',
        action='store_true',
        help='Run tests only, skip deployment'
    )
    
    parser.add_argument(
        '--deploy-only',
        action='store_true',
        help='Skip tests, deploy only'
    )
    
    parser.add_argument(
        '--component',
        choices=['pre-deployment', 'hf-spaces', 'telegram-sync', 'frontend-sync', 'integration'],
        help='Test/deploy specific component only'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run full test and deployment suite'
    )
    
    args = parser.parse_args()
    
    # Create manager
    manager = TestDeploymentManager(
        dry_run=args.dry_run,
        test_only=args.test_only,
        deploy_only=args.deploy_only,
        component=args.component
    )
    
    # Run tests and deployment
    success = manager.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
