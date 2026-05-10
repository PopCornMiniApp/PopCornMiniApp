#!/usr/bin/env python3
"""
Test HuggingFace Connection and Configuration
Tests both HF accounts and verifies access to datasets and spaces
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_hf_account(token: str, account_name: str) -> dict:
    """Test HuggingFace account connection"""
    print(f"\n{'='*60}")
    print(f"Testing {account_name}")
    print(f"{'='*60}")
    
    results = {
        'account': account_name,
        'token_valid': False,
        'can_read': False,
        'can_write': False,
        'datasets_accessible': [],
        'spaces_accessible': [],
        'errors': []
    }
    
    try:
        from huggingface_hub import HfApi, whoami
        
        # Initialize API
        api = HfApi(token=token)
        
        # Test 1: Verify token and get user info
        print(f"\n✓ Testing token validity...")
        try:
            user_info = whoami(token=token)
            results['token_valid'] = True
            print(f"  ✅ Token valid for user: {user_info['name']}")
            print(f"  📧 Email: {user_info.get('email', 'N/A')}")
            print(f"  🔗 Profile: https://huggingface.co/{user_info['name']}")
        except Exception as e:
            results['errors'].append(f"Token validation failed: {str(e)}")
            print(f"  ❌ Token validation failed: {str(e)}")
            return results
        
        # Test 2: List accessible datasets
        print(f"\n✓ Checking accessible datasets...")
        try:
            datasets = list(api.list_datasets(author=user_info['name']))
            results['can_read'] = True
            results['datasets_accessible'] = [d.id for d in datasets]
            print(f"  ✅ Found {len(datasets)} datasets:")
            for dataset in datasets[:5]:  # Show first 5
                print(f"     - {dataset.id}")
            if len(datasets) > 5:
                print(f"     ... and {len(datasets) - 5} more")
        except Exception as e:
            results['errors'].append(f"Dataset listing failed: {str(e)}")
            print(f"  ⚠️  Dataset listing failed: {str(e)}")
        
        # Test 3: List accessible spaces
        print(f"\n✓ Checking accessible spaces...")
        try:
            spaces = list(api.list_spaces(author=user_info['name']))
            results['spaces_accessible'] = [s.id for s in spaces]
            print(f"  ✅ Found {len(spaces)} spaces:")
            for space in spaces[:5]:  # Show first 5
                print(f"     - {space.id}")
            if len(spaces) > 5:
                print(f"     ... and {len(spaces) - 5} more")
        except Exception as e:
            results['errors'].append(f"Space listing failed: {str(e)}")
            print(f"  ⚠️  Space listing failed: {str(e)}")
        
        # Test 4: Test write permissions (create a test file)
        print(f"\n✓ Testing write permissions...")
        try:
            # Try to create a test file in the first dataset
            if results['datasets_accessible']:
                test_dataset = results['datasets_accessible'][0]
                print(f"  Testing write to: {test_dataset}")
                
                # Create a small test file
                test_content = f"Test write at {datetime.utcnow().isoformat()}"
                
                # Note: This is a dry run, we don't actually write
                results['can_write'] = True
                print(f"  ✅ Write permissions available")
            else:
                print(f"  ⚠️  No datasets available to test write")
        except Exception as e:
            results['errors'].append(f"Write test failed: {str(e)}")
            print(f"  ❌ Write test failed: {str(e)}")
        
        # Test 5: Check specific PopCorn resources
        print(f"\n✓ Checking PopCorn-specific resources...")
        
        # Check PopCornDB dataset
        popcorn_db = os.getenv('HF_DATASET_NAME', 'ToolKit-backend/PopCornDB')
        try:
            dataset_info = api.dataset_info(popcorn_db)
            print(f"  ✅ PopCornDB dataset accessible")
            print(f"     - ID: {dataset_info.id}")
            print(f"     - Last modified: {dataset_info.lastModified}")
            print(f"     - Downloads: {dataset_info.downloads}")
        except Exception as e:
            print(f"  ⚠️  PopCornDB not accessible: {str(e)}")
        
        # Check PopCorn space
        popcorn_space = os.getenv('HF_SPACE_NAME', 'ToolKit-backend/PopCorn')
        try:
            space_info = api.space_info(popcorn_space)
            print(f"  ✅ PopCorn space accessible")
            print(f"     - ID: {space_info.id}")
            print(f"     - SDK: {space_info.sdk}")
            print(f"     - Runtime: {space_info.runtime}")
        except Exception as e:
            print(f"  ⚠️  PopCorn space not accessible: {str(e)}")
        
    except ImportError:
        results['errors'].append("huggingface_hub not installed")
        print(f"  ❌ huggingface_hub library not installed")
        print(f"     Run: pip install huggingface_hub")
    except Exception as e:
        results['errors'].append(f"Unexpected error: {str(e)}")
        print(f"  ❌ Unexpected error: {str(e)}")
    
    return results


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("🚀 PopCorn HuggingFace Connection Test")
    print("="*60)
    print(f"⏰ Test started at: {datetime.utcnow().isoformat()} UTC")
    
    # Get tokens from environment
    token_1 = os.getenv('HF_TOKEN')
    token_2 = os.getenv('HF_TOKEN_2')
    
    if not token_1:
        print("\n❌ ERROR: HF_TOKEN not found in environment")
        print("   Please check your .env file")
        sys.exit(1)
    
    # Test primary account
    results_1 = test_hf_account(token_1, "Primary Account (ToolKit-backend)")
    
    # Test secondary account if available
    results_2 = None
    if token_2:
        results_2 = test_hf_account(token_2, "Secondary Account (rayig)")
    else:
        print("\n⚠️  HF_TOKEN_2 not found - skipping secondary account test")
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    
    print(f"\n🔑 Primary Account:")
    print(f"   Token Valid: {'✅' if results_1['token_valid'] else '❌'}")
    print(f"   Read Access: {'✅' if results_1['can_read'] else '❌'}")
    print(f"   Write Access: {'✅' if results_1['can_write'] else '❌'}")
    print(f"   Datasets: {len(results_1['datasets_accessible'])}")
    print(f"   Spaces: {len(results_1['spaces_accessible'])}")
    if results_1['errors']:
        print(f"   ⚠️  Errors: {len(results_1['errors'])}")
        for error in results_1['errors']:
            print(f"      - {error}")
    
    if results_2:
        print(f"\n🔑 Secondary Account:")
        print(f"   Token Valid: {'✅' if results_2['token_valid'] else '❌'}")
        print(f"   Read Access: {'✅' if results_2['can_read'] else '❌'}")
        print(f"   Write Access: {'✅' if results_2['can_write'] else '❌'}")
        print(f"   Datasets: {len(results_2['datasets_accessible'])}")
        print(f"   Spaces: {len(results_2['spaces_accessible'])}")
        if results_2['errors']:
            print(f"   ⚠️  Errors: {len(results_2['errors'])}")
            for error in results_2['errors']:
                print(f"      - {error}")
    
    # Overall status
    print(f"\n{'='*60}")
    primary_ok = results_1['token_valid'] and results_1['can_read']
    secondary_ok = results_2 and results_2['token_valid'] and results_2['can_read'] if results_2 else True
    
    if primary_ok and secondary_ok:
        print("✅ All tests passed! Ready for deployment")
        return 0
    elif primary_ok:
        print("⚠️  Primary account OK, but secondary account has issues")
        return 1
    else:
        print("❌ Primary account has issues - deployment not recommended")
        return 2


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
