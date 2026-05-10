#!/usr/bin/env python3
"""
Telegram Synchronization Monitoring Script
==========================================

Real-time monitoring of Telegram-to-Database synchronization across all groups.
Tracks:
- Messages processed per group
- Sync delays and failures
- Bot health status
- Database update rates
- Real-time alerts and reports
"""

import os
import sys
import asyncio
import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram.client import Client
from pyrogram.errors import FloodWait

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class GroupStats:
    """Statistics for a single group"""
    group_id: int
    group_name: str
    messages_processed: int = 0
    last_message_time: Optional[float] = None
    sync_errors: int = 0
    last_sync_time: Optional[float] = None
    is_accessible: bool = False
    bot_access: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.bot_access is None:
            self.bot_access = []

@dataclass
class BotStats:
    """Statistics for a single bot"""
    bot_name: str
    is_online: bool = False
    groups_accessible: int = 0
    messages_sent: int = 0
    errors: int = 0
    last_activity: Optional[float] = None

@dataclass
class SyncReport:
    """Complete synchronization report"""
    timestamp: float
    total_groups: int
    accessible_groups: int
    total_bots: int
    online_bots: int
    messages_processed: int
    sync_errors: int
    avg_sync_delay: float
    group_stats: Dict[str, GroupStats]
    bot_stats: Dict[str, BotStats]
    alerts: List[str]

# All groups to monitor
GROUPS = {
    "main": {"id": -1003826837517, "name": "POPCORN DB (Main)"},
    "private1": {"id": -1003951262474, "name": "Group Private 1"},
    "private2": {"id": -1003677704923, "name": "Group Private 2"},
    "private3": {"id": -1003959203452, "name": "Group Private 3"},
    "private4": {"id": -1003955245446, "name": "Group Private 4"},
    "private5": {"id": -1003571403410, "name": "Group Private 5"},
    "private6": {"id": -1003815795036, "name": "Group Private 6"},
    "private7": {"id": -1003988855078, "name": "Group Private 7"},
    "private8": {"id": -1003950953536, "name": "Group Private 8"},
}

# Bot tokens
BOTS = {
    "main_bot": "8710134678:AAGkOYggKyE4PrRlDCcu4tijkhwqTJw-GuI",
    "stream1": "8719488711:AAFY5LKvNLANqJFA2BOHWN1ogENJzrqpRr4",
    "stream2": "8358623405:AAEHWckq3vtdVjSebLuHC1a-BXUuSBJ2sCI",
    "popcornapp1": "8601161145:AAFVGAET03TQeMCrf60ZpaKMPiJY6eZT57w",
    "str03": "8791203414:AAHtN2_K6ghUNAxUZkYsRdM8_c5m9TfYZmc",
    "str04": "8208972864:AAGk65FNEocCE0sqoPs22izpLEzYTVS4Dxg",
    "str05": "8619904355:AAGBVtb3waURI1nqvMpGCNIYxn5yGpqlbW0",
    "str06": "8487656110:AAHiBR1ZazVLyqyyy1rNz2EnU234lBpKLc8",
    "str07": "8504691467:AAHAfPRKdEjXQpAxQNKQ65enaGnQS-5DPvM",
    "str08": "8724259235:AAGkaFXMljHS7arRklCaecjO0iEh2udRHIs",
    "str09": "8677695221:AAEoIOADJv329KB0lebUndWkKMPUcUh236s",
    "str10": "8020247478:AAGYB37soYjNPO9b1_SuEcZSRnREr2d5UNU",
}

# Session configuration
SESSION_1_API_ID = int(os.getenv("SESSION_1_API_ID", "32360090"))
SESSION_1_API_HASH = os.getenv("SESSION_1_API_HASH", "c7b022dcf0b1d3021197857e51be9375")

# ============================================================================
# MONITORING CLASS
# ============================================================================

class TelegramSyncMonitor:
    """Monitor Telegram synchronization across all groups"""
    
    def __init__(self):
        self.group_stats: Dict[str, GroupStats] = {}
        self.bot_stats: Dict[str, BotStats] = {}
        self.alerts: List[str] = []
        self.start_time = time.time()
        
        # Initialize stats
        for key, group in GROUPS.items():
            self.group_stats[key] = GroupStats(
                group_id=group["id"],
                group_name=group["name"]
            )
        
        for bot_name in BOTS.keys():
            self.bot_stats[bot_name] = BotStats(bot_name=bot_name)
    
    async def check_bot_status(self, bot_name: str, bot_token: str) -> bool:
        """Check if a bot is online and responsive"""
        try:
            client = Client(
                f"monitor_{bot_name}",
                api_id=SESSION_1_API_ID,
                api_hash=SESSION_1_API_HASH,
                bot_token=bot_token,
                in_memory=True
            )
            
            await client.start()
            me = await client.get_me()
            await client.stop()
            
            self.bot_stats[bot_name].is_online = True
            self.bot_stats[bot_name].last_activity = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Bot {bot_name} check failed: {e}")
            self.bot_stats[bot_name].is_online = False
            self.bot_stats[bot_name].errors += 1
            return False
    
    async def check_group_access(self, bot_name: str, bot_token: str, group_key: str, group_id: int) -> bool:
        """Check if a bot can access a specific group"""
        try:
            client = Client(
                f"monitor_{bot_name}_{abs(group_id)}",
                api_id=SESSION_1_API_ID,
                api_hash=SESSION_1_API_HASH,
                bot_token=bot_token,
                in_memory=True
            )
            
            await client.start()
            chat = await client.get_chat(group_id)
            await client.stop()
            
            self.group_stats[group_key].is_accessible = True
            bot_access = self.group_stats[group_key].bot_access or []
            if bot_name not in bot_access:
                bot_access.append(bot_name)
                self.group_stats[group_key].bot_access = bot_access
            self.bot_stats[bot_name].groups_accessible += 1
            
            return True
            
        except Exception as e:
            logger.debug(f"Bot {bot_name} cannot access {group_key}: {e}")
            return False
    
    async def check_recent_messages(self, group_key: str, group_id: int) -> int:
        """Check recent messages in a group"""
        try:
            # Use first available bot that has access
            bot_name = None
            bot_token = None
            
            for name, token in BOTS.items():
                bot_access = self.group_stats[group_key].bot_access or []
                if name in bot_access:
                    bot_name = name
                    bot_token = token
                    break
            
            if not bot_name or not bot_token:
                return 0
            
            client = Client(
                f"monitor_messages_{abs(group_id)}",
                api_id=SESSION_1_API_ID,
                api_hash=SESSION_1_API_HASH,
                bot_token=bot_token,
                in_memory=True
            )
            
            await client.start()
            
            # Get last 10 messages
            message_count = 0
            async for message in client.get_chat_history(group_id, limit=10):
                message_count += 1
                if message.date:
                    msg_time = message.date.timestamp()
                    if not self.group_stats[group_key].last_message_time or msg_time > self.group_stats[group_key].last_message_time:
                        self.group_stats[group_key].last_message_time = msg_time
            
            await client.stop()
            
            self.group_stats[group_key].messages_processed += message_count
            return message_count
            
        except Exception as e:
            logger.error(f"Error checking messages in {group_key}: {e}")
            self.group_stats[group_key].sync_errors += 1
            return 0
    
    async def run_health_check(self):
        """Run complete health check"""
        logger.info("="*80)
        logger.info("🔍 RUNNING HEALTH CHECK")
        logger.info("="*80)
        
        # Check all bots
        logger.info("\n📱 Checking bot status...")
        bot_tasks = [
            self.check_bot_status(name, token)
            for name, token in BOTS.items()
        ]
        await asyncio.gather(*bot_tasks, return_exceptions=True)
        
        # Check group access
        logger.info("\n🔐 Checking group access...")
        access_tasks = []
        for bot_name, bot_token in BOTS.items():
            if self.bot_stats[bot_name].is_online:
                for group_key, group in GROUPS.items():
                    access_tasks.append(
                        self.check_group_access(bot_name, bot_token, group_key, group["id"])
                    )
        
        await asyncio.gather(*access_tasks, return_exceptions=True)
        
        # Check recent messages
        logger.info("\n📨 Checking recent messages...")
        message_tasks = [
            self.check_recent_messages(key, group["id"])
            for key, group in GROUPS.items()
            if self.group_stats[key].is_accessible
        ]
        await asyncio.gather(*message_tasks, return_exceptions=True)
    
    def generate_alerts(self):
        """Generate alerts based on current stats"""
        self.alerts = []
        
        # Check for inaccessible groups
        for key, stats in self.group_stats.items():
            if not stats.is_accessible:
                self.alerts.append(f"⚠️ CRITICAL: {stats.group_name} is not accessible by any bot!")
            else:
                bot_access = stats.bot_access or []
                if len(bot_access) < 2:
                    self.alerts.append(f"⚠️ WARNING: {stats.group_name} only accessible by {len(bot_access)} bot(s)")
        
        # Check for offline bots
        offline_bots = [name for name, stats in self.bot_stats.items() if not stats.is_online]
        if offline_bots:
            self.alerts.append(f"⚠️ WARNING: {len(offline_bots)} bot(s) offline: {', '.join(offline_bots)}")
        
        # Check for sync delays
        current_time = time.time()
        for key, stats in self.group_stats.items():
            if stats.last_message_time:
                delay = current_time - stats.last_message_time
                if delay > 3600:  # 1 hour
                    self.alerts.append(f"⚠️ WARNING: {stats.group_name} has no new messages for {delay/3600:.1f} hours")
    
    def generate_report(self) -> SyncReport:
        """Generate comprehensive sync report"""
        self.generate_alerts()
        
        total_messages = sum(s.messages_processed for s in self.group_stats.values())
        total_errors = sum(s.sync_errors for s in self.group_stats.values())
        accessible_groups = sum(1 for s in self.group_stats.values() if s.is_accessible)
        online_bots = sum(1 for s in self.bot_stats.values() if s.is_online)
        
        # Calculate average sync delay
        delays = []
        current_time = time.time()
        for stats in self.group_stats.values():
            if stats.last_message_time:
                delays.append(current_time - stats.last_message_time)
        avg_delay = sum(delays) / len(delays) if delays else 0
        
        return SyncReport(
            timestamp=time.time(),
            total_groups=len(GROUPS),
            accessible_groups=accessible_groups,
            total_bots=len(BOTS),
            online_bots=online_bots,
            messages_processed=total_messages,
            sync_errors=total_errors,
            avg_sync_delay=avg_delay,
            group_stats=self.group_stats,
            bot_stats=self.bot_stats,
            alerts=self.alerts
        )
    
    def print_report(self, report: SyncReport):
        """Print formatted report"""
        logger.info("\n" + "="*80)
        logger.info("📊 TELEGRAM SYNC MONITORING REPORT")
        logger.info("="*80)
        logger.info(f"Timestamp: {datetime.fromtimestamp(report.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Uptime: {(report.timestamp - self.start_time)/60:.1f} minutes")
        
        logger.info("\n📈 OVERALL STATS:")
        logger.info(f"   Groups: {report.accessible_groups}/{report.total_groups} accessible")
        logger.info(f"   Bots: {report.online_bots}/{report.total_bots} online")
        logger.info(f"   Messages Processed: {report.messages_processed}")
        logger.info(f"   Sync Errors: {report.sync_errors}")
        logger.info(f"   Avg Sync Delay: {report.avg_sync_delay/60:.1f} minutes")
        
        logger.info("\n📁 GROUP STATUS:")
        for key, stats in report.group_stats.items():
            status = "✅" if stats.is_accessible else "❌"
            logger.info(f"   {status} {stats.group_name}")
            logger.info(f"      Messages: {stats.messages_processed}, Errors: {stats.sync_errors}")
            logger.info(f"      Accessible by: {', '.join(stats.bot_access) if stats.bot_access else 'None'}")
            if stats.last_message_time:
                last_msg = datetime.fromtimestamp(stats.last_message_time).strftime('%H:%M:%S')
                logger.info(f"      Last message: {last_msg}")
        
        logger.info("\n🤖 BOT STATUS:")
        for name, stats in report.bot_stats.items():
            status = "🟢" if stats.is_online else "🔴"
            logger.info(f"   {status} {name}: {stats.groups_accessible} groups, {stats.errors} errors")
        
        if report.alerts:
            logger.info("\n⚠️ ALERTS:")
            for alert in report.alerts:
                logger.warning(f"   {alert}")
        
        logger.info("\n" + "="*80)
    
    async def monitor_loop(self, interval: int = 60):
        """Continuous monitoring loop"""
        logger.info(f"🚀 Starting continuous monitoring (interval: {interval}s)")
        
        while True:
            try:
                await self.run_health_check()
                report = self.generate_report()
                self.print_report(report)
                
                # Save report to file
                report_file = Path(__file__).parent / "telegram_sync_report.json"
                with open(report_file, 'w') as f:
                    json.dump({
                        "timestamp": report.timestamp,
                        "total_groups": report.total_groups,
                        "accessible_groups": report.accessible_groups,
                        "total_bots": report.total_bots,
                        "online_bots": report.online_bots,
                        "messages_processed": report.messages_processed,
                        "sync_errors": report.sync_errors,
                        "avg_sync_delay": report.avg_sync_delay,
                        "alerts": report.alerts,
                        "group_stats": {k: asdict(v) for k, v in report.group_stats.items()},
                        "bot_stats": {k: asdict(v) for k, v in report.bot_stats.items()}
                    }, f, indent=2, default=str)
                
                logger.info(f"💾 Report saved to: {report_file}")
                
                # Wait for next check
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("\n⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main execution function"""
    monitor = TelegramSyncMonitor()
    
    # Run single check or continuous monitoring
    import argparse
    parser = argparse.ArgumentParser(description="Monitor Telegram sync")
    parser.add_argument("--continuous", action="store_true", help="Run continuous monitoring")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    args = parser.parse_args()
    
    if args.continuous:
        await monitor.monitor_loop(interval=args.interval)
    else:
        await monitor.run_health_check()
        report = monitor.generate_report()
        monitor.print_report(report)

if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob