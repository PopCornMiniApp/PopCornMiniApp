"""
Permissions System for PopCorn Bot
Handles admin verification, role-based access control, and permission checking.
"""
import logging
import functools
from typing import Callable, List
from telegram import Update
from telegram.ext import ContextTypes

from app.config import ADMIN_ID, ADMIN_USERNAME
from app import database as db

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Admin List Management
# ══════════════════════════════════════════════════════════════════════════════

# Primary admin (from config)
PRIMARY_ADMIN_ID = ADMIN_ID
PRIMARY_ADMIN_USERNAME = ADMIN_USERNAME

# Additional admins can be added here
ADMIN_IDS = [PRIMARY_ADMIN_ID]
ADMIN_USERNAMES = [PRIMARY_ADMIN_USERNAME]

# Super admins have full access to all features
SUPER_ADMIN_IDS = [PRIMARY_ADMIN_ID]

# Moderators have limited admin access
MODERATOR_IDS = []


def add_admin(user_id: int, username: str = None) -> bool:
    """Add a new admin to the system."""
    try:
        if user_id not in ADMIN_IDS:
            ADMIN_IDS.append(user_id)
            if username and username not in ADMIN_USERNAMES:
                ADMIN_USERNAMES.append(username)
            logger.info(f"✅ Added admin: {user_id} ({username})")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error adding admin: {e}")
        return False


def remove_admin(user_id: int) -> bool:
    """Remove an admin from the system (except primary admin)."""
    try:
        if user_id == PRIMARY_ADMIN_ID:
            logger.warning("⚠️ Cannot remove primary admin")
            return False

        if user_id in ADMIN_IDS:
            ADMIN_IDS.remove(user_id)
            logger.info(f"✅ Removed admin: {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error removing admin: {e}")
        return False


def add_moderator(user_id: int) -> bool:
    """Add a moderator to the system."""
    try:
        if user_id not in MODERATOR_IDS:
            MODERATOR_IDS.append(user_id)
            logger.info(f"✅ Added moderator: {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error adding moderator: {e}")
        return False


def remove_moderator(user_id: int) -> bool:
    """Remove a moderator from the system."""
    try:
        if user_id in MODERATOR_IDS:
            MODERATOR_IDS.remove(user_id)
            logger.info(f"✅ Removed moderator: {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Error removing moderator: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# Permission Checking Functions
# ══════════════════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_IDS


def is_super_admin(user_id: int) -> bool:
    """Check if user is a super admin."""
    return user_id in SUPER_ADMIN_IDS


def is_moderator(user_id: int) -> bool:
    """Check if user is a moderator."""
    return user_id in MODERATOR_IDS


def has_admin_access(user_id: int) -> bool:
    """Check if user has any admin access (admin or moderator)."""
    return is_admin(user_id) or is_moderator(user_id)


def get_user_role(user_id: int) -> str:
    """Get the role of a user."""
    if is_super_admin(user_id):
        return "super_admin"
    elif is_admin(user_id):
        return "admin"
    elif is_moderator(user_id):
        return "moderator"
    else:
        return "user"


def get_admin_list() -> List[dict]:
    """Get list of all admins with their roles."""
    admins = []
    for admin_id in ADMIN_IDS:
        role = get_user_role(admin_id)
        username = None
        if admin_id == PRIMARY_ADMIN_ID:
            username = PRIMARY_ADMIN_USERNAME
        admins.append({
            "user_id": admin_id,
            "username": username,
            "role": role
        })
    return admins


# ══════════════════════════════════════════════════════════════════════════════
# Permission Decorators
# ══════════════════════════════════════════════════════════════════════════════

def admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict command access to admins only.
    Usage: @admin_only
    """
    @functools.wraps(func)
    async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs):
        user = update.effective_user
        if not user:
            return

        if not is_admin(user.id):
            logger.warning(
                f"⚠️ Unauthorized access attempt by {user.id} ({user.username})")
            await update.message.reply_text(
                "❌ **Access Denied**\n\n"
                "This command is restricted to administrators only.\n"
                f"Your ID: `{user.id}`",
                parse_mode="Markdown"
            )

            # Log unauthorized access attempt
            try:
                db.log_admin_action(
                    admin_id=user.id,
                    action_type="unauthorized_access",
                    action_details=f"Attempted to use admin command: {update.message.text}",
                    status="denied")
            except Exception as e:
                logger.error(f"Error logging unauthorized access: {e}")

            return

        logger.info(f"✅ Admin access granted to {user.id} ({user.username})")
        return await func(update, context, *args, **kwargs)

    return wrapper


def super_admin_only(func: Callable) -> Callable:
    """
    Decorator to restrict command access to super admins only.
    Usage: @super_admin_only
    """
    @functools.wraps(func)
    async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs):
        user = update.effective_user
        if not user:
            return

        if not is_super_admin(user.id):
            logger.warning(
                f"⚠️ Unauthorized super admin access attempt by {user.id} ({user.username})")
            await update.message.reply_text(
                "❌ **Access Denied**\n\n"
                "This command is restricted to super administrators only.\n"
                f"Your ID: `{user.id}`\n"
                f"Your Role: `{get_user_role(user.id)}`",
                parse_mode="Markdown"
            )

            # Log unauthorized access attempt
            try:
                db.log_admin_action(
                    admin_id=user.id,
                    action_type="unauthorized_super_admin_access",
                    action_details=f"Attempted to use super admin command: {update.message.text}",
                    status="denied")
            except Exception as e:
                logger.error(f"Error logging unauthorized access: {e}")

            return

        logger.info(
            f"✅ Super admin access granted to {user.id} ({user.username})")
        return await func(update, context, *args, **kwargs)

    return wrapper


def moderator_or_admin(func: Callable) -> Callable:
    """
    Decorator to restrict command access to moderators and admins.
    Usage: @moderator_or_admin
    """
    @functools.wraps(func)
    async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs):
        user = update.effective_user
        if not user:
            return

        if not has_admin_access(user.id):
            logger.warning(
                f"⚠️ Unauthorized access attempt by {user.id} ({user.username})")
            await update.message.reply_text(
                "❌ **Access Denied**\n\n"
                "This command is restricted to moderators and administrators.\n"
                f"Your ID: `{user.id}`",
                parse_mode="Markdown"
            )

            # Log unauthorized access attempt
            try:
                db.log_admin_action(
                    admin_id=user.id,
                    action_type="unauthorized_moderator_access",
                    action_details=f"Attempted to use moderator command: {update.message.text}",
                    status="denied")
            except Exception as e:
                logger.error(f"Error logging unauthorized access: {e}")

            return

        logger.info(
            f"✅ Moderator/Admin access granted to {user.id} ({user.username})")
        return await func(update, context, *args, **kwargs)

    return wrapper


def require_permission(permission: str) -> Callable:
    """
    Decorator to require specific permission.
    Usage: @require_permission("manage_users")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(
                update: Update,
                context: ContextTypes.DEFAULT_TYPE,
                *args,
                **kwargs):
            user = update.effective_user
            if not user:
                return

            # Check if user has the required permission
            if not check_permission(user.id, permission):
                logger.warning(
                    f"⚠️ Permission denied for {user.id} ({user.username}): {permission}")
                await update.message.reply_text(
                    "❌ **Permission Denied**\n\n"
                    f"You don't have the required permission: `{permission}`\n"
                    f"Your Role: `{get_user_role(user.id)}`",
                    parse_mode="Markdown"
                )

                # Log permission denial
                try:
                    db.log_admin_action(
                        admin_id=user.id,
                        action_type="permission_denied",
                        action_details=f"Required permission: {permission}, Command: {update.message.text}",
                        status="denied")
                except Exception as e:
                    logger.error(f"Error logging permission denial: {e}")

                return

            logger.info(
                f"✅ Permission granted to {user.id} ({user.username}): {permission}")
            return await func(update, context, *args, **kwargs)

        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# Permission System
# ══════════════════════════════════════════════════════════════════════════════

# Define available permissions
PERMISSIONS = {
    # User Management
    "view_users": ["super_admin", "admin", "moderator"],
    "manage_users": ["super_admin", "admin"],
    "block_users": ["super_admin", "admin", "moderator"],
    "delete_users": ["super_admin"],

    # Content Management
    "view_content": ["super_admin", "admin", "moderator"],
    "manage_content": ["super_admin", "admin"],
    "delete_content": ["super_admin", "admin"],

    # Sync Management
    "view_sync_status": ["super_admin", "admin", "moderator"],
    "trigger_sync": ["super_admin", "admin"],
    "manage_sync": ["super_admin"],

    # Reports & Analytics
    "view_reports": ["super_admin", "admin", "moderator"],
    "generate_reports": ["super_admin", "admin"],
    "export_data": ["super_admin"],

    # System Management
    "view_system_status": ["super_admin", "admin", "moderator"],
    "manage_system": ["super_admin", "admin"],
    "manage_admins": ["super_admin"],

    # Database Operations
    "view_database": ["super_admin", "admin"],
    "backup_database": ["super_admin", "admin"],
    "restore_database": ["super_admin"],

    # Notifications
    "send_notifications": ["super_admin", "admin"],
    "manage_notifications": ["super_admin", "admin"],
}


def check_permission(user_id: int, permission: str) -> bool:
    """Check if user has a specific permission."""
    role = get_user_role(user_id)

    if permission not in PERMISSIONS:
        logger.warning(f"⚠️ Unknown permission: {permission}")
        return False

    allowed_roles = PERMISSIONS[permission]
    return role in allowed_roles


def get_user_permissions(user_id: int) -> List[str]:
    """Get all permissions for a user."""
    role = get_user_role(user_id)
    permissions = []

    for permission, allowed_roles in PERMISSIONS.items():
        if role in allowed_roles:
            permissions.append(permission)

    return permissions


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

async def log_admin_action_wrapper(
    user_id: int,
    action_type: str,
    action_details: str = None,
    target_type: str = None,
    target_id: str = None,
    status: str = "success"
):
    """Wrapper function to log admin actions with error handling."""
    try:
        db.log_admin_action(
            admin_id=user_id,
            action_type=action_type,
            action_details=action_details,
            target_type=target_type,
            target_id=target_id,
            status=status
        )
        logger.info(f"📝 Logged admin action: {action_type} by {user_id}")
    except Exception as e:
        logger.error(f"❌ Error logging admin action: {e}")


def format_admin_info(user_id: int) -> str:
    """Format admin information for display."""
    role = get_user_role(user_id)
    permissions = get_user_permissions(user_id)

    info = f"**User ID:** `{user_id}`\n"
    info += f"**Role:** `{role}`\n"
    info += f"**Permissions:** {len(permissions)}\n\n"
    info += "**Available Permissions:**\n"

    for perm in permissions[:10]:  # Show first 10 permissions
        info += f"• `{perm}`\n"

    if len(permissions) > 10:
        info += f"• ... and {len(permissions) - 10} more\n"

    return info


def get_permission_description(permission: str) -> str:
    """Get description for a permission."""
    descriptions = {
        "view_users": "View user list and details",
        "manage_users": "Create, update, and manage users",
        "block_users": "Block and unblock users",
        "delete_users": "Permanently delete users",
        "view_content": "View content list and details",
        "manage_content": "Add, update, and manage content",
        "delete_content": "Delete content from system",
        "view_sync_status": "View synchronization status",
        "trigger_sync": "Trigger manual synchronization",
        "manage_sync": "Full sync management and configuration",
        "view_reports": "View system reports and analytics",
        "generate_reports": "Generate custom reports",
        "export_data": "Export system data",
        "view_system_status": "View system health and status",
        "manage_system": "Manage system settings",
        "manage_admins": "Add and remove administrators",
        "view_database": "View database information",
        "backup_database": "Create database backups",
        "restore_database": "Restore database from backup",
        "send_notifications": "Send notifications to users",
        "manage_notifications": "Manage notification system",
    }

    return descriptions.get(permission, "No description available")


# ══════════════════════════════════════════════════════════════════════════════
# Initialization
# ══════════════════════════════════════════════════════════════════════════════

def initialize_permissions():
    """Initialize the permissions system."""
    logger.info("🔐 Initializing permissions system...")
    logger.info(
        f"✅ Primary Admin: {PRIMARY_ADMIN_ID} ({PRIMARY_ADMIN_USERNAME})")
    logger.info(f"✅ Total Admins: {len(ADMIN_IDS)}")
    logger.info(f"✅ Total Moderators: {len(MODERATOR_IDS)}")
    logger.info(f"✅ Total Permissions: {len(PERMISSIONS)}")
    logger.info("🔐 Permissions system initialized successfully!")


# Initialize on module load
initialize_permissions()

# Made with Bob
