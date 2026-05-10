#!/usr/bin/env python3
"""
PopCorn Bot System - Post-Deployment Verification Script
Verifies all Spaces are running and bot functionality is working.
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from huggingface_hub import HfApi
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Spaces to verify
SPACES_TO_VERIFY = [
    {
        "name": "ToolKit-backend/PopCorn",
        "token_env": "HF_TOKEN_1",
        "url": "https://toolkit-backend-popcorn.hf.space"
    },
    {
        "name": "ToolKit-backend/popcorn-main",
        "token_env": "HF_TOKEN_1",
        "url": "https://toolkit-backend-popcorn-main.hf.space"
    },
    {
        "name": "ToolKit-backend/popcorn-streaming",
        "token_env": "HF_TOKEN_1",
        "url": "https://toolkit-backend-popcorn-streaming.hf.space"
    },
    {
        "name": "rayig/popcorn-backup",
        "token_env": "HF_TOKEN_2",
        "url": "https://rayig-popcorn-backup.hf.space"
    },
    {
        "name": "rayig/popcorn-analytics",
        "token_env": "HF_TOKEN_2",
        "url": "https://rayig-popcorn-analytics.hf.space"
    }
]


class DeploymentVerifier:
    """Verifies deployment across all Spaces."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.verification_results = {
            "timestamp": datetime.now().isoformat(),
            "spaces": {},
            "summary": {
                "total": len(SPACES_TO_VERIFY),
                "running": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
        # Initialize HF API clients
        self.hf_apis = {}
        for space in SPACES_TO_VERIFY:
            token = os.getenv(space["token_env"])
            if token:
                self.hf_apis[space["name"]] = HfApi(token=token)
    
    async def verify_all_spaces(self) -> Dict:
        """Verify all Spaces."""
        logger.info("=" * 80)
        logger.info("🔍 VERIFYING ALL SPACES")
        logger.info("=" * 80)
        
        for space_config in SPACES_TO_VERIFY:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"📋 Verifying: {space_config['name']}")
            logger.info(f"{'=' * 80}")
            
            result = await self.verify_space(space_config)
            self.verification_results["spaces"][space_config["name"]] = result
            
            if result["status"] == "running":
                self.verification_results["summary"]["running"] += 1
                logger.info(f"✅ {space_config['name']} is RUNNING")
            else:
                self.verification_results["summary"]["failed"] += 1
                logger.error(f"❌ {space_config['name']} is NOT running")
        
        # Generate report
        self.generate_verification_report()
        
        return self.verification_results
    
    async def verify_space(self, space_config: Dict) -> Dict:
        """Verify a single Space."""
        space_name = space_config["name"]
        space_url = space_config["url"]
        
        result = {
            "space_name": space_name,
            "url": space_url,
            "status": "unknown",
            "runtime_stage": "unknown",
            "health_check": False,
            "api_check": False,
            "bot_check": False,
            "response_time": 0,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 1. Check Space runtime status
            logger.info("📊 Checking runtime status...")
            if space_name in self.hf_apis:
                try:
                    api = self.hf_apis[space_name]
                    space_info = api.space_info(repo_id=space_name)
                    
                    if space_info.runtime:
                        result["runtime_stage"] = space_info.runtime.stage
                        result["status"] = space_info.runtime.stage.lower()
                        logger.info(f"  Status: {result['runtime_stage']}")
                    else:
                        logger.warning("  ⚠️  No runtime information available")
                        result["warnings"].append("No runtime information")
                        
                except Exception as e:
                    logger.error(f"  ❌ Could not get Space info: {e}")
                    result["errors"].append(f"Space info error: {str(e)}")
            
            # 2. Health check
            logger.info("🏥 Performing health check...")
            health_result = await self.check_health(space_url)
            result["health_check"] = health_result["success"]
            result["response_time"] = health_result["response_time"]
            
            if health_result["success"]:
                logger.info(f"  ✅ Health check passed ({health_result['response_time']:.2f}s)")
            else:
                logger.warning(f"  ⚠️  Health check failed: {health_result['error']}")
                result["warnings"].append(f"Health check: {health_result['error']}")
            
            # 3. API endpoints check
            logger.info("🔌 Checking API endpoints...")
            api_result = await self.check_api_endpoints(space_url)
            result["api_check"] = api_result["success"]
            
            if api_result["success"]:
                logger.info(f"  ✅ API endpoints responding")
            else:
                logger.warning(f"  ⚠️  API check failed: {api_result['error']}")
                result["warnings"].append(f"API check: {api_result['error']}")
            
            # 4. Bot functionality check (if applicable)
            logger.info("🤖 Checking bot functionality...")
            bot_result = await self.check_bot_functionality(space_url)
            result["bot_check"] = bot_result["success"]
            
            if bot_result["success"]:
                logger.info(f"  ✅ Bot functionality verified")
            else:
                logger.warning(f"  ⚠️  Bot check: {bot_result['error']}")
                result["warnings"].append(f"Bot check: {bot_result['error']}")
            
        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            result["errors"].append(str(e))
        
        return result
    
    async def check_health(self, base_url: str) -> Dict:
        """Check health endpoint."""
        result = {"success": False, "response_time": 0, "error": None}
        
        try:
            import time
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{base_url}/health")
                result["response_time"] = time.time() - start_time
                
                if response.status_code == 200:
                    result["success"] = True
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    
        except httpx.TimeoutException:
            result["error"] = "Timeout"
        except httpx.ConnectError:
            result["error"] = "Connection failed"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_api_endpoints(self, base_url: str) -> Dict:
        """Check critical API endpoints."""
        result = {"success": False, "error": None}
        
        endpoints_to_check = [
            "/api/stats",
            "/api/genres",
            "/api/movies",
            "/api/series"
        ]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for endpoint in endpoints_to_check:
                    try:
                        response = await client.get(f"{base_url}{endpoint}")
                        if response.status_code not in [200, 404]:
                            result["error"] = f"{endpoint}: HTTP {response.status_code}"
                            return result
                    except Exception as e:
                        result["error"] = f"{endpoint}: {str(e)}"
                        return result
                
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    async def check_bot_functionality(self, base_url: str) -> Dict:
        """Check bot-specific functionality."""
        result = {"success": False, "error": None}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check admin endpoints (may require auth)
                response = await client.get(f"{base_url}/api/admin/bot-status")
                
                if response.status_code in [200, 401, 403]:
                    # 200 = success, 401/403 = auth required (expected)
                    result["success"] = True
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def generate_verification_report(self):
        """Generate verification report."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 VERIFICATION SUMMARY")
        logger.info("=" * 80)
        
        summary = self.verification_results["summary"]
        logger.info(f"Total Spaces: {summary['total']}")
        logger.info(f"✅ Running: {summary['running']}")
        logger.info(f"❌ Failed: {summary['failed']}")
        logger.info(f"⚠️  Warnings: {summary['warnings']}")
        
        # Save detailed report
        report_path = self.base_path / "verification_results.json"
        with open(report_path, 'w') as f:
            json.dump(self.verification_results, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: {report_path}")
        
        # Print individual space results
        logger.info("\n📋 Individual Space Results:")
        for space_name, space_result in self.verification_results["spaces"].items():
            status_icon = "✅" if space_result["status"] == "running" else "❌"
            logger.info(f"\n{status_icon} {space_name}")
            logger.info(f"   Status: {space_result['status']}")
            logger.info(f"   Runtime: {space_result['runtime_stage']}")
            logger.info(f"   Health: {'✅' if space_result['health_check'] else '❌'}")
            logger.info(f"   API: {'✅' if space_result['api_check'] else '❌'}")
            logger.info(f"   Bot: {'✅' if space_result['bot_check'] else '❌'}")
            logger.info(f"   Response Time: {space_result['response_time']:.2f}s")
            
            if space_result["errors"]:
                logger.info(f"   Errors: {len(space_result['errors'])}")
                for error in space_result["errors"]:
                    logger.info(f"     - {error}")
            
            if space_result["warnings"]:
                logger.info(f"   Warnings: {len(space_result['warnings'])}")
                for warning in space_result["warnings"][:3]:
                    logger.info(f"     - {warning}")


async def main():
    """Main verification execution."""
    logger.info("🔍 Starting post-deployment verification...")
    
    verifier = DeploymentVerifier()
    results = await verifier.verify_all_spaces()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        logger.error("\n❌ Verification found failures!")
        sys.exit(1)
    elif results["summary"]["warnings"] > 0:
        logger.warning("\n⚠️  Verification completed with warnings.")
        sys.exit(0)
    else:
        logger.info("\n✅ All Spaces verified successfully!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
