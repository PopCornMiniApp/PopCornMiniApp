"""
Periodic Tasks Manager
======================

This module manages all periodic background tasks:
1. Health monitoring (every 5 minutes)
2. Mirror verification (every hour)
3. Mirror maintenance and repair (every hour)
4. Incremental sync (every minute)
5. Full sync (every hour)
6. Statistics calculation (every hour)
7. Cleanup tasks (daily)
"""

import asyncio
import logging
from typing import Optional

from app.config import (
    HEALTH_CHECK_INTERVAL,
    MIRROR_VERIFICATION_INTERVAL,
    MIRROR_MAINTENANCE_INTERVAL,
    INCREMENTAL_SYNC_INTERVAL,
    FULL_SYNC_INTERVAL,
    HEALTH_MONITORING_ENABLED,
    MIRROR_REPAIR_ENABLED
)

logger = logging.getLogger(__name__)

# ============================================================================
# PERIODIC TASKS MANAGER
# ============================================================================


class PeriodicTasksManager:
    """
    Manages all periodic background tasks
    """

    def __init__(self):
        self._running = False
        self._tasks: dict[str, Optional[asyncio.Task]] = {}
        self._last_run: dict[str, float] = {}

    async def start_all_tasks(self):
        """Start all periodic tasks"""
        if self._running:
            logger.warning("Periodic tasks already running")
            return

        self._running = True
        logger.info("🚀 Starting all periodic tasks...")

        # Start health monitoring
        if HEALTH_MONITORING_ENABLED:
            self._tasks["health_monitor"] = asyncio.create_task(
                self._health_monitoring_loop()
            )
            logger.info(
                f"✅ Health monitoring started (interval: {HEALTH_CHECK_INTERVAL}s)")

        # Start mirror verification
        self._tasks["mirror_verification"] = asyncio.create_task(
            self._mirror_verification_loop()
        )
        logger.info(
            f"✅ Mirror verification started (interval: {MIRROR_VERIFICATION_INTERVAL}s)")

        # Start mirror maintenance
        if MIRROR_REPAIR_ENABLED:
            self._tasks["mirror_maintenance"] = asyncio.create_task(
                self._mirror_maintenance_loop()
            )
            logger.info(
                f"✅ Mirror maintenance started (interval: {MIRROR_MAINTENANCE_INTERVAL}s)")

        # Start incremental sync
        self._tasks["incremental_sync"] = asyncio.create_task(
            self._incremental_sync_loop()
        )
        logger.info(
            f"✅ Incremental sync started (interval: {INCREMENTAL_SYNC_INTERVAL}s)")

        # Start full sync
        self._tasks["full_sync"] = asyncio.create_task(
            self._full_sync_loop()
        )
        logger.info(f"✅ Full sync started (interval: {FULL_SYNC_INTERVAL}s)")

        # Start statistics calculation
        self._tasks["statistics"] = asyncio.create_task(
            self._statistics_loop()
        )
        logger.info("✅ Statistics calculation started (interval: 3600s)")

        # Start cleanup tasks
        self._tasks["cleanup"] = asyncio.create_task(
            self._cleanup_loop()
        )
        logger.info("✅ Cleanup tasks started (interval: 86400s)")

        logger.info("✅ All periodic tasks started successfully")

    async def stop_all_tasks(self):
        """Stop all periodic tasks"""
        if not self._running:
            return

        self._running = False
        logger.info("⏹️ Stopping all periodic tasks...")

        for task_name, task in self._tasks.items():
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.info(f"⏹️ Stopped: {task_name}")

        self._tasks.clear()
        logger.info("✅ All periodic tasks stopped")

    async def _health_monitoring_loop(self):
        """Health monitoring loop"""
        while self._running:
            try:
                from app.health_monitor import check_system_health

                logger.info("🔍 Running health check...")
                result = await check_system_health()

                self._last_run["health_monitor"] = asyncio.get_event_loop(
                ).time()

                logger.info(
                    f"✅ Health check complete: {result.status.upper()} - "
                    f"Bots: {result.healthy_bots}/{result.total_bots}, "
                    f"Groups: {result.healthy_groups}/{result.total_groups}"
                )

                await asyncio.sleep(HEALTH_CHECK_INTERVAL)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _mirror_verification_loop(self):
        """Mirror verification loop"""
        while self._running:
            try:
                from app.mirror_manager import mirror_manager

                if not mirror_manager._initialized:
                    logger.warning(
                        "Mirror manager not initialized, skipping verification")
                    await asyncio.sleep(MIRROR_VERIFICATION_INTERVAL)
                    continue

                logger.info("🔍 Running mirror verification...")

                # Verify a batch of mirrors
                verified_count = 0
                for file_id in list(
                        mirror_manager.file_mirrors.keys())[
                        :100]:  # Verify 100 at a time
                    try:
                        result = await mirror_manager.verify_mirrors(file_id)
                        if result.get("success"):
                            verified_count += 1
                    except Exception as e:
                        logger.error(f"Error verifying {file_id}: {e}")

                self._last_run["mirror_verification"] = asyncio.get_event_loop(
                ).time()

                logger.info(
                    f"✅ Mirror verification complete: verified {verified_count} files")

                await asyncio.sleep(MIRROR_VERIFICATION_INTERVAL)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in mirror verification loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _mirror_maintenance_loop(self):
        """Mirror maintenance and repair loop"""
        while self._running:
            try:
                from app.mirror_manager import run_mirror_maintenance

                logger.info("🔧 Running mirror maintenance...")
                result = await run_mirror_maintenance()

                self._last_run["mirror_maintenance"] = asyncio.get_event_loop(
                ).time()

                logger.info(
                    "✅ Mirror maintenance complete: "
                    f"verified={result.get('verified', 0)}, "
                    f"repaired={result.get('repaired', 0)}"
                )

                await asyncio.sleep(MIRROR_MAINTENANCE_INTERVAL)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in mirror maintenance loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _incremental_sync_loop(self):
        """Incremental sync loop"""
        last_message_id = 0

        while self._running:
            try:
                from app.multi_group_sync import run_incremental_sync

                logger.info(
                    f"🔄 Running incremental sync from message {last_message_id}...")
                result = await run_incremental_sync(last_message_id)

                # Update last message ID
                if result.get("last_message_id"):
                    last_message_id = result["last_message_id"]

                self._last_run["incremental_sync"] = asyncio.get_event_loop(
                ).time()

                logger.info(
                    "✅ Incremental sync complete: "
                    f"new_items={result.get('new_items', 0)}, "
                    f"synced={result.get('synced', 0)}"
                )

                await asyncio.sleep(INCREMENTAL_SYNC_INTERVAL)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in incremental sync loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _full_sync_loop(self):
        """Full sync loop"""
        while self._running:
            try:
                from app.multi_group_sync import run_full_sync

                logger.info("🔄 Running full sync...")
                result = await run_full_sync(limit=1000)

                self._last_run["full_sync"] = asyncio.get_event_loop().time()

                logger.info(
                    "✅ Full sync complete: "
                    f"total_items={result.get('total_items', 0)}, "
                    f"synced={result.get('synced', 0)}, "
                    f"duration={result.get('duration', 0):.2f}s"
                )

                await asyncio.sleep(FULL_SYNC_INTERVAL)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in full sync loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _statistics_loop(self):
        """Statistics calculation loop"""
        while self._running:
            try:
                from app.database import calculate_user_statistics, get_connection

                logger.info("📊 Calculating user statistics...")

                # Get all users
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT user_id FROM users WHERE is_blocked = 0")
                users = cursor.fetchall()

                calculated_count = 0
                for (user_id,) in users:
                    try:
                        await calculate_user_statistics(user_id)
                        calculated_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error calculating stats for user {user_id}: {e}")

                self._last_run["statistics"] = asyncio.get_event_loop().time()

                logger.info(
                    f"✅ Statistics calculation complete: {calculated_count} users")

                await asyncio.sleep(3600)  # Every hour

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in statistics loop: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _cleanup_loop(self):
        """Cleanup tasks loop"""
        while self._running:
            try:
                from app.database import get_connection

                logger.info("🧹 Running cleanup tasks...")

                conn = get_connection()
                cursor = conn.cursor()

                # Clean up old sessions (older than 7 days)
                cursor.execute("""
                    DELETE FROM user_sessions
                    WHERE is_active = 0
                    AND datetime(logout_time) < datetime('now', '-7 days')
                """)
                deleted_sessions = cursor.rowcount

                # Clean up old analytics (older than 90 days)
                cursor.execute("""
                    DELETE FROM analytics_views
                    WHERE datetime(created_at) < datetime('now', '-90 days')
                """)
                deleted_views = cursor.rowcount

                cursor.execute("""
                    DELETE FROM analytics_searches
                    WHERE datetime(created_at) < datetime('now', '-90 days')
                """)
                deleted_searches = cursor.rowcount

                cursor.execute("""
                    DELETE FROM analytics_errors
                    WHERE datetime(created_at) < datetime('now', '-30 days')
                """)
                deleted_errors = cursor.rowcount

                conn.commit()

                self._last_run["cleanup"] = asyncio.get_event_loop().time()

                logger.info(
                    "✅ Cleanup complete: "
                    f"sessions={deleted_sessions}, "
                    f"views={deleted_views}, "
                    f"searches={deleted_searches}, "
                    f"errors={deleted_errors}"
                )

                await asyncio.sleep(86400)  # Every 24 hours

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    def get_status(self) -> dict:
        """Get status of all periodic tasks"""
        return {
            "running": self._running,
            "tasks": {
                name: {
                    "active": task is not None and not task.done(),
                    "last_run": self._last_run.get(name, 0)
                }
                for name, task in self._tasks.items()
            }
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global periodic tasks manager
periodic_tasks_manager = PeriodicTasksManager()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def start_periodic_tasks():
    """Start all periodic tasks"""
    await periodic_tasks_manager.start_all_tasks()
    logger.info("✅ Periodic tasks system started")


async def stop_periodic_tasks():
    """Stop all periodic tasks"""
    await periodic_tasks_manager.stop_all_tasks()
    logger.info("⏹️ Periodic tasks system stopped")


def get_periodic_tasks_status() -> dict:
    """Get status of periodic tasks"""
    return periodic_tasks_manager.get_status()


# Made with Bob
