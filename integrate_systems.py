#!/usr/bin/env python3
"""
Integrate Multi-Space and Multi-Dataset managers with main application
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def integrate_multi_space_manager():
    """Add Multi-Space Manager to main.py"""
    main_file = Path("app/main.py")
    content = main_file.read_text()
    
    # Check if already integrated
    if "multi_space_manager" in content:
        print("✅ Multi-Space Manager already integrated")
        return True
    
    # Add import at top
    import_line = "from app.multi_space_manager import get_manager as get_space_manager\n"
    
    # Find imports section
    lines = content.split('\n')
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('from app.'):
            insert_pos = i + 1
    
    lines.insert(insert_pos, import_line)
    
    # Write back
    main_file.write_text('\n'.join(lines))
    print("✅ Multi-Space Manager integrated into main.py")
    return True

def integrate_multi_dataset_manager():
    """Add Multi-Dataset Manager to database.py"""
    db_file = Path("app/database.py")
    content = db_file.read_text()
    
    # Check if already integrated
    if "multi_dataset_manager" in content:
        print("✅ Multi-Dataset Manager already integrated")
        return True
    
    # Add import at top
    import_line = "from app.multi_dataset_manager import get_manager as get_dataset_manager\n"
    
    lines = content.split('\n')
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_pos = i + 1
    
    lines.insert(insert_pos, import_line)
    
    db_file.write_text('\n'.join(lines))
    print("✅ Multi-Dataset Manager integrated into database.py")
    return True

def update_config():
    """Update config.py with new settings"""
    config_file = Path("app/config.py")
    content = config_file.read_text()
    
    if "ENABLE_MULTI_SPACE" in content:
        print("✅ Config already updated")
        return True
    
    # Add new config options
    new_config = """
# Multi-Space & Multi-Dataset Configuration
ENABLE_MULTI_SPACE = os.getenv("ENABLE_MULTI_SPACE", "true").lower() == "true"
ENABLE_MULTI_DATASET = os.getenv("ENABLE_MULTI_DATASET", "true").lower() == "true"
LOAD_BALANCING_METHOD = os.getenv("LOAD_BALANCING_METHOD", "weighted")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
"""
    
    config_file.write_text(content + new_config)
    print("✅ Config updated with new settings")
    return True

def create_startup_script():
    """Create startup script that initializes all managers"""
    script = """#!/usr/bin/env python3
\"\"\"
Startup script for PopCorn with distributed systems
\"\"\"

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_managers():
    \"\"\"Initialize all managers\"\"\"
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
        print("\\n✅ All systems initialized successfully")
        print("\\nStarting main application...")
        
        # Start main app
        os.system("python -m uvicorn app.main:app --host 0.0.0.0 --port 7860")
    else:
        print("\\n❌ Failed to initialize systems")
        sys.exit(1)
"""
    
    Path("start_distributed.py").write_text(script)
    os.chmod("start_distributed.py", 0o755)
    print("✅ Created start_distributed.py")
    return True

def main():
    """Main integration function"""
    print("\n" + "="*60)
    print("INTEGRATING DISTRIBUTED SYSTEMS")
    print("="*60 + "\n")
    
    # Already in PopCorn directory when script runs from there
    
    steps = [
        ("Integrating Multi-Space Manager", integrate_multi_space_manager),
        ("Integrating Multi-Dataset Manager", integrate_multi_dataset_manager),
        ("Updating Config", update_config),
        ("Creating Startup Script", create_startup_script),
    ]
    
    results = []
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        try:
            success = step_func()
            results.append((step_name, success))
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            results.append((step_name, False))
    
    print("\n" + "="*60)
    print("INTEGRATION SUMMARY")
    print("="*60)
    
    for step_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {step_name}")
    
    success_count = sum(1 for _, s in results if s)
    print(f"\n{success_count}/{len(results)} steps completed successfully")
    
    if success_count == len(results):
        print("\n✅ Integration complete! Use: python3 start_distributed.py")
    else:
        print("\n⚠️ Some steps failed. Please review errors above.")

if __name__ == "__main__":
    main()

# Made with Bob
