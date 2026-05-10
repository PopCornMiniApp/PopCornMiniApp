"""
PopCorn Admin Permission System
Multi-level admin permission system with role-based access control.
"""
import logging
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Admin Role Definitions
# ══════════════════════════════════════════════════════════════════════════════

class AdminRole(Enum):
    """Admin role levels with hierarchical permissions."""
    SUPER_ADMIN = "super_admin"  # المشرف الأعلى - Full system access
    ADMIN = "admin"              # المشرف - Content & user management
    MODERATOR = "moderator"      # المراقب - Limited moderation access


# ══════════════════════════════════════════════════════════════════════════════
# Permission Definitions
# ══════════════════════════════════════════════════════════════════════════════

class Permission(Enum):
    """Granular permission definitions."""
    # User Management
    VIEW_USERS = "view_users"
    VIEW_USER_DETAILS = "view_user_details"
    BLOCK_USERS = "block_users"
    UNBLOCK_USERS = "unblock_users"
    DELETE_USERS = "delete_users"
    UPGRADE_USERS = "upgrade_users"

    # Content Management
    VIEW_CONTENT = "view_content"
    ADD_CONTENT = "add_content"
    EDIT_CONTENT = "edit_content"
    DELETE_CONTENT = "delete_content"

    # Sync Operations
    TRIGGER_SYNC = "trigger_sync"
    VIEW_SYNC_STATUS = "view_sync_status"

    # Analytics & Reports
    VIEW_ANALYTICS = "view_analytics"
    VIEW_BASIC_ANALYTICS = "view_basic_analytics"
    GENERATE_REPORTS = "generate_reports"
    EXPORT_DATA = "export_data"

    # System Operations
    VIEW_LOGS = "view_logs"
    VIEW_ALL_LOGS = "view_all_logs"
    SYSTEM_SETTINGS = "system_settings"
    DATABASE_OPERATIONS = "database_operations"

    # Admin Management
    MANAGE_ADMINS = "manage_admins"
    MANAGE_MODERATORS = "manage_moderators"

    # Bulk Operations
    BULK_OPERATIONS = "bulk_operations"

    # Notifications
    SEND_NOTIFICATIONS = "send_notifications"


# ══════════════════════════════════════════════════════════════════════════════
# Role Permission Mapping
# ══════════════════════════════════════════════════════════════════════════════

ROLE_PERMISSIONS: Dict[AdminRole, List[Permission]] = {
    AdminRole.SUPER_ADMIN: [
        # All permissions
        Permission.VIEW_USERS,
        Permission.VIEW_USER_DETAILS,
        Permission.BLOCK_USERS,
        Permission.UNBLOCK_USERS,
        Permission.DELETE_USERS,
        Permission.UPGRADE_USERS,
        Permission.VIEW_CONTENT,
        Permission.ADD_CONTENT,
        Permission.EDIT_CONTENT,
        Permission.DELETE_CONTENT,
        Permission.TRIGGER_SYNC,
        Permission.VIEW_SYNC_STATUS,
        Permission.VIEW_ANALYTICS,
        Permission.GENERATE_REPORTS,
        Permission.EXPORT_DATA,
        Permission.VIEW_LOGS,
        Permission.VIEW_ALL_LOGS,
        Permission.SYSTEM_SETTINGS,
        Permission.DATABASE_OPERATIONS,
        Permission.MANAGE_ADMINS,
        Permission.MANAGE_MODERATORS,
        Permission.BULK_OPERATIONS,
        Permission.SEND_NOTIFICATIONS,
    ],

    AdminRole.ADMIN: [
        # User management
        Permission.VIEW_USERS,
        Permission.VIEW_USER_DETAILS,
        Permission.BLOCK_USERS,
        Permission.UNBLOCK_USERS,
        Permission.DELETE_USERS,
        Permission.UPGRADE_USERS,
        # Content management
        Permission.VIEW_CONTENT,
        Permission.ADD_CONTENT,
        Permission.EDIT_CONTENT,
        Permission.DELETE_CONTENT,
        # Sync operations
        Permission.TRIGGER_SYNC,
        Permission.VIEW_SYNC_STATUS,
        # Analytics
        Permission.VIEW_ANALYTICS,
        Permission.GENERATE_REPORTS,
        Permission.EXPORT_DATA,
        # Logs
        Permission.VIEW_LOGS,
        # Bulk operations
        Permission.BULK_OPERATIONS,
        # Notifications
        Permission.SEND_NOTIFICATIONS,
    ],

    AdminRole.MODERATOR: [
        # Limited user management
        Permission.VIEW_USERS,
        Permission.BLOCK_USERS,
        Permission.UNBLOCK_USERS,
        # Limited content management
        Permission.VIEW_CONTENT,
        Permission.EDIT_CONTENT,
        # Basic analytics
        Permission.VIEW_BASIC_ANALYTICS,
        # Limited logs
        Permission.VIEW_LOGS,
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# Admin Permission Manager
# ══════════════════════════════════════════════════════════════════════════════

class AdminPermissionManager:
    """Manages admin permissions and role-based access control."""

    def __init__(self, db_connection_pool):
        """
        Initialize the permission manager.

        Args:
            db_connection_pool: Database connection pool instance
        """
        self.db_pool = db_connection_pool
        self._init_admin_table()

    def _init_admin_table(self):
        """Initialize admin_users table if it doesn't exist."""
        try:
            with self.db_pool.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS admin_users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        role TEXT NOT NULL,
                        assigned_by INTEGER,
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        permissions_override TEXT,
                        last_activity TIMESTAMP,
                        notes TEXT,
                        FOREIGN KEY (assigned_by) REFERENCES admin_users(user_id)
                    )
                """)

                # Create indexes for performance
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_admin_role
                    ON admin_users(role)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_admin_active
                    ON admin_users(is_active)
                """)

                logger.info("✅ Admin users table initialized")
        except Exception as e:
            logger.error(f"Error initializing admin table: {e}", exc_info=True)

    def is_admin(self, user_id: int) -> bool:
        """
        Check if user has any admin role.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user is an admin, False otherwise
        """
        try:
            with self.db_pool.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT role FROM admin_users WHERE user_id = ? AND is_active = 1", (user_id,))
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(
                f"Error checking admin status for user {user_id}: {e}")
            return False

    def get_admin_role(self, user_id: int) -> Optional[AdminRole]:
        """
        Get the admin role for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            AdminRole if user is admin, None otherwise
        """
        try:
            with self.db_pool.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT role FROM admin_users WHERE user_id = ? AND is_active = 1", (user_id,))
                result = cursor.fetchone()

                if result:
                    role_str = result[0]
                    return AdminRole(role_str)
                return None
        except Exception as e:
            logger.error(f"Error getting admin role for user {user_id}: {e}")
            return None

    def has_permission(self, user_id: int, permission: Permission) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user_id: Telegram user ID
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise
        """
        role = self.get_admin_role(user_id)
        if not role:
            return False

        # Check if role has this permission
        role_perms = ROLE_PERMISSIONS.get(role, [])
        return permission in role_perms

    def has_any_permission(
            self,
            user_id: int,
            permissions: List[Permission]) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            user_id: Telegram user ID
            permissions: List of permissions to check

        Returns:
            True if user has at least one permission, False otherwise
        """
        return any(self.has_permission(user_id, perm) for perm in permissions)

    def has_all_permissions(
            self,
            user_id: int,
            permissions: List[Permission]) -> bool:
        """
        Check if user has all of the specified permissions.

        Args:
            user_id: Telegram user ID
            permissions: List of permissions to check

        Returns:
            True if user has all permissions, False otherwise
        """
        return all(self.has_permission(user_id, perm) for perm in permissions)

    def add_admin(
        self,
        user_id: int,
        role: AdminRole,
        assigned_by: int,
        username: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add a new admin user.

        Args:
            user_id: Telegram user ID to make admin
            role: Admin role to assign
            assigned_by: User ID of the admin assigning this role
            username: Optional username
            notes: Optional notes about this admin

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if assigner has permission
            if not self.has_permission(assigned_by, Permission.MANAGE_ADMINS):
                if role == AdminRole.MODERATOR:
                    # Admins can add moderators
                    if not self.has_permission(
                            assigned_by, Permission.MANAGE_MODERATORS):
                        logger.warning(
                            f"User {assigned_by} lacks permission to add admin")
                        return False
                else:
                    logger.warning(
                        f"User {assigned_by} lacks permission to add admin")
                    return False

            with self.db_pool.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO admin_users
                    (user_id, username, role, assigned_by, assigned_at, is_active, notes)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (user_id, username, role.value, assigned_by, datetime.now(), notes))

                logger.info(
                    f"✅ Added admin: user_id={user_id}, role={role.value}, assigned_by={assigned_by}")
                return True
        except Exception as e:
            logger.error(f"Error adding admin {user_id}: {e}", exc_info=True)
            return False

    def remove_admin(self, user_id: int, removed_by: int) -> bool:
        """
        Remove admin privileges from a user.

        Args:
            user_id: User ID to remove admin from
            removed_by: User ID performing the removal

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if remover has permission
            if not self.has_permission(removed_by, Permission.MANAGE_ADMINS):
                logger.warning(
                    f"User {removed_by} lacks permission to remove admin")
                return False

            # Check if target is super admin (cannot be removed)
            target_role = self.get_admin_role(user_id)
            if target_role == AdminRole.SUPER_ADMIN:
                logger.warning(f"Cannot remove super admin {user_id}")
                return False

            with self.db_pool.get_connection() as conn:
                conn.execute(
                    "UPDATE admin_users SET is_active = 0 WHERE user_id = ?",
                    (user_id,)
                )

                logger.info(
                    f"✅ Removed admin: user_id={user_id}, removed_by={removed_by}")
                return True
        except Exception as e:
            logger.error(f"Error removing admin {user_id}: {e}", exc_info=True)
            return False

    def get_all_admins(
            self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of all admin users.

        Args:
            include_inactive: Whether to include inactive admins

        Returns:
            List of admin user dictionaries
        """
        try:
            with self.db_pool.get_connection() as conn:
                query = "SELECT * FROM admin_users"
                if not include_inactive:
                    query += " WHERE is_active = 1"
                query += " ORDER BY role, assigned_at"

                cursor = conn.execute(query)
                rows = cursor.fetchall()

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting admin list: {e}")
            return []

    def update_last_activity(self, user_id: int):
        """
        Update the last activity timestamp for an admin.

        Args:
            user_id: Admin user ID
        """
        try:
            with self.db_pool.get_connection() as conn:
                conn.execute(
                    "UPDATE admin_users SET last_activity = ? WHERE user_id = ?",
                    (datetime.now(), user_id)
                )
        except Exception as e:
            logger.error(
                f"Error updating last activity for admin {user_id}: {e}")

    def get_admin_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an admin.

        Args:
            user_id: Admin user ID

        Returns:
            Dictionary with admin information or None
        """
        try:
            with self.db_pool.get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM admin_users WHERE user_id = ?",
                    (user_id,)
                )
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error getting admin info for {user_id}: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# Decorator for Permission Checking
# ══════════════════════════════════════════════════════════════════════════════

def require_permission(permission: Permission):
    """
    Decorator to check if user has required permission before executing function.

    Usage:
        @require_permission(Permission.DELETE_USERS)
        async def delete_user_handler(update, context):
            ...
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            user = update.effective_user

            # Get permission manager from context
            perm_manager = context.bot_data.get('permission_manager')
            if not perm_manager:
                logger.error("Permission manager not found in bot_data")
                await update.effective_message.reply_text(
                    "❌ خطأ في النظام / System error"
                )
                return

            # Check permission
            if not perm_manager.has_permission(user.id, permission):
                logger.warning(
                    f"User {user.id} lacks permission: {permission.value}")
                await update.effective_message.reply_text(
                    "❌ ليس لديك صلاحية لهذا الإجراء\n"
                    "You don't have permission for this action"
                )
                return

            # Update last activity
            perm_manager.update_last_activity(user.id)

            # Execute function
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


def require_admin(func):
    """
    Decorator to check if user is an admin before executing function.

    Usage:
        @require_admin
        async def admin_panel_handler(update, context):
            ...
    """
    from functools import wraps

    def wrapper(func):
        @wraps(func)
        async def inner(update, context, *args, **kwargs):
            user = update.effective_user

            # Get permission manager from context
            perm_manager = context.bot_data.get('permission_manager')
            if not perm_manager:
                logger.error("Permission manager not found in bot_data")
                await update.effective_message.reply_text(
                    "❌ خطأ في النظام / System error"
                )
                return

            # Check if admin
            if not perm_manager.is_admin(user.id):
                logger.warning(
                    f"Non-admin user {user.id} attempted admin action")
                await update.effective_message.reply_text(
                    "❌ هذا الأمر للمشرفين فقط\n"
                    "This command is for admins only"
                )
                return

            # Update last activity
            perm_manager.update_last_activity(user.id)

            # Execute function
            return await func(update, context, *args, **kwargs)

        return inner
    return wrapper(func)


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_role_display_name(role: AdminRole, language: str = "ar") -> str:
    """
    Get display name for admin role.

    Args:
        role: AdminRole enum
        language: Language code ('ar' or 'en')

    Returns:
        Localized role name
    """
    role_names = {
        AdminRole.SUPER_ADMIN: {
            "ar": "المشرف الأعلى",
            "en": "Super Admin"
        },
        AdminRole.ADMIN: {
            "ar": "المشرف",
            "en": "Admin"
        },
        AdminRole.MODERATOR: {
            "ar": "المراقب",
            "en": "Moderator"
        }
    }

    return role_names.get(role, {}).get(language, role.value)


def get_permission_display_name(
        permission: Permission,
        language: str = "ar") -> str:
    """
    Get display name for permission.

    Args:
        permission: Permission enum
        language: Language code ('ar' or 'en')

    Returns:
        Localized permission name
    """
    # This can be expanded with full translations
    return permission.value.replace("_", " ").title()


# Made with Bob
