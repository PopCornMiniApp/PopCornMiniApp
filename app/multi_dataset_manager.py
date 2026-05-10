"""
Multi-Dataset Manager for HuggingFace
Manages multiple datasets for database sharding and distributed storage
"""

import os
import sqlite3
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from threading import Lock
from huggingface_hub import HfApi, hf_hub_download

logger = logging.getLogger(__name__)


class DatasetPriority(Enum):
    """Dataset priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ShardingStrategy(Enum):
    """Database sharding strategies"""
    FUNCTIONAL = "functional"  # By table/function
    HORIZONTAL = "horizontal"  # By row ranges
    VERTICAL = "vertical"  # By columns
    HYBRID = "hybrid"  # Combination


@dataclass
class DatasetConfig:
    """Configuration for a HuggingFace Dataset"""
    name: str
    account: str
    token: str
    repo_id: str
    purpose: str
    tables: List[str]
    priority: DatasetPriority
    size_estimate_gb: float
    sharding_strategy: ShardingStrategy = ShardingStrategy.FUNCTIONAL

    # Runtime state
    last_sync: Optional[datetime] = None
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    current_size_mb: float = 0.0
    last_error: Optional[str] = None


@dataclass
class ShardConfig:
    """Configuration for a database shard"""
    shard_id: str
    dataset: str
    tables: List[str]
    row_range: Optional[Tuple[int, int]] = None  # For horizontal sharding
    columns: Optional[List[str]] = None  # For vertical sharding


class MultiDatasetManager:
    """
    Manages multiple HuggingFace Datasets for database sharding
    """

    def __init__(self):
        self.datasets: Dict[str, DatasetConfig] = {}
        self.shards: Dict[str, ShardConfig] = {}
        self.table_to_dataset: Dict[str, str] = {}  # Map table name to dataset
        self.lock = Lock()
        self.hf_api = HfApi()

        logger.info("MultiDatasetManager initialized")

    def register_dataset(self, dataset: DatasetConfig) -> None:
        """Register a new Dataset"""
        with self.lock:
            self.datasets[dataset.name] = dataset

            # Map tables to dataset
            for table in dataset.tables:
                self.table_to_dataset[table] = dataset.name

            logger.info(
                f"Registered Dataset: {dataset.name} ({dataset.account})")

    def register_datasets_from_config(
            self, config_file: str = "hf_optimization_strategy.json") -> None:
        """Register Datasets from configuration file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            for account_config in config['distribution_strategy']['datasets']['distribution']:
                account = account_config['account']
                token = os.getenv(
                    f"HF_TOKEN_{account.upper().replace('-', '_')}", "")

                for dataset_data in account_config['datasets']:
                    dataset = DatasetConfig(
                        name=dataset_data['name'],
                        account=account,
                        token=token,
                        repo_id=f"{account}/{dataset_data['name']}",
                        purpose=dataset_data['purpose'],
                        tables=dataset_data['tables'],
                        priority=DatasetPriority[dataset_data['priority'].upper()],
                        size_estimate_gb=dataset_data['size_estimate_gb']
                    )
                    self.register_dataset(dataset)

            logger.info(
                f"Registered {len(self.datasets)} Datasets from config")

        except Exception as e:
            logger.error(f"Failed to register Datasets from config: {str(e)}")

    def get_dataset_for_table(
            self,
            table_name: str) -> Optional[DatasetConfig]:
        """Get the dataset that contains a specific table"""
        dataset_name = self.table_to_dataset.get(table_name)
        if dataset_name:
            return self.datasets.get(dataset_name)
        return None

    def create_shard(self, shard_id: str, dataset_name: str, tables: List[str],
                     row_range: Optional[Tuple[int, int]] = None,
                     columns: Optional[List[str]] = None) -> ShardConfig:
        """Create a new database shard"""
        shard = ShardConfig(
            shard_id=shard_id,
            dataset=dataset_name,
            tables=tables,
            row_range=row_range,
            columns=columns
        )

        with self.lock:
            self.shards[shard_id] = shard

        logger.info(f"Created shard: {shard_id} in dataset {dataset_name}")
        return shard

    def export_table_to_dataset(self, source_db: str, table_name: str,
                                dataset_name: str) -> bool:
        """
        Export a table from source database to a specific dataset

        Args:
            source_db: Path to source SQLite database
            table_name: Name of table to export
            dataset_name: Target dataset name

        Returns:
            True if successful, False otherwise
        """
        dataset = self.datasets.get(dataset_name)
        if not dataset:
            logger.error(f"Dataset {dataset_name} not found")
            return False

        try:
            dataset.total_operations += 1

            # Connect to source database
            conn = sqlite3.connect(source_db)
            cursor = conn.cursor()

            # Export table to temporary file
            temp_db = f"/tmp/{dataset_name}_{table_name}.db"
            export_conn = sqlite3.connect(temp_db)

            # Copy table schema
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            create_sql = cursor.fetchone()
            if create_sql:
                export_conn.execute(create_sql[0])

            # Copy table data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()

            if rows:
                placeholders = ','.join(['?' for _ in rows[0]])
                export_conn.executemany(
                    f"INSERT INTO {table_name} VALUES ({placeholders})",
                    rows
                )

            export_conn.commit()
            export_conn.close()
            conn.close()

            # Upload to HuggingFace
            self.hf_api.upload_file(
                path_or_fileobj=temp_db,
                path_in_repo=f"{table_name}.db",
                repo_id=dataset.repo_id,
                repo_type="dataset",
                token=dataset.token
            )

            # Clean up
            os.remove(temp_db)

            dataset.successful_operations += 1
            dataset.last_sync = datetime.utcnow()

            logger.info(
                f"Exported table {table_name} to dataset {dataset_name}")
            return True

        except Exception as e:
            dataset.failed_operations += 1
            dataset.last_error = str(e)
            logger.error(f"Failed to export table {table_name}: {str(e)}")
            return False

    def import_table_from_dataset(self, dataset_name: str, table_name: str,
                                  target_db: str) -> bool:
        """
        Import a table from dataset to target database

        Args:
            dataset_name: Source dataset name
            table_name: Name of table to import
            target_db: Path to target SQLite database

        Returns:
            True if successful, False otherwise
        """
        dataset = self.datasets.get(dataset_name)
        if not dataset:
            logger.error(f"Dataset {dataset_name} not found")
            return False

        try:
            dataset.total_operations += 1

            # Download from HuggingFace
            temp_db = hf_hub_download(
                repo_id=dataset.repo_id,
                filename=f"{table_name}.db",
                repo_type="dataset",
                token=dataset.token
            )

            # Connect to databases
            source_conn = sqlite3.connect(temp_db)
            target_conn = sqlite3.connect(target_db)

            # Copy table schema
            cursor = source_conn.cursor()
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            create_sql = cursor.fetchone()

            if create_sql:
                # Drop existing table if exists
                target_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                target_conn.execute(create_sql[0])

                # Copy data
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                if rows:
                    placeholders = ','.join(['?' for _ in rows[0]])
                    target_conn.executemany(
                        f"INSERT INTO {table_name} VALUES ({placeholders})",
                        rows
                    )

            target_conn.commit()
            source_conn.close()
            target_conn.close()

            dataset.successful_operations += 1
            dataset.last_sync = datetime.utcnow()

            logger.info(
                f"Imported table {table_name} from dataset {dataset_name}")
            return True

        except Exception as e:
            dataset.failed_operations += 1
            dataset.last_error = str(e)
            logger.error(f"Failed to import table {table_name}: {str(e)}")
            return False

    def sync_all_tables(self, source_db: str) -> Dict[str, bool]:
        """
        Sync all tables to their respective datasets

        Args:
            source_db: Path to source SQLite database

        Returns:
            Dictionary mapping table names to sync status
        """
        results = {}

        for table_name, dataset_name in self.table_to_dataset.items():
            success = self.export_table_to_dataset(
                source_db, table_name, dataset_name)
            results[table_name] = success

        successful = sum(1 for v in results.values() if v)
        logger.info(f"Synced {successful}/{len(results)} tables successfully")

        return results

    def create_backup(self, source_db: str, backup_dataset: str) -> bool:
        """
        Create full database backup to a specific dataset

        Args:
            source_db: Path to source SQLite database
            backup_dataset: Name of backup dataset

        Returns:
            True if successful, False otherwise
        """
        dataset = self.datasets.get(backup_dataset)
        if not dataset:
            logger.error(f"Backup dataset {backup_dataset} not found")
            return False

        try:
            dataset.total_operations += 1

            # Create backup filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"

            # Upload entire database
            self.hf_api.upload_file(
                path_or_fileobj=source_db,
                path_in_repo=backup_filename,
                repo_id=dataset.repo_id,
                repo_type="dataset",
                token=dataset.token
            )

            dataset.successful_operations += 1
            dataset.last_sync = datetime.utcnow()

            logger.info(
                f"Created backup: {backup_filename} in {backup_dataset}")
            return True

        except Exception as e:
            dataset.failed_operations += 1
            dataset.last_error = str(e)
            logger.error(f"Failed to create backup: {str(e)}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all Datasets"""
        stats = {
            "total_datasets": len(self.datasets),
            "total_shards": len(self.shards),
            "total_tables": len(self.table_to_dataset),
            "datasets": {}
        }

        for name, dataset in self.datasets.items():
            success_rate = (
                dataset.successful_operations /
                dataset.total_operations *
                100) if dataset.total_operations > 0 else 0

            stats["datasets"][name] = {
                "account": dataset.account,
                "purpose": dataset.purpose,
                "priority": dataset.priority.name,
                "tables": dataset.tables,
                "size_estimate_gb": dataset.size_estimate_gb,
                "total_operations": dataset.total_operations,
                "successful_operations": dataset.successful_operations,
                "failed_operations": dataset.failed_operations,
                "success_rate": f"{success_rate:.2f}%",
                "last_sync": dataset.last_sync.isoformat() if dataset.last_sync else None,
                "last_error": dataset.last_error}

        return stats

    def print_statistics(self) -> None:
        """Print formatted statistics"""
        stats = self.get_statistics()

        print("\n" + "=" * 80)
        print("MULTI-DATASET MANAGER STATISTICS")
        print("=" * 80)
        print(f"Total Datasets: {stats['total_datasets']}")
        print(f"Total Shards: {stats['total_shards']}")
        print(f"Total Tables: {stats['total_tables']}")
        print("\nDataset Details:")
        print("-" * 80)

        for name, dataset_stats in stats["datasets"].items():
            print(f"\n{name} ({dataset_stats['account']})")
            print(f"  Purpose: {dataset_stats['purpose']}")
            print(f"  Priority: {dataset_stats['priority']}")
            print(f"  Tables: {', '.join(dataset_stats['tables'])}")
            print(f"  Size Estimate: {dataset_stats['size_estimate_gb']} GB")
            print(f"  Operations: {dataset_stats['total_operations']} total, "
                  f"{dataset_stats['successful_operations']} success, "
                  f"{dataset_stats['failed_operations']} failed")
            print(f"  Success Rate: {dataset_stats['success_rate']}")
            if dataset_stats['last_sync']:
                print(f"  Last Sync: {dataset_stats['last_sync']}")
            if dataset_stats['last_error']:
                print(f"  Last Error: {dataset_stats['last_error']}")

        print("=" * 80 + "\n")


# Global instance
_manager_instance: Optional[MultiDatasetManager] = None


def get_manager() -> MultiDatasetManager:
    """Get or create global MultiDatasetManager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiDatasetManager()
    return _manager_instance


def initialize_from_env() -> MultiDatasetManager:
    """Initialize manager from environment variables"""
    manager = get_manager()

    # Register main dataset (currently active)
    main_dataset = DatasetConfig(
        name="PopCornDB-Main",
        account="ToolKit-backend",
        token=os.getenv("HF_TOKEN", ""),
        repo_id="ToolKit-backend/PopCornDB",
        purpose="Core Database",
        tables=["movies", "series", "episodes", "users"],
        priority=DatasetPriority.CRITICAL,
        size_estimate_gb=5.0
    )
    manager.register_dataset(main_dataset)

    logger.info("MultiDatasetManager initialized from environment")
    return manager


if __name__ == "__main__":
    # Test the manager
    logging.basicConfig(level=logging.INFO)

    manager = initialize_from_env()
    manager.print_statistics()

# Made with Bob
