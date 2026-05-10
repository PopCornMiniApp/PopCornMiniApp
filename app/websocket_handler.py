"""
Enhanced WebSocket Handler for PopCorn
Provides connection pooling, room management, and error handling
"""

import logging
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Advanced WebSocket connection manager.
    Handles multiple rooms, user connections, and message broadcasting.
    """

    def __init__(self):
        # Room connections: {room_id: {user_id: websocket}}
        self.room_connections: Dict[str,
                                    Dict[int, WebSocket]] = defaultdict(dict)

        # User to rooms mapping: {user_id: {room_id}}
        self.user_rooms: Dict[int, Set[str]] = defaultdict(set)

        # Connection metadata: {websocket: {user_id, room_id, connected_at}}
        self.connection_metadata: Dict[WebSocket, dict] = {}

        # Statistics
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages': 0,
            'total_broadcasts': 0,
            'errors': 0
        }

        logger.info("✅ ConnectionManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        room_id: str,
        user_id: int,
        username: Optional[str] = None
    ) -> bool:
        """
        Connect a user to a room.

        Args:
            websocket: The WebSocket connection
            room_id: The room identifier
            user_id: The user identifier
            username: Optional username for display

        Returns:
            True if connection successful
        """
        try:
            # Accept the WebSocket connection
            await websocket.accept()

            # Store connection
            self.room_connections[room_id][user_id] = websocket
            self.user_rooms[user_id].add(room_id)

            # Store metadata
            self.connection_metadata[websocket] = {
                'user_id': user_id,
                'room_id': room_id,
                'username': username or f"User{user_id}",
                'connected_at': datetime.utcnow().isoformat(),
                'messages_sent': 0
            }

            # Update statistics
            self.stats['total_connections'] += 1
            self.stats['active_connections'] = self._count_active_connections()

            logger.info(
                f"✅ User {user_id} ({username}) connected to room {room_id}. "
                f"Active connections: {self.stats['active_connections']}"
            )

            # Notify room about new user
            await self.broadcast_to_room(
                room_id=room_id,
                message={
                    'type': 'user_joined',
                    'user_id': user_id,
                    'username': username or f"User{user_id}",
                    'timestamp': datetime.utcnow().isoformat(),
                    'room_users': len(self.room_connections[room_id])
                },
                exclude_user=user_id
            )

            # Send welcome message to user
            await self.send_personal_message(
                user_id=user_id,
                message={
                    'type': 'welcome',
                    'room_id': room_id,
                    'room_users': len(self.room_connections[room_id]),
                    'message': f'Welcome to room {room_id}!'
                }
            )

            return True

        except Exception as e:
            logger.error(
                f"❌ Error connecting user {user_id} to room {room_id}: {e}")
            self.stats['errors'] += 1
            return False

    async def disconnect(
        self,
        websocket: WebSocket,
        room_id: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """
        Disconnect a user from a room.

        Args:
            websocket: The WebSocket connection
            room_id: Optional room identifier (will be retrieved from metadata if not provided)
            user_id: Optional user identifier (will be retrieved from metadata if not provided)
        """
        try:
            # Get metadata if not provided
            metadata = self.connection_metadata.get(websocket, {})
            if room_id is None:
                room_id = metadata.get('room_id')
            if user_id is None:
                user_id = metadata.get('user_id')

            if not room_id or not user_id:
                logger.warning("Cannot disconnect: missing room_id or user_id")
                return

            username = metadata.get('username', f"User{user_id}")

            # Remove from room
            if room_id in self.room_connections:
                self.room_connections[room_id].pop(user_id, None)

                # Remove empty rooms
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]

            # Remove from user rooms
            if user_id in self.user_rooms:
                self.user_rooms[user_id].discard(room_id)
                if not self.user_rooms[user_id]:
                    del self.user_rooms[user_id]

            # Remove metadata
            self.connection_metadata.pop(websocket, None)

            # Update statistics
            self.stats['active_connections'] = self._count_active_connections()

            logger.info(
                f"👋 User {user_id} ({username}) disconnected from room {room_id}. "
                f"Active connections: {self.stats['active_connections']}")

            # Notify room about user leaving
            await self.broadcast_to_room(
                room_id=room_id,
                message={
                    'type': 'user_left',
                    'user_id': user_id,
                    'username': username,
                    'timestamp': datetime.utcnow().isoformat(),
                    'room_users': len(self.room_connections.get(room_id, {}))
                }
            )

        except Exception as e:
            logger.error(f"Error disconnecting user: {e}")
            self.stats['errors'] += 1

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict,
        exclude_user: Optional[int] = None
    ):
        """
        Broadcast a message to all users in a room.

        Args:
            room_id: The room identifier
            message: The message to broadcast
            exclude_user: Optional user ID to exclude from broadcast
        """
        if room_id not in self.room_connections:
            logger.warning(f"Room {room_id} not found")
            return

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.utcnow().isoformat()

        disconnected_users = []
        success_count = 0

        for user_id, websocket in self.room_connections[room_id].items():
            # Skip excluded user
            if exclude_user and user_id == exclude_user:
                continue

            try:
                await websocket.send_json(message)
                success_count += 1
            except WebSocketDisconnect:
                logger.warning(f"User {user_id} disconnected during broadcast")
                disconnected_users.append((websocket, room_id, user_id))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append((websocket, room_id, user_id))
                self.stats['errors'] += 1

        # Clean up disconnected users
        for ws, rid, uid in disconnected_users:
            await self.disconnect(ws, rid, uid)

        self.stats['total_broadcasts'] += 1
        logger.debug(f"Broadcast to room {room_id}: {success_count} users")

    async def send_personal_message(
        self,
        user_id: int,
        message: dict,
        room_id: Optional[str] = None
    ):
        """
        Send a message to a specific user.

        Args:
            user_id: The user identifier
            message: The message to send
            room_id: Optional room identifier (if user is in multiple rooms)
        """
        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.utcnow().isoformat()

        # Find user's websocket
        websocket = None
        if room_id:
            websocket = self.room_connections.get(room_id, {}).get(user_id)
        else:
            # Search all rooms
            for room_connections in self.room_connections.values():
                if user_id in room_connections:
                    websocket = room_connections[user_id]
                    break

        if not websocket:
            logger.warning(f"User {user_id} not found")
            return

        try:
            await websocket.send_json(message)
            self.stats['total_messages'] += 1
        except WebSocketDisconnect:
            logger.warning(f"User {user_id} disconnected")
            await self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            self.stats['errors'] += 1

    async def handle_message(
        self,
        websocket: WebSocket,
        message: dict
    ):
        """
        Handle incoming WebSocket message.

        Args:
            websocket: The WebSocket connection
            message: The received message
        """
        try:
            metadata = self.connection_metadata.get(websocket)
            if not metadata:
                logger.warning("Message from unknown connection")
                return

            user_id = metadata['user_id']
            room_id = metadata['room_id']
            username = metadata['username']

            # Update message count
            metadata['messages_sent'] += 1

            # Handle different message types
            msg_type = message.get('type', 'chat')

            if msg_type == 'chat':
                # Broadcast chat message to room
                await self.broadcast_to_room(
                    room_id=room_id,
                    message={
                        'type': 'chat',
                        'user_id': user_id,
                        'username': username,
                        'content': message.get('content', ''),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )

            elif msg_type == 'sync':
                # Broadcast playback sync to room
                await self.broadcast_to_room(
                    room_id=room_id,
                    message={
                        'type': 'sync',
                        'user_id': user_id,
                        'action': message.get('action'),  # play, pause, seek
                        'timestamp': message.get('timestamp'),
                        'position': message.get('position')
                    },
                    exclude_user=user_id
                )

            elif msg_type == 'ping':
                # Respond to ping
                await self.send_personal_message(
                    user_id=user_id,
                    message={'type': 'pong'}
                )

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self.stats['errors'] += 1

    def get_room_users(self, room_id: str) -> list:
        """Get list of users in a room"""
        if room_id not in self.room_connections:
            return []

        users = []
        for user_id, websocket in self.room_connections[room_id].items():
            metadata = self.connection_metadata.get(websocket, {})
            users.append({
                'user_id': user_id,
                'username': metadata.get('username', f"User{user_id}"),
                'connected_at': metadata.get('connected_at'),
                'messages_sent': metadata.get('messages_sent', 0)
            })

        return users

    def get_active_rooms(self) -> list:
        """Get list of active rooms"""
        rooms = []
        for room_id, connections in self.room_connections.items():
            rooms.append({
                'room_id': room_id,
                'user_count': len(connections),
                'users': [uid for uid in connections.keys()]
            })
        return rooms

    def _count_active_connections(self) -> int:
        """Count total active connections"""
        return sum(len(conns) for conns in self.room_connections.values())

    def get_stats(self) -> dict:
        """Get connection manager statistics"""
        return {
            **self.stats,
            'active_rooms': len(self.room_connections),
            'total_users': len(self.user_rooms)
        }


# Global connection manager instance
connection_manager = ConnectionManager()


# Convenience functions

async def connect_user(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    username: Optional[str] = None
) -> bool:
    """Connect a user to a room"""
    return await connection_manager.connect(websocket, room_id, user_id, username)


async def disconnect_user(
    websocket: WebSocket,
    room_id: Optional[str] = None,
    user_id: Optional[int] = None
):
    """Disconnect a user from a room"""
    await connection_manager.disconnect(websocket, room_id, user_id)


async def broadcast_to_room(
        room_id: str,
        message: dict,
        exclude_user: Optional[int] = None):
    """Broadcast a message to a room"""
    await connection_manager.broadcast_to_room(room_id, message, exclude_user)


async def send_to_user(
        user_id: int,
        message: dict,
        room_id: Optional[str] = None):
    """Send a message to a specific user"""
    await connection_manager.send_personal_message(user_id, message, room_id)


def get_room_info(room_id: str) -> dict:
    """Get information about a room"""
    return {
        'room_id': room_id,
        'users': connection_manager.get_room_users(room_id),
        'user_count': len(connection_manager.room_connections.get(room_id, {}))
    }


def get_websocket_stats() -> dict:
    """Get WebSocket statistics"""
    return connection_manager.get_stats()


# ══════════════════════════════════════════════════════════════════════
# Content Update Notifications
# ══════════════════════════════════════════════════════════════════════

async def broadcast_content_update(
    content_type: str,
    action: str,
    content_data: dict
):
    """
    Broadcast content update to all connected clients

    Args:
        content_type: Type of content ('movie', 'series', 'episode')
        action: Action performed ('added', 'updated', 'deleted')
        content_data: Content metadata
    """
    message = {
        'type': 'content_update',
        'content_type': content_type,
        'action': action,
        'data': content_data,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    # Broadcast to all active rooms
    for room_id in list(connection_manager.room_connections.keys()):
        await broadcast_to_room(room_id, message)

    logger.info(
        f"📢 Broadcasted {content_type} {action}: {content_data.get('title', 'N/A')}")


async def notify_new_movie(movie_data: dict):
    """Notify all clients about new movie"""
    await broadcast_content_update('movie', 'added', {
        'id': movie_data.get('id'),
        'title': movie_data.get('title'),
        'poster_path': movie_data.get('poster_path'),
        'rating': movie_data.get('rating'),
        'year': movie_data.get('release_date', '')[:4] if movie_data.get('release_date') else None
    })


async def notify_new_series(series_data: dict):
    """Notify all clients about new series"""
    await broadcast_content_update('series', 'added', {
        'id': series_data.get('id'),
        'title': series_data.get('title'),
        'poster_path': series_data.get('poster_path'),
        'rating': series_data.get('rating'),
        'total_seasons': series_data.get('total_seasons')
    })


async def notify_new_episode(episode_data: dict):
    """Notify all clients about new episode"""
    await broadcast_content_update('episode', 'added', {
        'id': episode_data.get('id'),
        'series_id': episode_data.get('series_id'),
        'season_number': episode_data.get('season_number'),
        'episode_number': episode_data.get('episode_number'),
        'title': episode_data.get('title')
    })


async def notify_frontend_sync_complete(stats: dict):
    """Notify all clients that frontend data has been synced"""
    message = {
        'type': 'sync_complete',
        'stats': stats,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    # Broadcast to all active rooms
    for room_id in list(connection_manager.room_connections.keys()):
        await broadcast_to_room(room_id, message)

    logger.info("📢 Broadcasted sync complete notification")


async def notify_database_update():
    """Notify all clients to refresh their data"""
    message = {
        'type': 'database_update',
        'action': 'refresh_required',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }

    # Broadcast to all active rooms
    for room_id in list(connection_manager.room_connections.keys()):
        await broadcast_to_room(room_id, message)

    logger.info("📢 Broadcasted database update notification")


# Made with ❤️ by Bob

# Made with Bob
