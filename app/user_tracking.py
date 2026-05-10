"""
User Tracking System
Automatic tracking of user activities, sessions, and behavior patterns
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
from user_agents import parse

from app import database as db

logger = logging.getLogger(__name__)


class UserTracker:
    """Comprehensive user tracking system"""

    @staticmethod
    def extract_request_info(request: Request) -> Dict[str, Any]:
        """Extract detailed information from request"""
        user_agent_string = request.headers.get("user-agent", "")
        user_agent = parse(user_agent_string)

        # Extract IP address (handle proxies)
        ip_address = request.headers.get("x-forwarded-for")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else "unknown"

        # Device information
        device_type = "mobile" if user_agent.is_mobile else \
            "tablet" if user_agent.is_tablet else \
            "tv" if user_agent.is_tv else "desktop"

        os_type = user_agent.os.family
        browser = user_agent.browser.family

        return {
            "ip_address": ip_address,
            "user_agent": user_agent_string,
            "device_type": device_type,
            "os_type": os_type,
            "browser": browser,
            "os_version": user_agent.os.version_string,
            "browser_version": user_agent.browser.version_string,
        }

    @staticmethod
    def get_or_create_session(
            request: Request,
            user_id: Optional[int] = None) -> str:
        """Get existing session or create new one"""
        # Try to get session from cookie or header
        session_id = request.cookies.get("session_id") or \
            request.headers.get("x-session-id")

        if not session_id:
            # Create new session
            session_id = str(uuid.uuid4())

            if user_id:
                request_info = UserTracker.extract_request_info(request)
                try:
                    db.create_user_session(
                        user_id=user_id,
                        session_id=session_id,
                        **request_info
                    )
                    logger.info(
                        f"Created new session {session_id} for user {user_id}")
                except Exception as e:
                    logger.error(f"Error creating session: {e}")

        return session_id

    @staticmethod
    def track_activity(
        user_id: int,
        activity_type: str,
        request: Request,
        content_type: Optional[str] = None,
        content_id: Optional[str] = None,
        duration: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """Track user activity with full context"""
        try:
            session_id = UserTracker.get_or_create_session(request, user_id)
            request_info = UserTracker.extract_request_info(request)

            activity_details = {
                "endpoint": str(request.url.path),
                "method": request.method,
                "timestamp": datetime.utcnow().isoformat(),
            }

            if metadata:
                activity_details.update(metadata)

            db.log_user_activity(
                user_id=user_id,
                activity_type=activity_type,
                activity_details=activity_details,
                content_type=content_type,
                content_id=content_id,
                session_id=session_id,
                duration=duration,
                metadata=metadata,
                **request_info
            )

            logger.debug(f"Tracked {activity_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error tracking activity: {e}", exc_info=True)

    @staticmethod
    def track_login(user_id: int, request: Request) -> str:
        """Track user login and create session"""
        try:
            session_id = str(uuid.uuid4())
            request_info = UserTracker.extract_request_info(request)

            # Create session
            db.create_user_session(
                user_id=user_id,
                session_id=session_id,
                **request_info
            )

            # Log activity
            db.log_user_activity(
                user_id=user_id,
                activity_type="login",
                session_id=session_id,
                activity_details={"login_time": datetime.utcnow().isoformat()},
                **request_info
            )

            # Update user last_active
            db.create_or_update_user(
                user_id=user_id,
                last_active=datetime.utcnow().isoformat()
            )

            # Update statistics
            db.update_user_statistics(
                user_id=user_id,
                total_logins=db.get_user_statistics(user_id).get(
                    'total_logins',
                    0) + 1)

            logger.info(f"User {user_id} logged in, session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error tracking login: {e}", exc_info=True)
            return str(uuid.uuid4())

    @staticmethod
    def track_logout(user_id: int, session_id: str, request: Request) -> None:
        """Track user logout and end session"""
        try:
            # End session
            db.end_user_session(session_id)

            # Log activity
            request_info = UserTracker.extract_request_info(request)
            db.log_user_activity(
                user_id=user_id,
                activity_type="logout",
                session_id=session_id,
                activity_details={
                    "logout_time": datetime.utcnow().isoformat()},
                **request_info)

            logger.info(f"User {user_id} logged out, session: {session_id}")
        except Exception as e:
            logger.error(f"Error tracking logout: {e}", exc_info=True)

    @staticmethod
    def track_content_view(
        user_id: int,
        content_type: str,
        content_id: str,
        request: Request,
        duration: Optional[int] = None
    ) -> None:
        """Track content viewing"""
        UserTracker.track_activity(
            user_id=user_id,
            activity_type="view_content",
            request=request,
            content_type=content_type,
            content_id=content_id,
            duration=duration,
            metadata={
                "content_type": content_type,
                "content_id": content_id,
                "view_time": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def track_search(
        user_id: int,
        query: str,
        results_count: int,
        request: Request
    ) -> None:
        """Track search activity"""
        UserTracker.track_activity(
            user_id=user_id,
            activity_type="search",
            request=request,
            metadata={
                "query": query,
                "results_count": results_count,
                "search_time": datetime.utcnow().isoformat()
            }
        )

        # Update statistics
        try:
            stats = db.get_user_statistics(user_id)
            db.update_user_statistics(
                user_id=user_id,
                total_searches=stats.get('total_searches', 0) + 1
            )
        except Exception as e:
            logger.error(f"Error updating search statistics: {e}")

    @staticmethod
    def track_rating(
        user_id: int,
        content_type: str,
        content_id: str,
        rating: int,
        request: Request
    ) -> None:
        """Track content rating"""
        UserTracker.track_activity(
            user_id=user_id,
            activity_type="rate",
            request=request,
            content_type=content_type,
            content_id=content_id,
            metadata={
                "rating": rating,
                "rated_at": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def track_favorite(
        user_id: int,
        content_type: str,
        content_id: str,
        action: str,  # 'add' or 'remove'
        request: Request
    ) -> None:
        """Track favorite actions"""
        activity_type = "favorite" if action == "add" else "unfavorite"
        UserTracker.track_activity(
            user_id=user_id,
            activity_type=activity_type,
            request=request,
            content_type=content_type,
            content_id=content_id,
            metadata={
                "action": action,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    @staticmethod
    def track_watch_progress(
        user_id: int,
        content_type: str,
        content_id: str,
        progress_seconds: int,
        total_seconds: int,
        request: Request,
        **kwargs
    ) -> None:
        """Track watch progress"""
        try:
            # Update watch progress in database
            db.update_watch_progress(
                user_id=user_id,
                content_type=content_type,
                content_id=content_id,
                progress_seconds=progress_seconds,
                total_seconds=total_seconds,
                **kwargs
            )

            # Track activity
            UserTracker.track_activity(
                user_id=user_id,
                activity_type="view_content",
                request=request,
                content_type=content_type,
                content_id=content_id,
                duration=progress_seconds,
                metadata={
                    "progress_seconds": progress_seconds,
                    "total_seconds": total_seconds,
                    "progress_percent": (
                        progress_seconds /
                        total_seconds *
                        100) if total_seconds > 0 else 0})

            logger.debug(
                f"Updated watch progress for user {user_id}: {content_id}")
        except Exception as e:
            logger.error(f"Error tracking watch progress: {e}", exc_info=True)

    @staticmethod
    def register_device(
        user_id: int,
        request: Request
    ) -> str:
        """Register or update user device"""
        try:
            request_info = UserTracker.extract_request_info(request)

            # Generate device ID from user agent and IP
            device_string = f"{request_info['user_agent']}_{request_info['ip_address']}"
            device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, device_string))

            db.register_user_device(
                user_id=user_id,
                device_id=device_id,
                device_name=f"{request_info['os_type']} - {request_info['browser']}",
                device_type=request_info['device_type'],
                os_type=request_info['os_type'],
                os_version=request_info.get(
                    'os_version',
                    ''),
                browser=request_info['browser'],
                browser_version=request_info.get(
                    'browser_version',
                    ''))

            logger.debug(f"Registered device {device_id} for user {user_id}")
            return device_id
        except Exception as e:
            logger.error(f"Error registering device: {e}", exc_info=True)
            return ""

    @staticmethod
    def update_session_activity(session_id: str) -> None:
        """Update session last activity timestamp"""
        try:
            db.update_user_session(
                session_id=session_id,
                last_activity=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")

    @staticmethod
    def get_user_context(user_id: int, request: Request) -> Dict[str, Any]:
        """Get comprehensive user context for personalization"""
        try:
            context = {
                "user_id": user_id,
                "profile": db.get_user_profile(user_id),
                "statistics": db.get_user_statistics(user_id),
                "preferences": db.get_user_preferences(user_id),
                "is_premium": db.is_user_premium(user_id),
                "request_info": UserTracker.extract_request_info(request)
            }
            return context
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {"user_id": user_id}


class TrackingMiddleware:
    """Middleware for automatic request tracking"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Track request
            request = Request(scope, receive)

            # Extract user_id from headers or cookies if available
            user_id = request.headers.get("x-user-id")
            if user_id:
                try:
                    user_id = int(user_id)
                    session_id = UserTracker.get_or_create_session(
                        request, user_id)

                    # Update session activity
                    UserTracker.update_session_activity(session_id)

                    # Register device if not already registered
                    UserTracker.register_device(user_id, request)
                except Exception as e:
                    logger.error(f"Error in tracking middleware: {e}")

        await self.app(scope, receive, send)


# Utility functions for easy tracking

def track_page_view(user_id: int, page: str, request: Request) -> None:
    """Track page view"""
    UserTracker.track_activity(
        user_id=user_id,
        activity_type="view_content",
        request=request,
        metadata={
            "page": page,
            "view_time": datetime.utcnow().isoformat()
        }
    )


def track_error(user_id: Optional[int], error_type: str, error_message: str,
                request: Request) -> None:
    """Track application errors"""
    try:
        request_info = UserTracker.extract_request_info(request)

        if user_id:
            db.log_user_activity(
                user_id=user_id,
                activity_type="error",
                activity_details={
                    "error_type": error_type,
                    "error_message": error_message,
                    "endpoint": str(request.url.path)
                },
                **request_info
            )

        # Also log to analytics_errors
        db.log_error(
            error_type=error_type,
            error_message=error_message,
            endpoint=str(request.url.path),
            user_id=user_id,
            ip_address=request_info['ip_address']
        )
    except Exception as e:
        logger.error(f"Error tracking error: {e}")


def get_session_info(session_id: str) -> Optional[Dict]:
    """Get session information"""
    try:
        sessions = db.get_active_sessions()
        for session in sessions:
            if session['session_id'] == session_id:
                return session
        return None
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        return None

# Made with Bob
