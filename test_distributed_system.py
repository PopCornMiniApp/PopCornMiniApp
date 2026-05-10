#!/usr/bin/env python3
"""
Test Distributed System
Comprehensive testing for Multi-Space and Multi-Dataset managers
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.multi_space_manager import (
    MultiSpaceManager, SpaceConfig, SpacePriority, 
    SpaceStatus, LoadBalancerConfig
)
from app.multi_dataset_manager import (
    MultiDatasetManager, DatasetConfig, DatasetPriority,
    ShardingStrategy
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DistributedSystemTester:
    """Test distributed system components"""
    
    def __init__(self):
        self.space_manager = None
        self.dataset_manager = None
        self.test_results = {
            "space_manager": {},
            "dataset_manager": {},
            "integration": {}
        }
    
    def test_space_manager_initialization(self) -> bool:
        """Test Space Manager initialization"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Space Manager Initialization")
        logger.info("="*80)
        
        try:
            # Test with default config
            self.space_manager = MultiSpaceManager()
            logger.info("✅ Default initialization successful")
            
            # Test with custom config
            custom_config = LoadBalancerConfig(
                method="weighted",
                health_check_interval=60,
                failover_enabled=True,
                sticky_sessions=True
            )
            manager2 = MultiSpaceManager(custom_config)
            logger.info("✅ Custom config initialization successful")
            
            self.test_results["space_manager"]["initialization"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Initialization failed: {str(e)}")
            self.test_results["space_manager"]["initialization"] = f"failed: {str(e)}"
            return False
    
    def test_space_registration(self) -> bool:
        """Test Space registration"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Space Registration")
        logger.info("="*80)
        
        try:
            # Register test Spaces
            test_spaces = [
                SpaceConfig(
                    name="test-space-1",
                    account="ToolKit-backend",
                    token=os.getenv("HF_TOKEN", "test_token"),
                    url="https://test1.hf.space",
                    purpose="Test Space 1",
                    services=["API", "Frontend"],
                    priority=SpacePriority.HIGH
                ),
                SpaceConfig(
                    name="test-space-2",
                    account="rayig",
                    token=os.getenv("HF_TOKEN_RAYIG", "test_token"),
                    url="https://test2.hf.space",
                    purpose="Test Space 2",
                    services=["Backup"],
                    priority=SpacePriority.MEDIUM
                )
            ]
            
            for space in test_spaces:
                self.space_manager.register_space(space)
                logger.info(f"✅ Registered: {space.name}")
            
            # Verify registration
            assert len(self.space_manager.spaces) == 2
            logger.info(f"✅ Total spaces registered: {len(self.space_manager.spaces)}")
            
            self.test_results["space_manager"]["registration"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Registration failed: {str(e)}")
            self.test_results["space_manager"]["registration"] = f"failed: {str(e)}"
            return False
    
    def test_space_selection_algorithms(self) -> bool:
        """Test Space selection algorithms"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Space Selection Algorithms")
        logger.info("="*80)
        
        try:
            spaces = list(self.space_manager.spaces.values())
            
            # Test round-robin
            space1 = self.space_manager.select_space_round_robin(spaces)
            space2 = self.space_manager.select_space_round_robin(spaces)
            logger.info(f"✅ Round-robin: {space1.name} -> {space2.name}")
            
            # Test least connections
            space3 = self.space_manager.select_space_least_connections(spaces)
            logger.info(f"✅ Least connections: {space3.name}")
            
            # Test weighted
            space4 = self.space_manager.select_space_weighted(spaces)
            logger.info(f"✅ Weighted: {space4.name}")
            
            self.test_results["space_manager"]["selection"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Selection failed: {str(e)}")
            self.test_results["space_manager"]["selection"] = f"failed: {str(e)}"
            return False
    
    def test_space_statistics(self) -> bool:
        """Test Space statistics"""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Space Statistics")
        logger.info("="*80)
        
        try:
            stats = self.space_manager.get_statistics()
            
            logger.info(f"Total Spaces: {stats['total_spaces']}")
            logger.info(f"Healthy Spaces: {stats['healthy_spaces']}")
            
            for name, space_stats in stats['spaces'].items():
                logger.info(f"\n{name}:")
                logger.info(f"  Status: {space_stats['status']}")
                logger.info(f"  Priority: {space_stats['priority']}")
            
            self.space_manager.print_statistics()
            
            self.test_results["space_manager"]["statistics"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Statistics failed: {str(e)}")
            self.test_results["space_manager"]["statistics"] = f"failed: {str(e)}"
            return False
    
    def test_dataset_manager_initialization(self) -> bool:
        """Test Dataset Manager initialization"""
        logger.info("\n" + "="*80)
        logger.info("TEST 5: Dataset Manager Initialization")
        logger.info("="*80)
        
        try:
            self.dataset_manager = MultiDatasetManager()
            logger.info("✅ Dataset Manager initialized")
            
            self.test_results["dataset_manager"]["initialization"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Initialization failed: {str(e)}")
            self.test_results["dataset_manager"]["initialization"] = f"failed: {str(e)}"
            return False
    
    def test_dataset_registration(self) -> bool:
        """Test Dataset registration"""
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Dataset Registration")
        logger.info("="*80)
        
        try:
            # Register test Datasets
            test_datasets = [
                DatasetConfig(
                    name="test-dataset-1",
                    account="ToolKit-backend",
                    token=os.getenv("HF_TOKEN", "test_token"),
                    repo_id="ToolKit-backend/test-dataset-1",
                    purpose="Test Dataset 1",
                    tables=["movies", "series"],
                    priority=DatasetPriority.HIGH,
                    size_estimate_gb=5.0
                ),
                DatasetConfig(
                    name="test-dataset-2",
                    account="rayig",
                    token=os.getenv("HF_TOKEN_RAYIG", "test_token"),
                    repo_id="rayig/test-dataset-2",
                    purpose="Test Dataset 2",
                    tables=["users", "logs"],
                    priority=DatasetPriority.MEDIUM,
                    size_estimate_gb=2.0
                )
            ]
            
            for dataset in test_datasets:
                self.dataset_manager.register_dataset(dataset)
                logger.info(f"✅ Registered: {dataset.name}")
            
            # Verify registration
            assert len(self.dataset_manager.datasets) == 2
            logger.info(f"✅ Total datasets registered: {len(self.dataset_manager.datasets)}")
            
            # Test table mapping
            dataset = self.dataset_manager.get_dataset_for_table("movies")
            assert dataset is not None
            logger.info(f"✅ Table mapping works: movies -> {dataset.name}")
            
            self.test_results["dataset_manager"]["registration"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Registration failed: {str(e)}")
            self.test_results["dataset_manager"]["registration"] = f"failed: {str(e)}"
            return False
    
    def test_shard_creation(self) -> bool:
        """Test shard creation"""
        logger.info("\n" + "="*80)
        logger.info("TEST 7: Shard Creation")
        logger.info("="*80)
        
        try:
            # Create functional shard
            shard1 = self.dataset_manager.create_shard(
                shard_id="shard-movies",
                dataset_name="test-dataset-1",
                tables=["movies"]
            )
            logger.info(f"✅ Created functional shard: {shard1.shard_id}")
            
            # Create horizontal shard
            shard2 = self.dataset_manager.create_shard(
                shard_id="shard-users-1",
                dataset_name="test-dataset-2",
                tables=["users"],
                row_range=(1, 10000)
            )
            logger.info(f"✅ Created horizontal shard: {shard2.shard_id} (rows 1-10000)")
            
            assert len(self.dataset_manager.shards) == 2
            logger.info(f"✅ Total shards created: {len(self.dataset_manager.shards)}")
            
            self.test_results["dataset_manager"]["sharding"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Shard creation failed: {str(e)}")
            self.test_results["dataset_manager"]["sharding"] = f"failed: {str(e)}"
            return False
    
    def test_dataset_statistics(self) -> bool:
        """Test Dataset statistics"""
        logger.info("\n" + "="*80)
        logger.info("TEST 8: Dataset Statistics")
        logger.info("="*80)
        
        try:
            stats = self.dataset_manager.get_statistics()
            
            logger.info(f"Total Datasets: {stats['total_datasets']}")
            logger.info(f"Total Shards: {stats['total_shards']}")
            logger.info(f"Total Tables: {stats['total_tables']}")
            
            self.dataset_manager.print_statistics()
            
            self.test_results["dataset_manager"]["statistics"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Statistics failed: {str(e)}")
            self.test_results["dataset_manager"]["statistics"] = f"failed: {str(e)}"
            return False
    
    def test_integration(self) -> bool:
        """Test integration between Space and Dataset managers"""
        logger.info("\n" + "="*80)
        logger.info("TEST 9: Integration Testing")
        logger.info("="*80)
        
        try:
            # Test that both managers work together
            space_count = len(self.space_manager.spaces)
            dataset_count = len(self.dataset_manager.datasets)
            
            logger.info(f"✅ Space Manager has {space_count} spaces")
            logger.info(f"✅ Dataset Manager has {dataset_count} datasets")
            
            # Test resource allocation
            total_resources = space_count + dataset_count
            logger.info(f"✅ Total resources managed: {total_resources}")
            
            self.test_results["integration"]["basic"] = "passed"
            return True
        
        except Exception as e:
            logger.error(f"❌ Integration test failed: {str(e)}")
            self.test_results["integration"]["basic"] = f"failed: {str(e)}"
            return False
    
    def generate_test_report(self) -> str:
        """Generate test report"""
        report = f"""
# Distributed System Test Report
Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Space Manager Tests

"""
        
        for test_name, result in self.test_results["space_manager"].items():
            emoji = "✅" if result == "passed" else "❌"
            report += f"{emoji} **{test_name}**: {result}\n"
        
        report += "\n## Dataset Manager Tests\n\n"
        
        for test_name, result in self.test_results["dataset_manager"].items():
            emoji = "✅" if result == "passed" else "❌"
            report += f"{emoji} **{test_name}**: {result}\n"
        
        report += "\n## Integration Tests\n\n"
        
        for test_name, result in self.test_results["integration"].items():
            emoji = "✅" if result == "passed" else "❌"
            report += f"{emoji} **{test_name}**: {result}\n"
        
        # Calculate success rate
        all_results = []
        for category in self.test_results.values():
            all_results.extend(category.values())
        
        passed = sum(1 for r in all_results if r == "passed")
        total = len(all_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        report += f"""
## Summary

- **Total Tests:** {total}
- **Passed:** {passed}
- **Failed:** {total - passed}
- **Success Rate:** {success_rate:.1f}%

## Status

"""
        
        if success_rate == 100:
            report += "✅ **ALL TESTS PASSED** - System ready for deployment\n"
        elif success_rate >= 80:
            report += "⚠️ **MOSTLY PASSED** - Minor issues to fix before deployment\n"
        else:
            report += "❌ **TESTS FAILED** - Critical issues need to be resolved\n"
        
        report += """
## Next Steps

1. Review any failed tests
2. Fix identified issues
3. Run tests again
4. Proceed with deployment if all tests pass

---
*Testing completed*
"""
        
        return report
    
    def run_all_tests(self) -> bool:
        """Run all tests"""
        print("\n" + "="*80)
        print("DISTRIBUTED SYSTEM COMPREHENSIVE TESTING")
        print("="*80)
        
        tests = [
            ("Space Manager Initialization", self.test_space_manager_initialization),
            ("Space Registration", self.test_space_registration),
            ("Space Selection Algorithms", self.test_space_selection_algorithms),
            ("Space Statistics", self.test_space_statistics),
            ("Dataset Manager Initialization", self.test_dataset_manager_initialization),
            ("Dataset Registration", self.test_dataset_registration),
            ("Shard Creation", self.test_shard_creation),
            ("Dataset Statistics", self.test_dataset_statistics),
            ("Integration", self.test_integration)
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                if not result:
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ Test '{test_name}' crashed: {str(e)}")
                all_passed = False
            
            time.sleep(1)  # Brief pause between tests
        
        # Generate report
        report = self.generate_test_report()
        
        # Save report
        with open("TEST_REPORT.md", 'w') as f:
            f.write(report)
        
        print("\n" + "="*80)
        print(report)
        print("="*80)
        print("\n✅ Test report saved to: TEST_REPORT.md")
        
        return all_passed


def main():
    """Main test function"""
    tester = DistributedSystemTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

# Made with Bob
