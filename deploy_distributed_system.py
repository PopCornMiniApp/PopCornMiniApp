#!/usr/bin/env python3
"""
Deploy Distributed System to HuggingFace
Creates multiple Spaces and Datasets for load balancing and high availability
"""

import os
import sys
import json
import time
import logging
from huggingface_hub import HfApi, create_repo, upload_file, upload_folder
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DistributedSystemDeployer:
    """Deploy distributed system to HuggingFace"""
    
    def __init__(self):
        self.hf_api = HfApi()
        self.accounts = {
            "primary": {
                "name": "ToolKit-backend",
                "token": os.getenv("HF_TOKEN", "")
            },
            "secondary": {
                "name": "rayig",
                "token": os.getenv("HF_TOKEN_2", "")
            }
        }
        
        # Load strategy
        with open("hf_optimization_strategy.json", 'r') as f:
            self.strategy = json.load(f)
    
    def create_space(self, account: str, space_name: str, space_config: dict) -> bool:
        """Create a new Space"""
        try:
            token = self.accounts[account]["token"]
            account_name = self.accounts[account]["name"]
            repo_id = f"{account_name}/{space_name}"
            
            logger.info(f"Creating Space: {repo_id}")
            
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
                logger.warning(f"Space may already exist: {str(e)}")
            
            # Upload Dockerfile
            dockerfile_content = self._generate_dockerfile(space_config)
            with open("/tmp/Dockerfile", 'w') as f:
                f.write(dockerfile_content)
            
            upload_file(
                path_or_fileobj="/tmp/Dockerfile",
                path_in_repo="Dockerfile",
                repo_id=repo_id,
                repo_type="space",
                token=token
            )
            
            # Upload requirements.txt
            upload_file(
                path_or_fileobj="requirements.txt",
                path_in_repo="requirements.txt",
                repo_id=repo_id,
                repo_type="space",
                token=token
            )
            
            # Upload .env
            upload_file(
                path_or_fileobj=".env",
                path_in_repo=".env",
                repo_id=repo_id,
                repo_type="space",
                token=token
            )
            
            # Upload app files based on services
            self._upload_app_files(repo_id, space_config, token)
            
            logger.info(f"✅ Space deployed successfully: {repo_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to create Space {space_name}: {str(e)}")
            return False
    
    def _generate_dockerfile(self, space_config: dict) -> str:
        """Generate Dockerfile based on Space configuration"""
        services = space_config.get('services', [])
        
        dockerfile = """FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p data logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port
EXPOSE 7860

"""
        
        # Add service-specific commands
        if "API" in services and "Frontend" in services:
            dockerfile += """# Start main application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
"""
        elif "Stream Handler" in services:
            dockerfile += """# Start streaming service
CMD ["python", "-m", "app.stream"]
"""
        elif "Backup Manager" in services:
            dockerfile += """# Start backup service
CMD ["python", "-m", "app.backup_manager"]
"""
        elif "Analytics" in services:
            dockerfile += """# Start analytics service
CMD ["python", "-m", "app.analytics"]
"""
        else:
            dockerfile += """# Start default service
CMD ["python", "-m", "app.main"]
"""
        
        return dockerfile
    
    def _upload_app_files(self, repo_id: str, space_config: dict, token: str) -> None:
        """Upload relevant app files based on services"""
        services = space_config.get('services', [])
        
        # Core files always needed
        core_files = [
            "app/__init__.py",
            "app/config.py",
            "app/database.py",
            "app/exceptions.py",
            "app/multi_account_manager.py",
            "app/multi_space_manager.py",
            "app/multi_dataset_manager.py"
        ]
        
        # Service-specific files
        service_files = {
            "API": ["app/main.py", "app/error_handlers.py"],
            "Frontend": ["static/", "frontend/"],
            "WebSocket": ["app/websocket_handler.py", "app/websocket_manager.py"],
            "Stream Handler": ["app/stream.py", "app/advanced_streaming.py"],
            "Video Processing": ["app/stream.py"],
            "Cache": ["app/cache.py", "app/smart_cache.py"],
            "Backup Manager": ["app/backup_manager.py", "app/db_manager.py"],
            "Sync Bot": ["app/sync_bot.py", "app/smart_sync.py", "app/multi_group_sync.py"],
            "Mirror Manager": ["app/mirror_manager.py"],
            "Analytics": ["app/analytics.py", "app/user_tracking.py"],
            "Health Monitor": ["app/health_monitor.py", "app/performance_monitor.py"],
            "User Tracking": ["app/user_tracking.py"]
        }
        
        files_to_upload = set(core_files)
        
        for service in services:
            if service in service_files:
                files_to_upload.update(service_files[service])
        
        # Upload files
        for file_path in files_to_upload:
            if os.path.exists(file_path):
                try:
                    if os.path.isdir(file_path):
                        # Upload directory
                        upload_folder(
                            folder_path=file_path,
                            path_in_repo=file_path,
                            repo_id=repo_id,
                            repo_type="space",
                            token=token
                        )
                    else:
                        # Upload file
                        upload_file(
                            path_or_fileobj=file_path,
                            path_in_repo=file_path,
                            repo_id=repo_id,
                            repo_type="space",
                            token=token
                        )
                    logger.info(f"  Uploaded: {file_path}")
                except Exception as e:
                    logger.warning(f"  Failed to upload {file_path}: {str(e)}")
    
    def create_dataset(self, account: str, dataset_name: str, dataset_config: dict) -> bool:
        """Create a new Dataset"""
        try:
            token = self.accounts[account]["token"]
            account_name = self.accounts[account]["name"]
            repo_id = f"{account_name}/{dataset_name}"
            
            logger.info(f"Creating Dataset: {repo_id}")
            
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
                logger.warning(f"Dataset may already exist: {str(e)}")
            
            # Create README
            readme_content = f"""# {dataset_name}

## Purpose
{dataset_config['purpose']}

## Tables
{', '.join(dataset_config['tables'])}

## Size Estimate
~{dataset_config['size_estimate_gb']} GB

## Priority
{dataset_config['priority']}

## Status
{dataset_config['status']}

---
*Part of PopCorn Mini App distributed database system*
"""
            
            with open("/tmp/README.md", 'w') as f:
                f.write(readme_content)
            
            upload_file(
                path_or_fileobj="/tmp/README.md",
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                token=token
            )
            
            logger.info(f"✅ Dataset created successfully: {repo_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to create Dataset {dataset_name}: {str(e)}")
            return False
    
    def deploy_all_spaces(self) -> dict:
        """Deploy all Spaces from strategy"""
        results = {}
        
        for account_config in self.strategy['distribution_strategy']['spaces']['distribution']:
            account = "primary" if account_config['account'] == "ToolKit-backend" else "secondary"
            
            for space_data in account_config['spaces']:
                space_name = space_data['name']
                
                # Skip if already running
                if space_data['status'] == 'running':
                    logger.info(f"⏭️  Skipping {space_name} (already running)")
                    results[space_name] = "skipped"
                    continue
                
                success = self.create_space(account, space_name, space_data)
                results[space_name] = "success" if success else "failed"
                
                # Wait between deployments
                time.sleep(5)
        
        return results
    
    def deploy_all_datasets(self) -> dict:
        """Deploy all Datasets from strategy"""
        results = {}
        
        for account_config in self.strategy['distribution_strategy']['datasets']['distribution']:
            account = "primary" if account_config['account'] == "ToolKit-backend" else "secondary"
            
            for dataset_data in account_config['datasets']:
                dataset_name = dataset_data['name']
                
                # Skip if already active
                if dataset_data['status'] == 'active':
                    logger.info(f"⏭️  Skipping {dataset_name} (already active)")
                    results[dataset_name] = "skipped"
                    continue
                
                success = self.create_dataset(account, dataset_name, dataset_data)
                results[dataset_name] = "success" if success else "failed"
                
                # Wait between deployments
                time.sleep(2)
        
        return results
    
    def generate_deployment_report(self, space_results: dict, dataset_results: dict) -> str:
        """Generate deployment report"""
        report = f"""
# Distributed System Deployment Report
Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Spaces Deployment

"""
        
        for space_name, status in space_results.items():
            emoji = "✅" if status == "success" else "⏭️" if status == "skipped" else "❌"
            report += f"{emoji} **{space_name}**: {status}\n"
        
        report += "\n## Datasets Deployment\n\n"
        
        for dataset_name, status in dataset_results.items():
            emoji = "✅" if status == "success" else "⏭️" if status == "skipped" else "❌"
            report += f"{emoji} **{dataset_name}**: {status}\n"
        
        # Summary
        space_success = sum(1 for s in space_results.values() if s == "success")
        space_total = len(space_results)
        dataset_success = sum(1 for s in dataset_results.values() if s == "success")
        dataset_total = len(dataset_results)
        
        report += f"""
## Summary

- **Spaces:** {space_success}/{space_total} deployed successfully
- **Datasets:** {dataset_success}/{dataset_total} created successfully
- **Total Resources:** {space_success + dataset_success}/{space_total + dataset_total}

## Next Steps

1. Wait for Spaces to build (5-10 minutes each)
2. Configure load balancer to use new Spaces
3. Sync database tables to respective Datasets
4. Test failover and load balancing
5. Monitor system health

---
*Deployment completed*
"""
        
        return report


def main():
    """Main deployment function"""
    print("="*80)
    print("DEPLOYING DISTRIBUTED SYSTEM TO HUGGINGFACE")
    print("="*80)
    
    deployer = DistributedSystemDeployer()
    
    # Deploy Spaces
    print("\n📦 Deploying Spaces...")
    space_results = deployer.deploy_all_spaces()
    
    # Deploy Datasets
    print("\n💾 Creating Datasets...")
    dataset_results = deployer.deploy_all_datasets()
    
    # Generate report
    report = deployer.generate_deployment_report(space_results, dataset_results)
    
    # Save report
    with open("DEPLOYMENT_REPORT.md", 'w') as f:
        f.write(report)
    
    print("\n" + "="*80)
    print(report)
    print("="*80)
    print("\n✅ Deployment report saved to: DEPLOYMENT_REPORT.md")


if __name__ == "__main__":
    main()

# Made with Bob
