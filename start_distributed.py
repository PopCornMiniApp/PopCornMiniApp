#!/usr/bin/env python3
"""
Startup script for PopCorn with distributed systems
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_managers():
    """Initialize all managers"""
    try:
        # Initialize Multi-Space Manager
        from app.multi_space_manager import initialize_from_env
        space_manager = initialize_from_env()
        logger.info(f"✅ Space Manager initialized with {len(space_manager.spaces)} spaces")
        
        # Initialize Multi-Dataset Manager
        from app.multi_dataset_manager import initialize_from_env as init_dataset
        dataset_manager = init_dataset()
        logger.info(f"✅ Dataset Manager initialized with {len(dataset_manager.datasets)} datasets")
        
        # Initialize Multi-Account Manager
        from app.multi_account_manager import get_manager
        account_manager = get_manager()
        logger.info(f"✅ Account Manager initialized with {len(account_manager.accounts)} accounts")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize managers: {str(e)}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("INITIALIZING POPCORN DISTRIBUTED SYSTEMS")
    print("="*60)
    
    if initialize_managers():
        print("\n✅ All systems initialized successfully")
        print("\nStarting main application...")
        
        # Start main app
        os.system("python -m uvicorn app.main:app --host 0.0.0.0 --port 7860")
    else:
        print("\n❌ Failed to initialize systems")
        sys.exit(1)
