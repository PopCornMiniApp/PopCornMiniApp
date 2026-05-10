#!/usr/bin/env python3
"""
Production Deployment Script for PopCorn Distributed System
Deploys multiple Spaces and Datasets to HuggingFace for load balancing
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from huggingface_hub import HfApi, create_repo, upload_file, upload_folder
from huggingface_hub.utils import RepositoryNotFoundError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductionDeployer:
    """Handles production deployment to HuggingFace"""
    
    def __init__(self):
        self.api = None
        self.tokens = self._load_tokens()
        self.deployment_config = self._load_deployment_config()
        
    def _load_tokens(self) -> Dict[str, str]:
        """Load HuggingFace tokens from environment"""
        tokens = {}
        
        # Load main token
        main_token = os.getenv('HF_TOKEN')
        if main_token:
            tokens['main'] = main_token
            tokens['ToolKit-backend'] = main_token  # Map to account name
            logger.info("✅ Main HF token loaded")
        else:
            logger.error("❌ HF_TOKEN not found in environment")
            
        # Load additional tokens
        token_2 = os.getenv('HF_TOKEN_2')
        if token_2:
            tokens['account_2'] = token_2
            tokens['rayig'] = token_2  # Map to account name
            logger.info("✅ HF_TOKEN_2 loaded")
            
        for i in range(3, 6):
            token = os.getenv(f'HF_TOKEN_{i}')
            if token:
                tokens[f'account_{i}'] = token
                logger.info(f"✅ HF_TOKEN_{i} loaded")
                
        return tokens
    
    def _load_deployment_config(self) -> Dict:
        """Load deployment configuration"""
        config_file = Path('hf_optimization_strategy.json')
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            logger.warning("⚠️ hf_optimization_strategy.json not found, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Get default deployment configuration"""
        return {
            "distribution_strategy": {
                "spaces": {
                    "total_spaces": 3,
                    "distribution": [
                        {
                            "account": "main",
                            "spaces": [
                                {
                                    "name": "PopCorn-Main",
                                    "purpose": "Primary API and Frontend",
                                    "services": ["api", "frontend", "streaming"]
                                }
                            ]
                        },
                        {
                            "account": "account-2",
                            "spaces": [
                                {
                                    "name": "PopCorn-Streaming",
                                    "purpose": "Dedicated Streaming Service",
                                    "services": ["streaming", "cache"]
                                }
                            ]
                        },
                        {
                            "account": "account-3",
                            "spaces": [
                                {
                                    "name": "PopCorn-Analytics",
                                    "purpose": "Analytics and Monitoring",
                                    "services": ["analytics", "monitoring"]
                                }
                            ]
                        }
                    ]
                },
                "datasets": {
                    "total_datasets": 5,
                    "distribution": [
                        {
                            "account": "main",
                            "datasets": [
                                {
                                    "name": "PopCornDB-Main",
                                    "purpose": "Primary Database",
                                    "tables": ["movies", "series", "episodes"]
                                }
                            ]
                        },
                        {
                            "account": "account-2",
                            "datasets": [
                                {
                                    "name": "PopCornDB-Users",
                                    "purpose": "User Data",
                                    "tables": ["users", "watch_history", "preferences"]
                                },
                                {
                                    "name": "PopCornDB-Analytics",
                                    "purpose": "Analytics Data",
                                    "tables": ["analytics", "logs"]
                                }
                            ]
                        },
                        {
                            "account": "account-3",
                            "datasets": [
                                {
                                    "name": "PopCornDB-Cache",
                                    "purpose": "Cache Data",
                                    "tables": ["cache", "sessions"]
                                },
                                {
                                    "name": "PopCornDB-Backup",
                                    "purpose": "Backup Storage",
                                    "tables": ["backups"]
                                }
                            ]
                        }
                    ]
                }
            }
        }
    
    def deploy_space(self, account: str, space_config: Dict) -> bool:
        """Deploy a single Space"""
        try:
            token = self.tokens.get(account)
            if not token:
                logger.error(f"❌ No token found for account: {account}")
                return False
            
            api = HfApi(token=token)
            space_name = space_config['name']
            
            # Get username from token
            user_info = api.whoami()
            username = user_info['name']
            repo_id = f"{username}/{space_name}"
            
            logger.info(f"🚀 Deploying Space: {repo_id}")
            
            # Create Space repository
            try:
                create_repo(
                    repo_id=repo_id,
                    repo_type="space",
                    space_sdk="docker",
                    token=token,
                    exist_ok=True
                )
                logger.info(f"✅ Space repository created: {repo_id}")
            except Exception as e:
                logger.warning(f"⚠️ Space may already exist: {e}")
            
            # Upload Dockerfile
            dockerfile_path = Path('Dockerfile')
            if dockerfile_path.exists():
                upload_file(
                    path_or_fileobj=str(dockerfile_path),
                    path_in_repo="Dockerfile",
                    repo_id=repo_id,
                    repo_type="space",
                    token=token
                )
                logger.info(f"✅ Dockerfile uploaded to {repo_id}")
            
            # Upload requirements.txt
            requirements_path = Path('requirements.txt')
            if requirements_path.exists():
                upload_file(
                    path_or_fileobj=str(requirements_path),
                    path_in_repo="requirements.txt",
                    repo_id=repo_id,
                    repo_type="space",
                    token=token
                )
                logger.info(f"✅ requirements.txt uploaded to {repo_id}")
            
            # Upload app directory
            app_path = Path('app')
            if app_path.exists():
                upload_folder(
                    folder_path=str(app_path),
                    path_in_repo="app",
                    repo_id=repo_id,
                    repo_type="space",
                    token=token
                )
                logger.info(f"✅ app/ directory uploaded to {repo_id}")
            
            # Upload frontend if this is main space
            if 'frontend' in space_config.get('services', []):
                frontend_path = Path('frontend')
                if frontend_path.exists():
                    upload_folder(
                        folder_path=str(frontend_path),
                        path_in_repo="frontend",
                        repo_id=repo_id,
                        repo_type="space",
                        token=token
                    )
                    logger.info(f"✅ frontend/ directory uploaded to {repo_id}")
            
            # Create README
            readme_content = self._generate_space_readme(space_config)
            with open('temp_readme.md', 'w') as f:
                f.write(readme_content)
            
            upload_file(
                path_or_fileobj='temp_readme.md',
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="space",
                token=token
            )
            os.remove('temp_readme.md')
            logger.info(f"✅ README.md uploaded to {repo_id}")
            
            logger.info(f"🎉 Space deployed successfully: {repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to deploy Space {space_config['name']}: {e}")
            return False
    
    def deploy_dataset(self, account: str, dataset_config: Dict) -> bool:
        """Deploy a single Dataset"""
        try:
            token = self.tokens.get(account)
            if not token:
                logger.error(f"❌ No token found for account: {account}")
                return False
            
            api = HfApi(token=token)
            dataset_name = dataset_config['name']
            
            # Get username from token
            user_info = api.whoami()
            username = user_info['name']
            repo_id = f"{username}/{dataset_name}"
            
            logger.info(f"📦 Deploying Dataset: {repo_id}")
            
            # Create Dataset repository
            try:
                create_repo(
                    repo_id=repo_id,
                    repo_type="dataset",
                    token=token,
                    exist_ok=True
                )
                logger.info(f"✅ Dataset repository created: {repo_id}")
            except Exception as e:
                logger.warning(f"⚠️ Dataset may already exist: {e}")
            
            # Upload database file if exists
            db_path = Path('popcorn.db')
            if db_path.exists():
                upload_file(
                    path_or_fileobj=str(db_path),
                    path_in_repo="popcorn.db",
                    repo_id=repo_id,
                    repo_type="dataset",
                    token=token
                )
                logger.info(f"✅ Database uploaded to {repo_id}")
            
            # Create README
            readme_content = self._generate_dataset_readme(dataset_config)
            with open('temp_readme.md', 'w') as f:
                f.write(readme_content)
            
            upload_file(
                path_or_fileobj='temp_readme.md',
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                token=token
            )
            os.remove('temp_readme.md')
            logger.info(f"✅ README.md uploaded to {repo_id}")
            
            logger.info(f"🎉 Dataset deployed successfully: {repo_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to deploy Dataset {dataset_config['name']}: {e}")
            return False
    
    def _generate_space_readme(self, space_config: Dict) -> str:
        """Generate README for Space"""
        return f"""---
title: {space_config['name']}
emoji: 🍿
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# {space_config['name']}

## Purpose
{space_config['purpose']}

## Services
{', '.join(space_config.get('services', []))}

## Part of PopCorn Distributed System
This Space is part of the PopCorn Mini App distributed system for load balancing and high availability.

## Auto-deployed
This Space is automatically deployed and managed by the PopCorn deployment system.
"""
    
    def _generate_dataset_readme(self, dataset_config: Dict) -> str:
        """Generate README for Dataset"""
        return f"""---
title: {dataset_config['name']}
emoji: 📦
colorFrom: blue
colorTo: green
---

# {dataset_config['name']}

## Purpose
{dataset_config['purpose']}

## Tables
{', '.join(dataset_config.get('tables', []))}

## Part of PopCorn Distributed System
This Dataset is part of the PopCorn Mini App distributed database system.

## Auto-deployed
This Dataset is automatically deployed and managed by the PopCorn deployment system.
"""
    
    def deploy_all(self) -> Dict[str, Any]:
        """Deploy all Spaces and Datasets"""
        results = {
            'spaces': {'total': 0, 'success': 0, 'failed': 0, 'details': []},
            'datasets': {'total': 0, 'success': 0, 'failed': 0, 'details': []}
        }
        
        logger.info("=" * 80)
        logger.info("🚀 Starting Production Deployment")
        logger.info("=" * 80)
        
        # Deploy Spaces
        logger.info("\n📍 Deploying Spaces...")
        spaces_config = self.deployment_config['distribution_strategy']['spaces']['distribution']
        
        for account_config in spaces_config:
            account = account_config['account']
            for space_config in account_config['spaces']:
                results['spaces']['total'] += 1
                success = self.deploy_space(account, space_config)
                
                if success:
                    results['spaces']['success'] += 1
                    results['spaces']['details'].append({
                        'name': space_config['name'],
                        'account': account,
                        'status': 'success'
                    })
                else:
                    results['spaces']['failed'] += 1
                    results['spaces']['details'].append({
                        'name': space_config['name'],
                        'account': account,
                        'status': 'failed'
                    })
                
                time.sleep(2)  # Rate limiting
        
        # Deploy Datasets
        logger.info("\n📍 Deploying Datasets...")
        datasets_config = self.deployment_config['distribution_strategy']['datasets']['distribution']
        
        for account_config in datasets_config:
            account = account_config['account']
            for dataset_config in account_config['datasets']:
                results['datasets']['total'] += 1
                success = self.deploy_dataset(account, dataset_config)
                
                if success:
                    results['datasets']['success'] += 1
                    results['datasets']['details'].append({
                        'name': dataset_config['name'],
                        'account': account,
                        'status': 'success'
                    })
                else:
                    results['datasets']['failed'] += 1
                    results['datasets']['details'].append({
                        'name': dataset_config['name'],
                        'account': account,
                        'status': 'failed'
                    })
                
                time.sleep(2)  # Rate limiting
        
        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 Deployment Summary")
        logger.info("=" * 80)
        logger.info(f"\n🚀 Spaces:")
        logger.info(f"   Total: {results['spaces']['total']}")
        logger.info(f"   ✅ Success: {results['spaces']['success']}")
        logger.info(f"   ❌ Failed: {results['spaces']['failed']}")
        
        logger.info(f"\n📦 Datasets:")
        logger.info(f"   Total: {results['datasets']['total']}")
        logger.info(f"   ✅ Success: {results['datasets']['success']}")
        logger.info(f"   ❌ Failed: {results['datasets']['failed']}")
        
        # Save results
        with open('deployment_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n💾 Results saved to deployment_results.json")
        
        return results


def main():
    """Main deployment function"""
    try:
        deployer = ProductionDeployer()
        results = deployer.deploy_all()
        
        # Exit with appropriate code
        if results['spaces']['failed'] > 0 or results['datasets']['failed'] > 0:
            logger.warning("\n⚠️ Deployment completed with some failures")
            sys.exit(1)
        else:
            logger.info("\n🎉 Deployment completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
