#!/usr/bin/env python3
"""
Automated script to fix all flake8 errors in the PopCorn app
"""

import os
import re
import subprocess
from pathlib import Path


def run_autopep8():
    """Run autopep8 to fix most formatting issues"""
    print("Running autopep8 to fix formatting issues...")
    cmd = [
        "python3", "-m", "autopep8",
        "--in-place",
        "--recursive",
        "--aggressive",
        "--aggressive",
        "--max-line-length", "79",
        "app/"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"autopep8 completed: {result.returncode}")
    return result.returncode == 0


def run_autoflake():
    """Run autoflake to remove unused imports and variables"""
    print("Running autoflake to remove unused imports...")
    cmd = [
        "python3", "-m", "autoflake",
        "--in-place",
        "--recursive",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
        "--remove-duplicate-keys",
        "app/"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"autoflake completed: {result.returncode}")
    return result.returncode == 0


def fix_f_strings(file_path):
    """Fix f-strings without placeholders"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace f"string" with "string" if no placeholders
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Find f-strings without {} placeholders
        if 'f"' in line or "f'" in line:
            # Check if line has f-string without placeholders
            if (('f"' in line and '{' not in line.split('f"')[1].split('"')[0]) or
                ("f'" in line and '{' not in line.split("f'")[1].split("'")[0])):
                # Remove the f prefix
                line = line.replace('f"', '"').replace("f'", "'")
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def fix_bare_except(file_path):
    """Fix bare except clauses"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # Replace bare except with except Exception
    content = re.sub(r'\bexcept\s*:', 'except Exception:', content)
    
    if content != original:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def process_all_files():
    """Process all Python files in app directory"""
    app_dir = Path("app")
    python_files = list(app_dir.glob("*.py"))
    
    print(f"\nProcessing {len(python_files)} Python files...")
    
    f_string_fixes = 0
    bare_except_fixes = 0
    
    for py_file in python_files:
        if fix_f_strings(py_file):
            f_string_fixes += 1
        if fix_bare_except(py_file):
            bare_except_fixes += 1
    
    print(f"Fixed f-strings in {f_string_fixes} files")
    print(f"Fixed bare except in {bare_except_fixes} files")


def main():
    """Main execution"""
    print("=" * 60)
    print("AUTOMATED FLAKE8 ERROR FIXER")
    print("=" * 60)
    
    # Change to PopCorn directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Step 1: Install required tools
    print("\n1. Installing required tools...")
    subprocess.run(["pip3", "install", "-q", "autopep8", "autoflake"], 
                   capture_output=True)
    
    # Step 2: Run autoflake to remove unused imports
    print("\n2. Removing unused imports and variables...")
    run_autoflake()
    
    # Step 3: Fix f-strings and bare except
    print("\n3. Fixing f-strings and bare except clauses...")
    process_all_files()
    
    # Step 4: Run autopep8 to fix formatting
    print("\n4. Fixing formatting issues...")
    run_autopep8()
    
    # Step 5: Run flake8 to check remaining errors
    print("\n5. Checking remaining errors...")
    result = subprocess.run(
        ["python3", "-m", "flake8", "app/", "--count", "--statistics"],
        capture_output=True,
        text=True
    )
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # Count remaining errors
    lines = result.stdout.split('\n')
    total_errors = 0
    for line in lines:
        if line.strip().isdigit():
            total_errors = int(line.strip())
            break
    
    print(f"\nTotal remaining errors: {total_errors}")
    
    if total_errors == 0:
        print("\n✅ ALL ERRORS FIXED!")
    else:
        print(f"\n⚠️  {total_errors} errors remaining - manual fixes needed")
    
    return total_errors


if __name__ == "__main__":
    exit(main())

# Made with Bob
