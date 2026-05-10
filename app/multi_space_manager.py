"""
Multi-Space Manager for HuggingFace
Manages multiple Spaces across different accounts for load balancing and high availability
"""

import os
import time
import logging
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from threading import Lock

logger = logging.getLogger(__name__)


class SpaceStatus(Enum):
    """Space status enumeration"""
    RUNNING = "running"
    BUILDING = "building"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class SpacePriority(Enum):
    """Space priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class SpaceConfig:
    """Configuration for a HuggingFace Space"""
    name: str
    account: str
    token: str
    url: str
    purpose: str
    services: List[str]
    priority: SpacePriority
    health_check_endpoint: str = "/health"
    timeout_seconds: int = 10
    max_retries: int = 3

    # Runtime state
    status: SpaceStatus = SpaceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_error: Optional[str] = None


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    method: str = "round_robin"  # round_robin, least_connections, weighted
    health_check_interval: int = 30  # seconds
    failover_enabled: bool = True
    sticky_sessions: bool = False
    session_timeout: int = 3600  # seconds


class MultiSpaceManager:
    """
    Manages multiple HuggingFace Spaces for load balancing and high availability
    """

    def __init__(self, config: Optional[LoadBalancerConfig] = None):
        self.config = config or LoadBalancerConfig()
        self.spaces: Dict[str, SpaceConfig] = {}
        self.current_index = 0
        self.lock = Lock()
        # session_id -> (space_name, timestamp)
        self.sessions: Dict[str, Tuple[str, datetime]] = {}

        logger.info("MultiSpaceManager initialized")

    def register_space(self, space: SpaceConfig) -> None:
        """Register a new Space"""
        with self.lock:
            self.spaces[space.name] = space
            logger.info(f"Registered Space: {space.name} ({space.account})")

    def register_spaces_from_config(
            self, config_file: str = "hf_optimization_strategy.json") -> None:
        """Register Spaces from configuration file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            for account_config in config['distribution_strategy']['spaces']['distribution']:
                account = account_config['account']
                token = os.getenv(
                    f"HF_TOKEN_{account.upper().replace('-', '_')}", "")

                for space_data in account_config['spaces']:
                    if space_data['status'] == 'running' or space_data['status'] == 'planned':
                        space = SpaceConfig(
                            name=space_data['name'],
                            account=account,
                            token=token,
                            url=f"https://{account}-{space_data['name']}.hf.space",
                            purpose=space_data['purpose'],
                            services=space_data['services'],
                            priority=SpacePriority[space_data['priority'].upper()]
                        )
                        self.register_space(space)

            logger.info(f"Registered {len(self.spaces)} Spaces from config")

        except Exception as e:
            logger.error(f"Failed to register Spaces from config: {str(e)}")

    def check_space_health(self, space: SpaceConfig) -> bool:
        """Check if a Space is healthy"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{space.url}{space.health_check_endpoint}",
                timeout=space.timeout_seconds,
                headers={"Authorization": f"Bearer {space.token}"}
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                space.status = SpaceStatus.RUNNING
                space.consecutive_failures = 0
                space.last_health_check = datetime.utcnow()

                # Update average response time
                if space.average_response_time == 0:
                    space.average_response_time = response_time
                else:
                    space.average_response_time = (
                        space.average_response_time * 0.9) + (response_time * 0.1)

                logger.debug(
                    f"Space {space.name} is healthy (response time: {response_time:.2f}s)")
                return True
            else:
                raise Exception(f"HTTP {response.status_code}")

        except Exception as e:
            space.status = SpaceStatus.ERROR
            space.consecutive_failures += 1
            space.last_error = str(e)
            space.last_health_check = datetime.utcnow()

            logger.warning(f"Space {space.name} health check failed: {str(e)}")
            return False

    def get_healthy_spaces(
            self,
            priority: Optional[SpacePriority] = None) -> List[SpaceConfig]:
        """Get list of healthy Spaces, optionally filtered by priority"""
        healthy = []

        for space in self.spaces.values():
            # Check if health check is recent
            if space.last_health_check is None or (
                    datetime.utcnow() -
                    space.last_health_check).seconds > self.config.health_check_interval:
                self.check_space_health(space)

            # Filter by status and priority
            if space.status == SpaceStatus.RUNNING:
                if priority is None or space.priority == priority:
                    healthy.append(space)

        # Sort by priority and performance
        healthy.sort(key=lambda s: (s.priority.value, s.average_response_time))
        return healthy

    def select_space_round_robin(
            self, spaces: List[SpaceConfig]) -> Optional[SpaceConfig]:
        """Select Space using round-robin algorithm"""
        if not spaces:
            return None

        with self.lock:
            space = spaces[self.current_index % len(spaces)]
            self.current_index += 1
            return space

    def select_space_least_connections(
            self, spaces: List[SpaceConfig]) -> Optional[SpaceConfig]:
        """Select Space with least active connections"""
        if not spaces:
            return None

        # Calculate active connections (requests - successful - failed)
        spaces_with_load = [
            (space, space.total_requests - space.successful_requests - space.failed_requests)
            for space in spaces
        ]

        # Sort by load and response time
        spaces_with_load.sort(key=lambda x: (x[1], x[0].average_response_time))
        return spaces_with_load[0][0]

    def select_space_weighted(
            self,
            spaces: List[SpaceConfig]) -> Optional[SpaceConfig]:
        """Select Space using weighted algorithm based on priority and performance"""
        if not spaces:
            return None

        # Calculate weights (lower is better)
        weights = []
        for space in spaces:
            # Weight based on priority (1-4) and response time
            weight = space.priority.value * \
                space.average_response_time if space.average_response_time > 0 else space.priority.value
            weights.append(1.0 / weight if weight > 0 else 1.0)

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return spaces[0]

        normalized_weights = [w / total_weight for w in weights]

        # Select based on weights
        import random
        return random.choices(spaces, weights=normalized_weights)[0]

    def get_space_for_request(
            self,
            session_id: Optional[str] = None,
            priority: Optional[SpacePriority] = None) -> Optional[SpaceConfig]:
        """
        Get the best Space for handling a request

        Args:
            session_id: Optional session ID for sticky sessions
            priority: Optional priority filter

        Returns:
            Selected SpaceConfig or None if no healthy Space available
        """
        # Check sticky session
        if self.config.sticky_sessions and session_id:
            if session_id in self.sessions:
                space_name, timestamp = self.sessions[session_id]

                # Check if session is still valid
                if (datetime.utcnow() -
                        timestamp).seconds < self.config.session_timeout:
                    space = self.spaces.get(space_name)
                    if space and space.status == SpaceStatus.RUNNING:
                        logger.debug(
                            f"Using sticky session for {session_id} -> {space_name}")
                        return space
                else:
                    # Session expired
                    del self.sessions[session_id]

        # Get healthy Spaces
        healthy_spaces = self.get_healthy_spaces(priority)

        if not healthy_spaces:
            logger.error("No healthy Spaces available!")
            return None

        # Select Space based on load balancing method
        if self.config.method == "round_robin":
            space = self.select_space_round_robin(healthy_spaces)
        elif self.config.method == "least_connections":
            space = self.select_space_least_connections(healthy_spaces)
        elif self.config.method == "weighted":
            space = self.select_space_weighted(healthy_spaces)
        else:
            space = healthy_spaces[0]

        # Store session if sticky sessions enabled
        if self.config.sticky_sessions and session_id and space:
            self.sessions[session_id] = (space.name, datetime.utcnow())

        return space

    def execute_request(self, endpoint: str, method: str = "GET",
                        data: Optional[Dict] = None, session_id: Optional[str] = None,
                        priority: Optional[SpacePriority] = None) -> Optional[requests.Response]:
        """
        Execute a request with automatic failover

        Args:
            endpoint: API endpoint path
            method: HTTP method
            data: Request data
            session_id: Optional session ID
            priority: Optional priority filter

        Returns:
            Response object or None if all attempts failed
        """
        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            space = self.get_space_for_request(session_id, priority)

            if not space:
                logger.error("No Space available for request")
                return None

            try:
                space.total_requests += 1

                url = f"{space.url}{endpoint}"
                headers = {"Authorization": f"Bearer {space.token}"}

                if method == "GET":
                    response = requests.get(
                        url, headers=headers, timeout=space.timeout_seconds)
                elif method == "POST":
                    response = requests.post(
                        url, json=data, headers=headers, timeout=space.timeout_seconds)
                elif method == "PUT":
                    response = requests.put(
                        url, json=data, headers=headers, timeout=space.timeout_seconds)
                elif method == "DELETE":
                    response = requests.delete(
                        url, headers=headers, timeout=space.timeout_seconds)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                space.successful_requests += 1

                logger.info(
                    f"Request successful via {space.name}: {method} {endpoint}")
                return response

            except Exception as e:
                space.failed_requests += 1
                space.last_error = str(e)

                logger.warning(f"Request failed via {space.name}: {str(e)}")

                if self.config.failover_enabled:
                    attempts += 1
                    logger.info(
                        f"Attempting failover (attempt {attempts}/{max_attempts})")
                    time.sleep(1)  # Brief delay before retry
                else:
                    return None

        logger.error(
            f"All failover attempts exhausted for {method} {endpoint}")
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all Spaces"""
        stats = {
            "total_spaces": len(self.spaces),
            "healthy_spaces": len(self.get_healthy_spaces()),
            "spaces": {}
        }

        for name, space in self.spaces.items():
            success_rate = (
                space.successful_requests /
                space.total_requests *
                100) if space.total_requests > 0 else 0

            stats["spaces"][name] = {
                "account": space.account,
                "status": space.status.value,
                "priority": space.priority.name,
                "total_requests": space.total_requests,
                "successful_requests": space.successful_requests,
                "failed_requests": space.failed_requests,
                "success_rate": f"{success_rate:.2f}%",
                "average_response_time": f"{space.average_response_time:.3f}s",
                "consecutive_failures": space.consecutive_failures,
                "last_health_check": space.last_health_check.isoformat() if space.last_health_check else None,
                "last_error": space.last_error}

        return stats

    def print_statistics(self) -> None:
        """Print formatted statistics"""
        stats = self.get_statistics()

        print("\n" + "=" * 80)
        print("MULTI-SPACE MANAGER STATISTICS")
        print("=" * 80)
        print(f"Total Spaces: {stats['total_spaces']}")
        print(f"Healthy Spaces: {stats['healthy_spaces']}")
        print("\nSpace Details:")
        print("-" * 80)

        for name, space_stats in stats["spaces"].items():
            print(f"\n{name} ({space_stats['account']})")
            print(f"  Status: {space_stats['status']}")
            print(f"  Priority: {space_stats['priority']}")
            print(f"  Requests: {space_stats['total_requests']} total, "
                  f"{space_stats['successful_requests']} success, "
                  f"{space_stats['failed_requests']} failed")
            print(f"  Success Rate: {space_stats['success_rate']}")
            print(
                f"  Avg Response Time: {space_stats['average_response_time']}")
            if space_stats['last_error']:
                print(f"  Last Error: {space_stats['last_error']}")

        print("=" * 80 + "\n")


# Global instance
_manager_instance: Optional[MultiSpaceManager] = None


def get_manager() -> MultiSpaceManager:
    """Get or create global MultiSpaceManager instance"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiSpaceManager()
    return _manager_instance


def initialize_from_env() -> MultiSpaceManager:
    """Initialize manager from environment variables"""
    manager = get_manager()

    # Register main Space (currently running)
    main_space = SpaceConfig(
        name="popcorn-main",
        account="ToolKit-backend",
        token=os.getenv("HF_TOKEN", ""),
        url="https://toolkit-backend-popcorn.hf.space",
        purpose="Main API & Frontend",
        services=["API", "Frontend", "WebSocket"],
        priority=SpacePriority.CRITICAL
    )
    manager.register_space(main_space)

    logger.info("MultiSpaceManager initialized from environment")
    return manager


if __name__ == "__main__":
    # Test the manager
    logging.basicConfig(level=logging.INFO)

    manager = initialize_from_env()
    manager.print_statistics()

# Made with Bob
