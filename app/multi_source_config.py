"""
Multi-Source Streaming Configuration
=====================================

This module manages multiple streaming bots and mirror groups for:
1. Load balancing across bots and groups
2. Bypassing Telegram file size limits
3. Ensuring high availability and redundancy
4. Automatic failover
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import time

@dataclass
class StreamBot:
    """Streaming bot configuration"""
    name: str
    token: str
    active: bool = True
    current_load: int = 0  # Number of active streams
    total_streams: int = 0  # Total streams served
    last_error: float = 0  # Timestamp of last error
    error_count: int = 0  # Consecutive errors
    
    def is_healthy(self) -> bool:
        """Check if bot is healthy and available"""
        if not self.active:
            return False
        
        # If bot had errors in last 5 minutes, consider unhealthy
        if self.error_count > 3 and (time.time() - self.last_error) < 300:
            return False
        
        return True
    
    def record_error(self):
        """Record an error for this bot"""
        self.error_count += 1
        self.last_error = time.time()
    
    def reset_errors(self):
        """Reset error counter (after successful stream)"""
        self.error_count = 0
        self.last_error = 0


@dataclass
class MirrorGroup:
    """Mirror group configuration"""
    name: str
    group_id: int
    active: bool = True
    current_load: int = 0  # Number of active streams from this group
    total_streams: int = 0  # Total streams served
    last_sync: float = 0  # Last sync timestamp
    file_count: int = 0  # Number of files in this group
    
    def is_healthy(self) -> bool:
        """Check if group is healthy and available"""
        return self.active and self.file_count > 0


# ============================================================================
# STREAMING BOTS CONFIGURATION
# ============================================================================

STREAM_BOTS: Dict[str, StreamBot] = {
    # Original bots
    "stream1": StreamBot(
        name="stream1",
        token="8719488711:AAFY5LKvNLANqJFA2BOHWN1ogENJzrqpRr4"
    ),
    "stream2": StreamBot(
        name="stream2",
        token="8358623405:AAEHWckq3vtdVjSebLuHC1a-BXUuSBJ2sCI"
    ),
    
    # New streaming bots
    "popcornapp1": StreamBot(
        name="popcornapp1",
        token="8601161145:AAFVGAET03TQeMCrf60ZpaKMPiJY6eZT57w"
    ),
    "str03": StreamBot(
        name="str03",
        token="8791203414:AAHtN2_K6ghUNAxUZkYsRdM8_c5m9TfYZmc"
    ),
    "str04": StreamBot(
        name="str04",
        token="8208972864:AAGk65FNEocCE0sqoPs22izpLEzYTVS4Dxg"
    ),
    "str05": StreamBot(
        name="str05",
        token="8619904355:AAGBVtb3waURI1nqvMpGCNIYxn5yGpqlbW0"
    ),
    "str06": StreamBot(
        name="str06",
        token="8487656110:AAHiBR1ZazVLyqyyy1rNz2EnU234lBpKLc8"
    ),
    "str07": StreamBot(
        name="str07",
        token="8504691467:AAHAfPRKdEjXQpAxQNKQ65enaGnQS-5DPvM"
    ),
    "str08": StreamBot(
        name="str08",
        token="8724259235:AAGkaFXMljHS7arRklCaecjO0iEh2udRHIs"
    ),
    "str09": StreamBot(
        name="str09",
        token="8677695221:AAEoIOADJv329KB0lebUndWkKMPUcUh236s"
    ),
    "str10": StreamBot(
        name="str10",
        token="8020247478:AAGYB37soYjNPO9b1_SuEcZSRnREr2d5UNU"
    ),
}

# ============================================================================
# MIRROR GROUPS CONFIGURATION
# ============================================================================

MIRROR_GROUPS: Dict[str, MirrorGroup] = {
    # Main group (primary source)
    "main": MirrorGroup(
        name="main",
        group_id=-1003826837517  # POPCORN DB (main)
    ),
    
    # Mirror groups
    "mirror1": MirrorGroup(
        name="mirror1",
        group_id=-1003951262474
    ),
    "mirror2": MirrorGroup(
        name="mirror2",
        group_id=-1003677704923
    ),
    "mirror3": MirrorGroup(
        name="mirror3",
        group_id=-1003959203452
    ),
    "mirror4": MirrorGroup(
        name="mirror4",
        group_id=-1003955245446
    ),
    "mirror5": MirrorGroup(
        name="mirror5",
        group_id=-1003571403410
    ),
    "mirror6": MirrorGroup(
        name="mirror6",
        group_id=-1003815795036
    ),
    "mirror7": MirrorGroup(
        name="mirror7",
        group_id=-1003988855078
    ),
    "mirror8": MirrorGroup(
        name="mirror8",
        group_id=-1003950953536
    ),
}

# ============================================================================
# SYNC CONFIGURATION
# ============================================================================

# Topics to ignore during sync (e.g., "General" for archiving)
IGNORED_TOPICS = [
    "General",
    "general",
    "عام",
    "الأرشيف",
    "Archive"
]

# Sync intervals (in seconds)
SYNC_INTERVALS = {
    "fast": 60,      # 1 minute - for active groups
    "normal": 300,   # 5 minutes - for normal groups
    "slow": 900,     # 15 minutes - for backup groups
}

# Maximum concurrent syncs
MAX_CONCURRENT_SYNCS = 3

# ============================================================================
# LOAD BALANCING CONFIGURATION
# ============================================================================

# Maximum load per bot before considering it "busy"
MAX_BOT_LOAD = 50

# Maximum load per group before considering it "busy"
MAX_GROUP_LOAD = 100

# Prefer bots/groups with load below this threshold
PREFERRED_LOAD_THRESHOLD = 20

# ============================================================================
# FILE SIZE LIMITS (Telegram restrictions)
# ============================================================================

# Telegram file size limits
TELEGRAM_BOT_FILE_LIMIT = 20 * 1024 * 1024  # 20 MB for bots
TELEGRAM_USER_FILE_LIMIT = 2 * 1024 * 1024 * 1024  # 2 GB for users

# Our strategy: Use chunked streaming for large files
CHUNK_SIZE = 512 * 1024  # 512 KB chunks
MAX_CHUNK_SIZE = 1024 * 1024  # 1 MB max chunk

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_least_loaded_bot() -> Tuple[str, StreamBot]:
    """Get the bot with the lowest current load"""
    healthy_bots = {
        name: bot for name, bot in STREAM_BOTS.items()
        if bot.is_healthy()
    }
    
    if not healthy_bots:
        # Fallback to first bot if all unhealthy
        return list(STREAM_BOTS.items())[0]
    
    # Sort by load, then by total streams (prefer less used bots)
    sorted_bots = sorted(
        healthy_bots.items(),
        key=lambda x: (x[1].current_load, x[1].total_streams)
    )
    
    return sorted_bots[0]


def get_least_loaded_group() -> Tuple[str, MirrorGroup]:
    """Get the group with the lowest current load"""
    healthy_groups = {
        name: group for name, group in MIRROR_GROUPS.items()
        if group.is_healthy()
    }
    
    if not healthy_groups:
        # Fallback to main group
        return "main", MIRROR_GROUPS["main"]
    
    # Sort by load, then by total streams
    sorted_groups = sorted(
        healthy_groups.items(),
        key=lambda x: (x[1].current_load, x[1].total_streams)
    )
    
    return sorted_groups[0]


def get_optimal_source() -> Tuple[str, StreamBot, str, MirrorGroup]:
    """
    Get the optimal bot and group combination for streaming.
    
    Returns:
        Tuple of (bot_name, bot, group_name, group)
    """
    bot_name, bot = get_least_loaded_bot()
    group_name, group = get_least_loaded_group()
    
    return bot_name, bot, group_name, group


def get_all_group_ids() -> List[int]:
    """Get list of all group IDs (for syncing)"""
    return [group.group_id for group in MIRROR_GROUPS.values()]


def get_active_group_ids() -> List[int]:
    """Get list of active group IDs only"""
    return [
        group.group_id for group in MIRROR_GROUPS.values()
        if group.active
    ]


def should_ignore_topic(topic_name: str) -> bool:
    """Check if a topic should be ignored during sync"""
    if not topic_name:
        return False
    
    topic_lower = topic_name.lower().strip()
    return any(
        ignored.lower() in topic_lower
        for ignored in IGNORED_TOPICS
    )


# ============================================================================
# STATISTICS
# ============================================================================

def get_system_stats() -> dict:
    """Get overall system statistics"""
    total_bots = len(STREAM_BOTS)
    healthy_bots = sum(1 for bot in STREAM_BOTS.values() if bot.is_healthy())
    total_bot_load = sum(bot.current_load for bot in STREAM_BOTS.values())
    total_bot_streams = sum(bot.total_streams for bot in STREAM_BOTS.values())
    
    total_groups = len(MIRROR_GROUPS)
    healthy_groups = sum(1 for group in MIRROR_GROUPS.values() if group.is_healthy())
    total_group_load = sum(group.current_load for group in MIRROR_GROUPS.values())
    total_group_streams = sum(group.total_streams for group in MIRROR_GROUPS.values())
    
    return {
        "bots": {
            "total": total_bots,
            "healthy": healthy_bots,
            "current_load": total_bot_load,
            "total_streams": total_bot_streams,
            "average_load": total_bot_load / total_bots if total_bots > 0 else 0
        },
        "groups": {
            "total": total_groups,
            "healthy": healthy_groups,
            "current_load": total_group_load,
            "total_streams": total_group_streams,
            "average_load": total_group_load / total_groups if total_groups > 0 else 0
        },
        "system": {
            "total_capacity": total_bots * MAX_BOT_LOAD,
            "used_capacity": total_bot_load,
            "capacity_percentage": (total_bot_load / (total_bots * MAX_BOT_LOAD) * 100) if total_bots > 0 else 0
        }
    }


def print_system_status():
    """Print system status (for debugging)"""
    stats = get_system_stats()
    
    print("\n" + "="*60)
    print("POPCORN STREAMING SYSTEM STATUS")
    print("="*60)
    
    print(f"\n📊 BOTS: {stats['bots']['healthy']}/{stats['bots']['total']} healthy")
    print(f"   Current Load: {stats['bots']['current_load']}")
    print(f"   Total Streams: {stats['bots']['total_streams']}")
    print(f"   Average Load: {stats['bots']['average_load']:.1f}")
    
    print(f"\n📁 GROUPS: {stats['groups']['healthy']}/{stats['groups']['total']} healthy")
    print(f"   Current Load: {stats['groups']['current_load']}")
    print(f"   Total Streams: {stats['groups']['total_streams']}")
    print(f"   Average Load: {stats['groups']['average_load']:.1f}")
    
    print(f"\n⚡ SYSTEM:")
    print(f"   Capacity: {stats['system']['used_capacity']}/{stats['system']['total_capacity']}")
    print(f"   Usage: {stats['system']['capacity_percentage']:.1f}%")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    # Test configuration
    print_system_status()
    
    print("Testing optimal source selection:")
    for i in range(5):
        bot_name, bot, group_name, group = get_optimal_source()
        print(f"  Stream {i+1}: Bot={bot_name}, Group={group_name}")
        bot.current_load += 1
        group.current_load += 1
    
    print("\nAfter load simulation:")
    print_system_status()

# Made with Bob
