"""
WebSocket Manager - Real-time Communication for Watch Rooms
Handles WebSocket connections, message broadcasting, and event distribution
"""

import asyncio
import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
from datetime import datetime

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Connection Manager
# ══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections for watch rooms"""

    def __init__(self):
        # room_id -> set of (websocket, user_id) tuples
        self.active_connections: Dict[str, Set[tuple]] = {}
        # websocket -> (room_id, user_id) mapping
        self.connection_info: Dict[WebSocket, tuple] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room_id: str, user_id: int):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()

        async with self.lock:
            if room_id not in self.active_connections:
                self.active_connections[room_id] = set()

            self.active_connections[room_id].add((websocket, user_id))
            self.connection_info[websocket] = (room_id, user_id)

        logger.info(f"User {user_id} connected to room {room_id}")

        # Send connection confirmation
        await self.send_personal_message(websocket, {
            "type": "connected",
            "room_id": room_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Notify others
        await self.broadcast_to_room(room_id, {
            "type": "participant_joined",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        }, exclude_user=user_id)

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        async with self.lock:
            if websocket in self.connection_info:
                room_id, user_id = self.connection_info[websocket]

                # Remove from active connections
                if room_id in self.active_connections:
                    self.active_connections[room_id].discard(
                        (websocket, user_id))

                    # Clean up empty rooms
                    if not self.active_connections[room_id]:
                        del self.active_connections[room_id]

                del self.connection_info[websocket]

                logger.info(f"User {user_id} disconnected from room {room_id}")

                # Notify others
                await self.broadcast_to_room(room_id, {
                    "type": "participant_left",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                })

    async def send_personal_message(
            self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude_user: Optional[int] = None
    ):
        """Broadcast a message to all connections in a room"""
        if room_id not in self.active_connections:
            return

        # Create a copy of connections to avoid modification during iteration
        connections = list(self.active_connections[room_id])

        for websocket, user_id in connections:
            if exclude_user and user_id == exclude_user:
                continue

            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                # Connection is broken, remove it
                await self.disconnect(websocket)

    async def broadcast_to_user(
            self, room_id: str, user_id: int, message: Dict[str, Any]):
        """Send a message to a specific user in a room"""
        if room_id not in self.active_connections:
            return

        for websocket, uid in self.active_connections[room_id]:
            if uid == user_id:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")

    def get_room_connections(self, room_id: str) -> int:
        """Get number of active connections in a room"""
        if room_id not in self.active_connections:
            return 0
        return len(self.active_connections[room_id])

    def get_connected_users(self, room_id: str) -> Set[int]:
        """Get set of user IDs connected to a room"""
        if room_id not in self.active_connections:
            return set()
        return {user_id for _, user_id in self.active_connections[room_id]}

    def is_user_connected(self, room_id: str, user_id: int) -> bool:
        """Check if a user is connected to a room"""
        return user_id in self.get_connected_users(room_id)


# Global connection manager instance
manager = ConnectionManager()


# ══════════════════════════════════════════════════════════════════════════════
# Event Handlers
# ══════════════════════════════════════════════════════════════════════════════

async def handle_websocket_message(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")

    try:
        if message_type == "ping":
            # Heartbeat
            await handle_ping(websocket, room_id, user_id, message)

        elif message_type == "sync_event":
            # Video synchronization event
            await handle_sync_event(websocket, room_id, user_id, message)

        elif message_type == "chat_message":
            # Chat message
            await handle_chat_message(websocket, room_id, user_id, message)

        elif message_type == "reaction":
            # Reaction/emoji
            await handle_reaction(websocket, room_id, user_id, message)

        elif message_type == "typing":
            # Typing indicator
            await handle_typing(websocket, room_id, user_id, message)

        elif message_type == "request_sync":
            # Request current sync state
            await handle_sync_request(websocket, room_id, user_id, message)

        else:
            logger.warning(f"Unknown message type: {message_type}")

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_ping(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle ping/heartbeat messages"""
    from app.watch_rooms import update_participant_ping

    # Update last ping time in database
    update_participant_ping(room_id, user_id)

    # Send pong response
    await manager.send_personal_message(websocket, {
        "type": "pong",
        "timestamp": datetime.utcnow().isoformat(),
        "client_timestamp": message.get("timestamp")
    })


async def handle_sync_event(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle video synchronization events"""
    from app.room_sync import sync_playback

    action = message.get("action")
    timestamp = message.get("timestamp", 0.0)
    playback_speed = message.get("playback_speed", 1.0)

    try:
        # Process sync action
        sync_state = sync_playback(
            room_id,
            user_id,
            action,
            timestamp,
            playback_speed)

        # Broadcast to all participants
        await manager.broadcast_to_room(room_id, {
            "type": "sync_event",
            "action": action,
            "timestamp": timestamp,
            "playback_speed": playback_speed,
            "user_id": user_id,
            "sync_state": sync_state,
            "server_timestamp": datetime.utcnow().isoformat()
        })

    except ValueError as e:
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_chat_message(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle chat messages"""
    from app.watch_rooms import send_room_message

    content = message.get("content", "")
    message_type = message.get("message_type", "text")
    reply_to = message.get("reply_to")

    if not content:
        return

    try:
        # Save message to database
        saved_message = send_room_message(
            room_id=room_id,
            user_id=user_id,
            content=content,
            message_type=message_type,
            reply_to=reply_to
        )

        # Broadcast to all participants
        await manager.broadcast_to_room(room_id, {
            "type": "chat_message",
            "message": saved_message,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


async def handle_reaction(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle reactions/emojis"""
    from app.watch_rooms import add_reaction

    reaction_type = message.get("reaction_type")
    timestamp = message.get("timestamp", 0.0)

    if not reaction_type:
        return

    try:
        # Save reaction
        reaction_id = add_reaction(room_id, user_id, reaction_type, timestamp)

        # Broadcast to all participants
        await manager.broadcast_to_room(room_id, {
            "type": "reaction",
            "reaction_id": reaction_id,
            "user_id": user_id,
            "reaction_type": reaction_type,
            "timestamp": timestamp,
            "server_timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error handling reaction: {e}")


async def handle_typing(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle typing indicators"""
    is_typing = message.get("is_typing", False)

    # Broadcast typing status to others
    await manager.broadcast_to_room(room_id, {
        "type": "typing",
        "user_id": user_id,
        "is_typing": is_typing,
        "timestamp": datetime.utcnow().isoformat()
    }, exclude_user=user_id)


async def handle_sync_request(
    websocket: WebSocket,
    room_id: str,
    user_id: int,
    message: Dict[str, Any]
):
    """Handle sync state requests"""
    from app.room_sync import resync_participant

    try:
        # Get current sync state
        sync_state = resync_participant(room_id, user_id)

        # Send to requesting user
        await manager.send_personal_message(websocket, {
            "type": "sync_state",
            "sync_state": sync_state,
            "timestamp": datetime.utcnow().isoformat()
        })

    except Exception as e:
        await manager.send_personal_message(websocket, {
            "type": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════════════
# Background Tasks
# ══════════════════════════════════════════════════════════════════════════════

async def auto_sync_task(room_id: str):
    """
    Background task to automatically sync participants every 5 seconds
    Runs while room has active connections
    """
    from app.room_sync import auto_sync_participants

    while manager.get_room_connections(room_id) > 0:
        try:
            # Perform auto-sync
            sync_state = auto_sync_participants(room_id)

            # Broadcast sync state to all participants
            await manager.broadcast_to_room(room_id, {
                "type": "auto_sync",
                "sync_state": sync_state,
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error in auto-sync task for room {room_id}: {e}")

        # Wait 5 seconds before next sync
        await asyncio.sleep(5)


async def cleanup_inactive_connections():
    """
    Background task to clean up inactive connections
    Runs periodically to remove stale connections
    """
    while True:
        try:
            # Check all connections for activity
            for room_id in list(manager.active_connections.keys()):
                connections = list(manager.active_connections[room_id])

                for websocket, user_id in connections:
                    try:
                        # Send ping to check if connection is alive
                        await manager.send_personal_message(websocket, {
                            "type": "ping",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    except Exception:
                        # Connection is dead, remove it
                        await manager.disconnect(websocket)

        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")

        # Run every 30 seconds
        await asyncio.sleep(30)


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

async def notify_room_update(
        room_id: str, update_type: str, data: Dict[str, Any]):
    """
    Notify all participants about a room update
    Used for settings changes, participant changes, etc.
    """
    await manager.broadcast_to_room(room_id, {
        "type": "room_updated",
        "update_type": update_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_participant_kicked(room_id: str, user_id: int):
    """Notify a participant that they were kicked"""
    await manager.broadcast_to_user(room_id, user_id, {
        "type": "kicked",
        "message": "You have been removed from the room",
        "timestamp": datetime.utcnow().isoformat()
    })


async def notify_room_ended(room_id: str):
    """Notify all participants that the room has ended"""
    await manager.broadcast_to_room(room_id, {
        "type": "room_ended",
        "message": "The room has been closed",
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_system_message(room_id: str, message: str):
    """Broadcast a system message to all participants"""
    await manager.broadcast_to_room(room_id, {
        "type": "system_message",
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })


def get_room_stats(room_id: str) -> Dict[str, Any]:
    """Get statistics about a room's WebSocket connections"""
    return {
        "room_id": room_id,
        "active_connections": manager.get_room_connections(room_id),
        "connected_users": list(manager.get_connected_users(room_id)),
        "timestamp": datetime.utcnow().isoformat()
    }

# Made with Bob
