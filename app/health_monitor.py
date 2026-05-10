"""
Health Monitoring System
========================

This module monitors the health of all system components:
1. Bot health monitoring (response time, error rates)
2. Group health monitoring (accessibility, file counts)
3. Automatic health checks and reporting
4. Performance metrics tracking
5. Alert generation for issues
"""

import asyncio
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass

from pyrogram.client import Client
from pyrogram.errors import ChannelPrivate, ChatAdminRequired

from app.multi_source_config import STREAM_BOTS, MIRROR_GROUPS
from app.database import get_connection

logger = logging.getLogger(__name__)

# ============================================================================
# DATA STRUCTURES
# ============================================================================


@dataclass
class BotHealth:
    """Bot health status"""
    bot_name: str
    status: str  # 'healthy', 'degraded', 'down'
    response_time: float = 0
    success_rate: float = 100.0
    error_count: int = 0
    last_check: float = 0
    last_error: Optional[str] = None
    uptime_percentage: float = 100.0


@dataclass
class GroupHealth:
    """Group health status"""
    group_id: int
    group_name: str
    status: str  # 'active', 'slow', 'down'
    response_time: float = 0
    file_count: int = 0
    total_size: int = 0
    last_check: float = 0
    last_error: Optional[str] = None
    accessibility: bool = True


@dataclass
class SystemHealth:
    """Overall system health"""
    status: str  # 'healthy', 'degraded', 'critical'
    healthy_bots: int = 0
    total_bots: int = 0
    healthy_groups: int = 0
    total_groups: int = 0
    avg_response_time: float = 0
    total_errors: int = 0
    last_check: float = 0


# ============================================================================
# HEALTH MONITOR
# ============================================================================

class HealthMonitor:
    """
    Monitors health of all system components
    """

    def __init__(self, check_interval: int = 300):
        """
        Initialize health monitor

        Args:
            check_interval: Seconds between health checks (default: 5 minutes)
        """
        self.check_interval = check_interval
        self.bot_health: Dict[str, BotHealth] = {}
        self.group_health: Dict[int, GroupHealth] = {}
        self.system_health = SystemHealth(status='unknown')
        self._user_client: Optional[Client] = None
        self._bot_clients: Dict[str, Client] = {}
        self._initialized = False
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def initialize(
        self,
        user_client: Client,
        bot_clients: Optional[Dict[str, Client]] = None
    ):
        """
        Initialize the health monitor

        Args:
            user_client: Pyrogram user client
            bot_clients: Dict of bot clients (optional)
        """
        if self._initialized:
            logger.info("HealthMonitor already initialized")
            return

        self._user_client = user_client
        self._bot_clients = bot_clients or {}

        # Initialize bot health tracking
        for bot_name in STREAM_BOTS.keys():
            self.bot_health[bot_name] = BotHealth(
                bot_name=bot_name,
                status='unknown'
            )

        # Initialize group health tracking
        for group_name, group_config in MIRROR_GROUPS.items():
            self.group_health[group_config.group_id] = GroupHealth(
                group_id=group_config.group_id,
                group_name=group_name,
                status='unknown'
            )

        # Load historical data from database
        await self._load_health_data()

        self._initialized = True
        logger.info("✅ HealthMonitor initialized")

    async def _load_health_data(self):
        """Load historical health data from database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Load group health
            cursor.execute("""
                SELECT group_id, status, response_time, file_count,
                       total_size, last_check
                FROM group_health
                ORDER BY last_check DESC
            """)

            for row in cursor.fetchall():
                group_id = row[0]
                if group_id in self.group_health:
                    self.group_health[group_id].status = row[1]
                    self.group_health[group_id].response_time = row[2]  # noqa: F841
                    self.group_health[group_id].file_count = row[3]
                    self.group_health[group_id].total_size = row[4]
                    self.group_health[group_id].last_check = row[5]

            # Load bot stats
            cursor.execute("""
                SELECT bot_id, requests_count, success_count, failure_count,
                       avg_response_time, last_used, status
                FROM bot_stats
                ORDER BY last_used DESC
            """)

            for row in cursor.fetchall():
                bot_id = row[0]
                if bot_id in self.bot_health:
                    requests = row[1]
                    success = row[2]
                    failure = row[3]

                    if requests > 0:
                        success_rate = (success / requests) * 100
                        self.bot_health[bot_id].success_rate = success_rate

                    self.bot_health[bot_id].response_time = row[4]  # noqa: F841
                    self.bot_health[bot_id].error_count = failure
                    self.bot_health[bot_id].last_check = row[5]
                    self.bot_health[bot_id].status = row[6] or 'unknown'

            logger.info("📊 Loaded health data from database")

        except Exception as e:
            logger.error(f"Error loading health data: {e}")

    async def check_bot_health(self, bot_name: str) -> BotHealth:
        """
        Check health of a specific bot

        Args:
            bot_name: Bot name to check

        Returns:
            BotHealth object
        """
        health = self.bot_health.get(bot_name)
        if not health:
            health = BotHealth(bot_name=bot_name, status='unknown')
            self.bot_health[bot_name] = health

        bot_config = STREAM_BOTS.get(bot_name)
        if not bot_config:
            health.status = 'down'
            health.last_error = "Bot not configured"
            return health

        # Check if bot is marked as active
        if not bot_config.active:
            health.status = 'down'
            health.last_error = "Bot disabled"
            return health

        # Check bot client availability
        bot_client = self._bot_clients.get(bot_name)
        if not bot_client:
            health.status = 'degraded'
            health.last_error = "Client not available"
            return health

        # Perform health check
        start_time = time.time()  # noqa: F841

        try:
            # Try to get bot info (lightweight check)
            me = await asyncio.wait_for(  # noqa: F841
                bot_client.get_me(),
                timeout=10
            )

            response_time = time.time() - start_time  # noqa: F841
            health.response_time = response_time  # noqa: F841
            health.last_check = time.time()

            # Determine status based on response time and error count
            if response_time < 1.0 and bot_config.error_count < 3:
                health.status = 'healthy'
            elif response_time < 3.0 and bot_config.error_count < 5:
                health.status = 'degraded'
            else:
                health.status = 'down'

            health.error_count = bot_config.error_count
            health.success_rate = max(0, 100 - (bot_config.error_count * 10))
            health.last_error = None

        except asyncio.TimeoutError:
            health.status = 'down'
            health.last_error = "Timeout"
            health.response_time = 10.0  # noqa: F841

        except Exception as e:
            health.status = 'down'
            health.last_error = str(e)
            health.response_time = time.time() - start_time  # noqa: F841

        # Update database
        await self._save_bot_health(bot_name, health)

        return health

    async def check_group_health(self, group_id: int) -> GroupHealth:
        """
        Check health of a specific group

        Args:
            group_id: Group ID to check

        Returns:
            GroupHealth object
        """
        health = self.group_health.get(group_id)
        if not health:
            # Find group name
            group_name = next(  # noqa: F841
                (name for name,
                 g in MIRROR_GROUPS.items() if g.group_id == group_id),
                f"group_{group_id}")
            health = GroupHealth(
                group_id=group_id,
                group_name=group_name,
                status='unknown'
            )
            self.group_health[group_id] = health

        if not self._user_client:
            health.status = 'down'
            health.last_error = "User client not available"
            return health

        start_time = time.time()  # noqa: F841

        try:
            # Try to get chat info
            chat = await asyncio.wait_for(  # noqa: F841
                self._user_client.get_chat(group_id),
                timeout=10
            )

            response_time = time.time() - start_time  # noqa: F841
            health.response_time = response_time  # noqa: F841
            health.last_check = time.time()
            health.accessibility = True

            # Get file count from database
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*), COALESCE(SUM(file_size), 0)
                FROM file_mirrors
                WHERE group_id = ?
            """, (group_id,))

            row = cursor.fetchone()
            if row:
                health.file_count = row[0]
                health.total_size = row[1]

            # Determine status
            if response_time < 2.0:
                health.status = 'active'
            elif response_time < 5.0:
                health.status = 'slow'
            else:
                health.status = 'down'

            health.last_error = None

        except asyncio.TimeoutError:
            health.status = 'down'
            health.last_error = "Timeout"
            health.accessibility = False

        except (ChannelPrivate, ChatAdminRequired) as e:
            health.status = 'down'
            health.last_error = f"Access denied: {type(e).__name__}"
            health.accessibility = False

        except Exception as e:
            health.status = 'down'
            health.last_error = str(e)
            health.accessibility = False

        # Update database
        await self._save_group_health(group_id, health)

        return health

    async def check_all_health(self) -> SystemHealth:
        """
        Check health of all components

        Returns:
            SystemHealth object
        """
        logger.info("🔍 Running comprehensive health check...")

        # Check all bots
        bot_tasks = [
            self.check_bot_health(bot_name)
            for bot_name in STREAM_BOTS.keys()
        ]
        bot_results = await asyncio.gather(*bot_tasks, return_exceptions=True)

        # Check all groups
        group_tasks = [
            self.check_group_health(group_id)
            for group_id in self.group_health.keys()
        ]
        group_results = await asyncio.gather(*group_tasks, return_exceptions=True)

        # Calculate system health
        healthy_bots = sum(
            1 for r in bot_results
            if isinstance(r, BotHealth) and r.status == 'healthy'
        )

        healthy_groups = sum(
            1 for r in group_results
            if isinstance(r, GroupHealth) and r.status == 'active'
        )

        total_bots = len(STREAM_BOTS)
        total_groups = len(self.group_health)

        # Calculate average response time
        response_times = []
        for r in bot_results:
            if isinstance(r, BotHealth) and r.response_time > 0:
                response_times.append(r.response_time)
        for r in group_results:
            if isinstance(r, GroupHealth) and r.response_time > 0:
                response_times.append(r.response_time)

        avg_response_time = (  # noqa: F841
            sum(response_times) / len(response_times)
            if response_times else 0
        )

        # Count total errors
        total_errors = sum(
            r.error_count for r in bot_results
            if isinstance(r, BotHealth)
        )

        # Determine overall status
        bot_health_ratio = healthy_bots / total_bots if total_bots > 0 else 0
        group_health_ratio = healthy_groups / total_groups if total_groups > 0 else 0

        if bot_health_ratio >= 0.8 and group_health_ratio >= 0.8:
            status = 'healthy'
        elif bot_health_ratio >= 0.5 and group_health_ratio >= 0.5:
            status = 'degraded'
        else:
            status = 'critical'

        self.system_health = SystemHealth(
            status=status,
            healthy_bots=healthy_bots,
            total_bots=total_bots,
            healthy_groups=healthy_groups,
            total_groups=total_groups,
            avg_response_time=avg_response_time,
            total_errors=total_errors,
            last_check=time.time()
        )

        logger.info(
            f"✅ Health check complete: {status.upper()} - "
            f"Bots: {healthy_bots}/{total_bots}, "
            f"Groups: {healthy_groups}/{total_groups}"
        )

        return self.system_health

    async def _save_bot_health(self, bot_name: str, health: BotHealth):
        """Save bot health to database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Get current stats
            cursor.execute("""
                SELECT requests_count, success_count, failure_count
                FROM bot_stats
                WHERE bot_id = ?
            """, (bot_name,))

            row = cursor.fetchone()
            if row:
                requests = row[0] + 1
                success = row[1] + (1 if health.status == 'healthy' else 0)
                failure = row[2] + (1 if health.status == 'down' else 0)
            else:
                requests = 1
                success = 1 if health.status == 'healthy' else 0
                failure = 1 if health.status == 'down' else 0

            cursor.execute("""
                INSERT OR REPLACE INTO bot_stats
                (bot_id, requests_count, success_count, failure_count,
                 avg_response_time, last_used, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                bot_name,
                requests,
                success,
                failure,
                health.response_time,
                health.last_check,
                health.status
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Error saving bot health: {e}")

    async def _save_group_health(self, group_id: int, health: GroupHealth):
        """Save group health to database"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO group_health
                (group_id, status, response_time, file_count, total_size, last_check)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                group_id,
                health.status,
                health.response_time,
                health.file_count,
                health.total_size,
                health.last_check
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Error saving group health: {e}")

    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._monitoring:
            logger.warning("Health monitoring already running")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"✅ Health monitoring started (interval: {self.check_interval}s)")

    async def stop_monitoring(self):
        """Stop health monitoring"""
        if not self._monitoring:
            return

        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("⏹️ Health monitoring stopped")

    async def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self._monitoring:
            try:
                await self.check_all_health()
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    def get_stats(self) -> Dict:
        """Get health monitoring statistics"""
        return {
            "system": {
                "status": self.system_health.status,
                "healthy_bots": self.system_health.healthy_bots,
                "total_bots": self.system_health.total_bots,
                "healthy_groups": self.system_health.healthy_groups,
                "total_groups": self.system_health.total_groups,
                "avg_response_time": self.system_health.avg_response_time,
                "total_errors": self.system_health.total_errors,
                "last_check": self.system_health.last_check
            },
            "bots": {
                name: {
                    "status": health.status,
                    "response_time": health.response_time,
                    "success_rate": health.success_rate,
                    "error_count": health.error_count,
                    "last_check": health.last_check,
                    "last_error": health.last_error
                }
                for name, health in self.bot_health.items()
            },
            "groups": {
                health.group_name: {
                    "group_id": group_id,
                    "status": health.status,
                    "response_time": health.response_time,
                    "file_count": health.file_count,
                    "total_size": health.total_size,
                    "accessibility": health.accessibility,
                    "last_check": health.last_check,
                    "last_error": health.last_error
                }
                for group_id, health in self.group_health.items()
            }
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global health monitor instance
health_monitor = HealthMonitor(check_interval=300)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def initialize_health_monitoring(
    user_client: Client,
    bot_clients: Optional[Dict[str, Client]] = None
):
    """Initialize the health monitoring system"""
    await health_monitor.initialize(user_client, bot_clients)
    logger.info("✅ Health monitoring system initialized")


async def start_health_monitoring():
    """Start continuous health monitoring"""
    await health_monitor.start_monitoring()


async def stop_health_monitoring():
    """Stop health monitoring"""
    await health_monitor.stop_monitoring()


async def check_system_health() -> SystemHealth:
    """Check overall system health"""
    return await health_monitor.check_all_health()


async def check_bot_health(bot_name: str) -> BotHealth:
    """Check specific bot health"""
    return await health_monitor.check_bot_health(bot_name)


async def check_group_health(group_id: int) -> GroupHealth:
    """Check specific group health"""
    return await health_monitor.check_group_health(group_id)


def get_health_stats() -> Dict:
    """Get health monitoring statistics"""
    return health_monitor.get_stats()


# Made with Bob
