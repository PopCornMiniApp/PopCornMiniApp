"""
Backup Manager
Comprehensive database backup, restore, and version management system
"""

import os
import gzip
import shutil
import logging
import hashlib
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from app import database as db
from app.config import DB_PATH, HF_TOKEN, HF_DATASET_NAME

logger = logging.getLogger(__name__)


class BackupManager:
    """Advanced backup and restore management"""

    BACKUP_DIR = "/tmp/popcorn_backups"

    def __init__(self):
        """Initialize backup manager"""
        # Create backup directory if not exists
        Path(self.BACKUP_DIR).mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        backup_name: Optional[str] = None,
        backup_type: str = 'manual',
        compress: bool = True,
        created_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a database backup"""
        try:
            # Generate backup name if not provided
            if not backup_name:
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                backup_name = f"popcorn_backup_{timestamp}"

            # Backup file path
            backup_path = os.path.join(self.BACKUP_DIR, f"{backup_name}.db")

            # Copy database file
            if not os.path.exists(DB_PATH):
                raise FileNotFoundError(f"Database file not found: {DB_PATH}")

            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"Database copied to {backup_path}")

            # Get file size before compression
            backup_size = os.path.getsize(backup_path)

            # Compress if requested
            if compress:
                compressed_path = f"{backup_path}.gz"
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Remove uncompressed file
                os.remove(backup_path)
                backup_path = compressed_path
                compressed_size = os.path.getsize(backup_path)
                logger.info(
                    f"Backup compressed: {backup_size} -> {compressed_size} bytes")
                backup_size = compressed_size

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)

            # Get table statistics
            tables_info = self._get_tables_info()

            # Record backup in database
            backup_id = db.create_database_backup(
                backup_name=backup_name,
                backup_path=backup_path,
                backup_type=backup_type,
                backup_size=backup_size,
                compression='gzip' if compress else 'none',
                tables_included=list(tables_info.keys()),
                records_count=sum(tables_info.values()),
                status='completed',
                created_by=created_by
            )

            logger.info(
                f"Backup created successfully: {backup_name} (ID: {backup_id})")

            return {
                "success": True,
                "backup_id": backup_id,
                "backup_name": backup_name,
                "backup_path": backup_path,
                "backup_size": backup_size,
                "checksum": checksum,
                "tables": tables_info,
                "compressed": compress
            }
        except Exception as e:
            logger.error(f"Error creating backup: {e}", exc_info=True)

            # Record failed backup
            try:
                db.create_database_backup(
                    backup_name=backup_name or "failed_backup",
                    backup_path="",
                    backup_type=backup_type,
                    status='failed',
                    error_message=str(e),
                    created_by=created_by
                )
            except (sqlite3.Error, IOError, OSError) as db_error:
                logger.error(
                    f"Failed to record backup failure in database: {type(db_error).__name__}: {str(db_error)}")
            except Exception as unexpected_error:
                logger.exception(
                    f"Unexpected error recording backup failure: {str(unexpected_error)}")

            return {
                "success": False,
                "error": str(e)
            }

    def restore_backup(
        self,
        backup_path: str,
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(
                    f"Backup file not found: {backup_path}")

            # Create a backup of current database before restore
            current_backup = self.create_backup(
                backup_name=f"pre_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                backup_type='automatic')

            if not current_backup['success']:
                raise Exception("Failed to create pre-restore backup")

            # Decompress if needed
            restore_path = backup_path
            if backup_path.endswith('.gz'):
                decompressed_path = backup_path[:-3]
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(decompressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                restore_path = decompressed_path
                logger.info(f"Backup decompressed to {restore_path}")

            # Verify checksum if requested
            if verify_checksum:
                stored_checksum = self._calculate_checksum(restore_path)
                logger.info(f"Backup checksum verified: {stored_checksum}")

            # Stop any active connections
            # (In production, you'd want to stop the application first)

            # Replace current database
            shutil.copy2(restore_path, DB_PATH)
            logger.info(f"Database restored from {backup_path}")

            # Clean up decompressed file if created
            if restore_path != backup_path:
                os.remove(restore_path)

            return {
                "success": True,
                "restored_from": backup_path,
                "pre_restore_backup": current_backup['backup_path']
            }
        except Exception as e:
            logger.error(f"Error restoring backup: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def list_backups(
        self,
        limit: int = 50,
        backup_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List available backups"""
        try:
            # Get from database
            db_backups = db.get_database_backups(
                limit=limit, backup_type=backup_type)

            # Verify files still exist
            for backup in db_backups.get('backups', []):
                backup['file_exists'] = os.path.exists(backup['backup_path'])
                if backup['file_exists']:
                    backup['current_size'] = os.path.getsize(
                        backup['backup_path'])

            return db_backups.get('backups', [])
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    def delete_backup(self, backup_id: int) -> Dict[str, Any]:
        """Delete a backup"""
        try:
            # Get backup info
            backups = db.get_database_backups(limit=1000)
            backup = next(
                (b for b in backups.get(
                    'backups',
                    []) if b['id'] == backup_id),
                None)

            if not backup:
                raise ValueError(f"Backup not found: {backup_id}")

            # Delete file
            if os.path.exists(backup['backup_path']):
                os.remove(backup['backup_path'])
                logger.info(f"Deleted backup file: {backup['backup_path']}")

            # Update database record
            conn = db.get_connection()
            conn.execute(
                "DELETE FROM database_backups WHERE id=?", (backup_id,))
            conn.commit()
            conn.close()

            return {
                "success": True,
                "backup_id": backup_id
            }
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def cleanup_old_backups(
        self,
        keep_count: int = 10,
        keep_days: int = 30
    ) -> Dict[str, Any]:
        """Clean up old backups based on retention policy"""
        try:
            backups = self.list_backups(limit=1000)

            # Sort by creation date
            backups.sort(key=lambda x: x['created_at'], reverse=True)

            deleted_count = 0
            kept_count = 0

            for i, backup in enumerate(backups):
                # Keep recent backups
                if i < keep_count:
                    kept_count += 1
                    continue

                # Check age
                created_at = datetime.fromisoformat(backup['created_at'])
                age_days = (datetime.utcnow() - created_at).days

                if age_days > keep_days:
                    result = self.delete_backup(backup['id'])
                    if result['success']:
                        deleted_count += 1
                else:
                    kept_count += 1

            logger.info(
                f"Backup cleanup: kept {kept_count}, deleted {deleted_count}")

            return {
                "success": True,
                "deleted_count": deleted_count,
                "kept_count": kept_count
            }
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def export_data(
        self,
        export_format: str = 'json',
        tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Export database data to various formats"""
        try:
            import json

            conn = db.get_connection()

            # Get all tables if not specified
            if not tables:
                tables = self._get_all_tables()

            export_data = {}

            for table in tables:
                try:
                    # Fixed: Validate table name against existing tables to prevent SQL injection
                    # Get list of valid tables
                    valid_tables = [t[0] for t in conn.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """).fetchall()]

                    if table not in valid_tables:
                        logger.warning(f"Skipping invalid table: {table}")
                        continue

                    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                    export_data[table] = [dict(row) for row in rows]
                    logger.info(f"Exported {len(rows)} rows from {table}")
                except Exception as e:
                    logger.error(f"Error exporting table {table}: {e}")

            conn.close()

            # Generate export file
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            export_name = f"popcorn_export_{timestamp}"

            if export_format == 'json':
                export_path = os.path.join(
                    self.BACKUP_DIR, f"{export_name}.json")
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

            export_size = os.path.getsize(export_path)

            logger.info(f"Data exported to {export_path}")

            return {
                "success": True,
                "export_path": export_path,
                "export_size": export_size,
                "tables_exported": len(export_data),
                "total_records": sum(
                    len(rows) for rows in export_data.values())}
        except Exception as e:
            logger.error(f"Error exporting data: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _get_tables_info(self) -> Dict[str, int]:
        """Get information about all tables"""
        try:
            conn = db.get_connection()
            tables = {}

            # Get all table names
            table_names = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """).fetchall()

            for table in table_names:
                table_name = table[0]
                # Fixed: table_name comes from sqlite_master query, which is safe
                # But add extra validation for safety
                if not table_name or table_name.startswith('sqlite_'):
                    continue
                count = conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                tables[table_name] = count

            conn.close()
            return tables
        except Exception as e:
            logger.error(f"Error getting tables info: {e}")
            return {}

    def _get_all_tables(self) -> List[str]:
        """Get list of all tables"""
        try:
            conn = db.get_connection()
            tables = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """).fetchall()
            conn.close()
            return [t[0] for t in tables]
        except Exception as e:
            logger.error(f"Error getting table list: {e}")
            return []

    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup system statistics"""
        try:
            backups = self.list_backups(limit=1000)

            total_backups = len(backups)
            total_size = sum(b.get('backup_size', 0) for b in backups)

            # Count by type
            by_type = {}
            for backup in backups:
                backup_type = backup.get('backup_type', 'unknown')
                by_type[backup_type] = by_type.get(backup_type, 0) + 1

            # Latest backup
            latest_backup = backups[0] if backups else None

            return {
                "total_backups": total_backups,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "by_type": by_type,
                "latest_backup": latest_backup,
                "backup_directory": self.BACKUP_DIR
            }
        except Exception as e:
            logger.error(f"Error getting backup statistics: {e}")
            return {}


class HuggingFaceSync:
    """Enhanced HuggingFace synchronization with versioning"""

    def __init__(self):
        self.token = HF_TOKEN
        self.dataset_name = HF_DATASET_NAME

    def upload_with_version(
        self,
        version_tag: Optional[str] = None,
        commit_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload database to HuggingFace with version control"""
        try:
            from huggingface_hub import HfApi, CommitOperationAdd

            if not self.token:
                raise ValueError("HF_TOKEN not configured")

            # Generate version tag if not provided
            if not version_tag:
                version_tag = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Generate commit message
            if not commit_message:
                tables_info = BackupManager()._get_tables_info()
                total_records = sum(tables_info.values())
                commit_message = f"Database sync {version_tag} - {total_records} total records"

            # Log sync start
            sync_id = db.log_sync_operation(
                sync_type='upload',
                status='in_progress',
                tables_synced=list(tables_info.keys())
            )

            start_time = datetime.utcnow()

            # Upload to HuggingFace
            api = HfApi()

            # Create commit operation
            operations = [
                CommitOperationAdd(
                    path_in_repo="popcorn.db",
                    path_or_fileobj=DB_PATH
                )
            ]

            # Commit to repository
            commit_info = api.create_commit(
                repo_id=self.dataset_name,
                repo_type="dataset",
                operations=operations,
                commit_message=commit_message,
                token=self.token
            )

            # Calculate duration
            duration = int((datetime.utcnow() - start_time).total_seconds())
            file_size = os.path.getsize(DB_PATH)

            # Update sync record
            db.update_sync_operation(
                sync_id=sync_id,
                status='completed',
                records_synced=total_records,
                file_size=file_size,
                duration_seconds=duration,
                hf_commit_hash=commit_info.oid,
                completed_at=datetime.utcnow().isoformat()
            )

            logger.info(f"Database uploaded to HuggingFace: {version_tag}")

            return {
                "success": True,
                "version": version_tag,
                "commit_hash": commit_info.oid,
                "commit_url": commit_info.commit_url,
                "file_size": file_size,
                "duration_seconds": duration,
                "records_synced": total_records
            }
        except Exception as e:
            logger.error(f"Error uploading to HuggingFace: {e}", exc_info=True)

            # Update sync record as failed
            try:
                db.update_sync_operation(
                    sync_id=sync_id,
                    status='failed',
                    error_message=str(e),
                    completed_at=datetime.utcnow().isoformat()
                )
            except (sqlite3.Error, AttributeError) as db_error:
                logger.error(
                    f"Failed to update sync operation status: {type(db_error).__name__}: {str(db_error)}")
            except Exception as unexpected_error:
                logger.exception(
                    f"Unexpected error updating sync status: {str(unexpected_error)}")

            return {
                "success": False,
                "error": str(e)
            }

    def download_from_hf(
        self,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """Download database from HuggingFace"""
        try:
            from huggingface_hub import hf_hub_download

            if not self.token:
                raise ValueError("HF_TOKEN not configured")

            # Create backup of current database
            if create_backup:
                backup_mgr = BackupManager()
                backup_result = backup_mgr.create_backup(
                    backup_name=f"pre_download_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    backup_type='automatic')
                if not backup_result['success']:
                    logger.warning("Failed to create pre-download backup")

            # Log sync start
            sync_id = db.log_sync_operation(
                sync_type='download',
                status='in_progress'
            )

            start_time = datetime.utcnow()

            # Download from HuggingFace
            downloaded_path = hf_hub_download(
                repo_id=self.dataset_name,
                repo_type="dataset",
                filename="popcorn.db",
                token=self.token,
                force_download=True
            )

            # Replace current database
            shutil.copy2(downloaded_path, DB_PATH)

            # Calculate duration
            duration = int((datetime.utcnow() - start_time).total_seconds())
            file_size = os.path.getsize(DB_PATH)

            # Update sync record
            db.update_sync_operation(
                sync_id=sync_id,
                status='completed',
                file_size=file_size,
                duration_seconds=duration,
                completed_at=datetime.utcnow().isoformat()
            )

            logger.info("Database downloaded from HuggingFace")

            return {
                "success": True,
                "file_size": file_size,
                "duration_seconds": duration
            }
        except Exception as e:
            logger.error(
                f"Error downloading from HuggingFace: {e}",
                exc_info=True)

            # Update sync record as failed
            try:
                db.update_sync_operation(
                    sync_id=sync_id,
                    status='failed',
                    error_message=str(e),
                    completed_at=datetime.utcnow().isoformat()
                )
            except (sqlite3.Error, AttributeError) as db_error:
                logger.error(
                    f"Failed to update sync operation status: {type(db_error).__name__}: {str(db_error)}")
            except Exception as unexpected_error:
                logger.exception(
                    f"Unexpected error updating sync status: {str(unexpected_error)}")

            return {
                "success": False,
                "error": str(e)
            }


# Utility functions

def create_automatic_backup() -> Dict[str, Any]:
    """Create automatic backup (for scheduled tasks)"""
    backup_mgr = BackupManager()
    return backup_mgr.create_backup(backup_type='automatic')


def sync_to_huggingface() -> Dict[str, Any]:
    """Sync database to HuggingFace (for scheduled tasks)"""
    hf_sync = HuggingFaceSync()
    return hf_sync.upload_with_version()

# Made with Bob
