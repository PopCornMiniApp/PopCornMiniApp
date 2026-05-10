"""
Multi-Account Manager for HuggingFace
Manages multiple HF accounts for load balancing and failover
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AccountStatus(Enum):
    """Account status enumeration"""
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class HFAccount:
    """HuggingFace account configuration"""
    name: str
    token: str
    username: str
    priority: int = 1
    status: AccountStatus = AccountStatus.ACTIVE
    last_used: Optional[datetime] = None
    error_count: int = 0
    rate_limit_until: Optional[datetime] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0


class MultiAccountManager:
    """
    Manages multiple HuggingFace accounts for load balancing

    Features:
    - Automatic failover
    - Load balancing
    - Rate limit handling
    - Health monitoring
    - Usage statistics
    """

    def __init__(self):
        """Initialize multi-account manager"""
        self.accounts: List[HFAccount] = []
        self.current_account_index = 0
        self._load_accounts()

        logger.info(
            f"MultiAccountManager initialized with {len(self.accounts)} accounts")

    def _load_accounts(self):
        """Load accounts from environment variables"""
        # Primary account
        primary_token = os.getenv('HF_TOKEN')
        primary_username = os.getenv('HF_USERNAME', 'ToolKit-backend')

        if primary_token:
            self.accounts.append(HFAccount(
                name="primary",
                token=primary_token,
                username=primary_username,
                priority=1
            ))
            logger.info(f"Loaded primary account: {primary_username}")

        # Secondary account
        secondary_token = os.getenv('HF_TOKEN_2')
        secondary_username = os.getenv('HF_USERNAME_2', 'rayig')

        if secondary_token:
            self.accounts.append(HFAccount(
                name="secondary",
                token=secondary_token,
                username=secondary_username,
                priority=2
            ))
            logger.info(f"Loaded secondary account: {secondary_username}")

        # Additional accounts (HF_TOKEN_3, HF_TOKEN_4, etc.)
        for i in range(3, 11):  # Support up to 10 accounts
            token = os.getenv(f'HF_TOKEN_{i}')
            username = os.getenv(f'HF_USERNAME_{i}')

            if token:
                self.accounts.append(HFAccount(
                    name=f"account_{i}",
                    token=token,
                    username=username or f"account_{i}",
                    priority=i
                ))
                logger.info(
                    f"Loaded account {i}: {username or f'account_{i}'}")

        if not self.accounts:
            logger.warning("No HuggingFace accounts configured!")

    def get_active_account(self) -> Optional[HFAccount]:
        """
        Get the next active account using round-robin with priority

        Returns:
            HFAccount or None if no accounts available
        """
        if not self.accounts:
            logger.error("No accounts available")
            return None

        # Filter active accounts
        active_accounts = [
            acc for acc in self.accounts if acc.status == AccountStatus.ACTIVE and (
                acc.rate_limit_until is None or acc.rate_limit_until < datetime.utcnow())]

        if not active_accounts:
            logger.warning(
                "No active accounts available, trying to recover...")
            self._try_recover_accounts()
            active_accounts = [
                acc for acc in self.accounts
                if acc.status == AccountStatus.ACTIVE
            ]

        if not active_accounts:
            logger.error("All accounts are unavailable")
            return None

        # Sort by priority and last used time
        active_accounts.sort(
            key=lambda x: (
                x.priority,
                x.last_used or datetime.min))

        # Get the account with highest priority and least recent use
        account = active_accounts[0]
        account.last_used = datetime.utcnow()
        account.total_requests += 1

        logger.debug(f"Selected account: {account.name} ({account.username})")
        return account

    def mark_success(self, account: HFAccount):
        """Mark an operation as successful"""
        account.successful_requests += 1
        account.error_count = max(
            0, account.error_count - 1)  # Reduce error count

        if account.status == AccountStatus.ERROR and account.error_count == 0:
            account.status = AccountStatus.ACTIVE
            logger.info(f"Account {account.name} recovered to ACTIVE status")

    def mark_failure(self, account: HFAccount, error: Exception):
        """Mark an operation as failed"""
        account.failed_requests += 1
        account.error_count += 1

        error_str = str(error).lower()

        # Check for rate limiting
        if 'rate limit' in error_str or '429' in error_str:
            account.status = AccountStatus.RATE_LIMITED
            account.rate_limit_until = datetime.utcnow() + timedelta(minutes=15)
            logger.warning(
                f"Account {account.name} rate limited until {account.rate_limit_until}")

        # Check for authentication errors
        elif 'auth' in error_str or '401' in error_str or '403' in error_str:
            account.status = AccountStatus.ERROR
            logger.error(f"Account {account.name} has authentication error")

        # Too many errors
        elif account.error_count >= 5:
            account.status = AccountStatus.ERROR
            logger.error(
                f"Account {account.name} disabled due to too many errors ({account.error_count})")

    def _try_recover_accounts(self):
        """Try to recover accounts from error state"""
        for account in self.accounts:
            # Recover from rate limiting
            if account.status == AccountStatus.RATE_LIMITED:
                if account.rate_limit_until and account.rate_limit_until < datetime.utcnow():
                    account.status = AccountStatus.ACTIVE
                    account.rate_limit_until = None
                    logger.info(
                        f"Account {account.name} recovered from rate limiting")

            # Try to recover from errors if enough time has passed
            elif account.status == AccountStatus.ERROR:
                if account.last_used and (
                        datetime.utcnow() -
                        account.last_used) > timedelta(
                        minutes=30):
                    account.error_count = max(0, account.error_count - 2)
                    if account.error_count < 3:
                        account.status = AccountStatus.ACTIVE
                        logger.info(
                            f"Account {account.name} recovered from error state")

    def get_account_by_name(self, name: str) -> Optional[HFAccount]:
        """Get account by name"""
        for account in self.accounts:
            if account.name == name:
                return account
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics for all accounts"""
        stats = {
            'total_accounts': len(
                self.accounts),
            'active_accounts': sum(
                1 for acc in self.accounts if acc.status == AccountStatus.ACTIVE),
            'accounts': []}

        for account in self.accounts:
            success_rate = 0
            if account.total_requests > 0:
                success_rate = (account.successful_requests /
                                account.total_requests) * 100

            stats['accounts'].append({
                'name': account.name,
                'username': account.username,
                'status': account.status.value,
                'priority': account.priority,
                'total_requests': account.total_requests,
                'successful_requests': account.successful_requests,
                'failed_requests': account.failed_requests,
                'success_rate': round(success_rate, 2),
                'error_count': account.error_count,
                'last_used': account.last_used.isoformat() if account.last_used else None,
                'rate_limited_until': account.rate_limit_until.isoformat() if account.rate_limit_until else None
            })

        return stats

    def reset_statistics(self):
        """Reset usage statistics for all accounts"""
        for account in self.accounts:
            account.total_requests = 0
            account.successful_requests = 0
            account.failed_requests = 0
            account.error_count = 0

        logger.info("Statistics reset for all accounts")

    def disable_account(self, name: str):
        """Manually disable an account"""
        account = self.get_account_by_name(name)
        if account:
            account.status = AccountStatus.DISABLED
            logger.info(f"Account {name} manually disabled")

    def enable_account(self, name: str):
        """Manually enable an account"""
        account = self.get_account_by_name(name)
        if account:
            account.status = AccountStatus.ACTIVE
            account.error_count = 0
            account.rate_limit_until = None
            logger.info(f"Account {name} manually enabled")


# Global instance
_manager: Optional[MultiAccountManager] = None


def get_manager() -> MultiAccountManager:
    """Get or create the global multi-account manager"""
    global _manager
    if _manager is None:
        _manager = MultiAccountManager()
    return _manager


def get_active_token() -> Optional[str]:
    """Get token from an active account"""
    manager = get_manager()
    account = manager.get_active_account()
    return account.token if account else None


def execute_with_failover(operation, *args, **kwargs) -> Any:
    """
    Execute an operation with automatic failover

    Args:
        operation: Function to execute
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation

    Raises:
        Exception if all accounts fail
    """
    manager = get_manager()
    last_error = None

    # Try with each available account
    for attempt in range(len(manager.accounts)):
        account = manager.get_active_account()

        if not account:
            break

        try:
            # Execute operation with this account's token
            kwargs['token'] = account.token
            result = operation(*args, **kwargs)

            # Mark success
            manager.mark_success(account)
            return result

        except Exception as e:
            last_error = e
            manager.mark_failure(account, e)
            logger.warning(
                f"Operation failed with account {account.name}: {str(e)}")

            # If it's not a rate limit or auth error, don't retry
            error_str = str(e).lower()
            if 'rate limit' not in error_str and '429' not in error_str:
                if 'auth' not in error_str and '401' not in error_str and '403' not in error_str:
                    raise

    # All accounts failed
    if last_error:
        raise last_error
    else:
        raise Exception("No accounts available")


# Made with ❤️ by Bob

# Made with Bob
