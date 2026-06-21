# 3_realtime_system.py
"""
Instagram Clone - Real-time System
WebSocket, Notifications, Live Updates, Chat System
"""

import asyncio
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
from cassandra.cluster import Cluster
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID
import uvicorn
from prometheus_client import Counter, Gauge, Histogram
import aioredis
from typing import Optional
import asyncio
from contextlib import asynccontextmanager
import async_timeout
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential
import websockets
from websockets.exceptions import ConnectionClosed
from pydantic import BaseModel, Field
import bcrypt
import jwt
import httpx
from uuid import UUID
import pickle

# =============================================
# Configuration
# =============================================
class RealtimeConfig:
    REDIS_URL = "redis://redis:6379/0"
    CASSANDRA_HOSTS = ["cassandra"]
    CASSANDRA_KEYSPACE = "instagram"
    POSTGRES_URL = "postgresql://admin:securepass@postgres:5432/instagram"
    JWT_SECRET = "your-super-secret-key"
    WS_HEARTBEAT_INTERVAL = 30
    WS_MAX_CONNECTIONS = 10000
    MESSAGE_BATCH_SIZE = 100
    PRESENCE_EXPIRE = 60
    STREAM_CHUNK_SIZE = 4096

config = RealtimeConfig()

# =============================================
# Logging
# =============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================
# Prometheus Metrics
# =============================================
WS_CONNECTIONS = Gauge('websocket_connections_total', 'Total WebSocket connections')
WS_MESSAGES = Counter('websocket_messages_total', 'Total WebSocket messages', ['type'])
WS_LATENCY = Histogram('websocket_message_latency_seconds', 'WebSocket message latency', ['type'])
NOTIFICATIONS_SENT = Counter('notifications_sent_total', 'Total notifications sent', ['type'])
PRESENCE_UPDATES = Counter('presence_updates_total', 'Total presence updates', ['status'])

# =============================================
# Data Models
# =============================================
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    receiver_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    text = Column(Text)
    media_url = Column(String(500))
    media_type = Column(String(20))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    is_group = Column(Boolean, default=False)
    created_by = Column(PGUUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatRoomMember(Base):
    __tablename__ = "chat_room_members"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(PGUUID(as_uuid=True), ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# =============================================
# Redis Manager for Real-time
# =============================================
class RealtimeRedisManager:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        self.connection_pool = redis.ConnectionPool.from_url(
            config.REDIS_URL,
            max_connections=50,
            decode_responses=True,
            health_check_interval=30
        )
        self.client = redis.Redis(connection_pool=self.connection_pool)
        self.pubsub = self.client.pubsub()
        await self._init_redis()
        logger.info("Realtime Redis connected")
        return self
    
    async def _init_redis(self):
        # Initialize Redis with required keys
        await self.client.set('system:initialized', 'true')
    
    # Presence Management
    async def set_user_presence(self, user_id: str, status: str = 'online', metadata: Dict = None):
        key = f"presence:{user_id}"
        data = {
            'status': status,
            'last_seen': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        await self.client.setex(key, config.PRESENCE_EXPIRE, json.dumps(data))
        PRESENCE_UPDATES.labels(status=status).inc()
    
    async def get_user_presence(self, user_id: str) -> Optional[Dict]:
        key = f"presence:{user_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def get_users_presence(self, user_ids: List[str]) -> Dict[str, Dict]:
        result = {}
        for user_id in user_ids:
            presence = await self.get_user_presence(user_id)
            if presence:
                result[user_id] = presence
        return result
    
    # User Sessions
    async def add_user_session(self, user_id: str, session_id: str, connection_id: str):
        key = f"user_sessions:{user_id}"
        await self.client.sadd(key, f"{session_id}:{connection_id}")
        await self.client.expire(key, 3600)
    
    async def remove_user_session(self, user_id: str, session_id: str, connection_id: str):
        key = f"user_sessions:{user_id}"
        await self.client.srem(key, f"{session_id}:{connection_id}")
    
    async def get_user_sessions(self, user_id: str) -> List[str]:
        key = f"user_sessions:{user_id}"
        sessions = await self.client.smembers(key)
        return list(sessions)
    
    # Typing Indicators
    async def set_user_typing(self, user_id: str, chat_id: str, is_typing: bool = True):
        key = f"typing:{chat_id}"
        if is_typing:
            await self.client.setex(key, 5, user_id)
        else:
            await self.client.delete(key)
    
    async def get_typing_users(self, chat_id: str) -> List[str]:
        key = f"typing:{chat_id}"
        users = await self.client.smembers(key)
        return list(users)
    
    # Message Queue
    async def add_to_message_queue(self, user_id: str, message: Dict):
        key = f"message_queue:{user_id}"
        await self.client.rpush(key, json.dumps(message))
        await self.client.expire(key, 3600)
    
    async def get_message_batch(self, user_id: str, batch_size: int = 100) -> List[Dict]:
        key = f"message_queue:{user_id}"
        messages = await self.client.lrange(key, 0, batch_size - 1)
        if messages:
            await self.client.ltrim(key, len(messages), -1)
            return [json.loads(msg) for msg in messages]
        return []
    
    # Pub/Sub
    async def publish(self, channel: str, message: Dict):
        await self.client.publish(channel, json.dumps(message))
    
    async def subscribe(self, channels: List[str]):
        if self.pubsub:
            for channel in channels:
                await self.pubsub.subscribe(channel)
    
    async def unsubscribe(self, channels: List[str]):
        if self.pubsub:
            for channel in channels:
                await self.pubsub.unsubscribe(channel)
    
    async def listen(self):
        if self.pubsub:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    yield message['channel'], json.loads(message['data'])
    
    # Rate Limiting
    async def check_rate_limit(self, key: str, limit: int, period: int) -> bool:
        current = await self.client.get(key)
        if current is None:
            await self.client.setex(key, period, 1)
            return True
        current = int(current)
        if current >= limit:
            return False
        await self.client.incr(key)
        return True
    
    # Distributed Lock
    async def acquire_lock(self, key: str, ttl: int = 10) -> bool:
        return await self.client.set(key, 'locked', ex=ttl, nx=True)
    
    async def release_lock(self, key: str):
        await self.client.delete(key)

redis_manager = RealtimeRedisManager()

# =============================================
# Cassandra Manager for Activity Tracking
# =============================================
class CassandraActivityManager:
    def __init__(self):
        self.cluster = None
        self.session = None
    
    async def connect(self):
        self.cluster = Cluster(config.CASSANDRA_HOSTS)
        self.session = self.cluster.connect(config.CASSANDRA_KEYSPACE)
        await self.create_tables()
        logger.info("Cassandra activity manager connected")
        return self
    
    async def create_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS user_activities_realtime (
                user_id UUID,
                activity_time TIMESTAMP,
                activity_type TEXT,
                target_id UUID,
                data TEXT,
                PRIMARY KEY (user_id, activity_time)
            ) WITH CLUSTERING ORDER BY (activity_time DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                chat_id UUID,
                message_time TIMESTAMP,
                message_id UUID,
                sender_id UUID,
                text TEXT,
                media_url TEXT,
                metadata TEXT,
                PRIMARY KEY (chat_id, message_time, message_id)
            ) WITH CLUSTERING ORDER BY (message_time DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS user_notifications (
                user_id UUID,
                notification_time TIMESTAMP,
                notification_id UUID,
                type TEXT,
                message TEXT,
                data TEXT,
                is_read BOOLEAN,
                PRIMARY KEY (user_id, notification_time, notification_id)
            ) WITH CLUSTERING ORDER BY (notification_time DESC)
            """
        ]
        for query in queries:
            self.session.execute(query)
    
    async def log_activity(self, user_id: str, activity_type: str, target_id: str = None, data: Dict = None):
        query = """
            INSERT INTO user_activities_realtime 
            (user_id, activity_time, activity_type, target_id, data)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.session.execute(query, (
            UUID(user_id),
            datetime.utcnow(),
            activity_type,
            UUID(target_id) if target_id else None,
            json.dumps(data) if data else None
        ))
    
    async def save_chat_message(self, chat_id: str, message_id: str, sender_id: str, text: str, media_url: str = None, metadata: Dict = None):
        query = """
            INSERT INTO chat_messages 
            (chat_id, message_time, message_id, sender_id, text, media_url, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.session.execute(query, (
            UUID(chat_id),
            datetime.utcnow(),
            UUID(message_id),
            UUID(sender_id),
            text,
            media_url,
            json.dumps(metadata) if metadata else None
        ))
    
    async def get_chat_messages(self, chat_id: str, limit: int = 100) -> List[Dict]:
        query = """
            SELECT * FROM chat_messages 
            WHERE chat_id = %s 
            LIMIT %s
        """
        rows = self.session.execute(query, (UUID(chat_id), limit))
        result = []
        for row in rows:
            result.append({
                'message_id': str(row.message_id),
                'sender_id': str(row.sender_id),
                'text': row.text,
                'media_url': row.media_url,
                'timestamp': row.message_time.isoformat(),
                'metadata': json.loads(row.metadata) if row.metadata else {}
            })
        return result

cassandra_activity = CassandraActivityManager()

# =============================================
# WebSocket Connection Manager
# =============================================
@dataclass
class WebSocketConnection:
    websocket: WebSocket
    user_id: str
    session_id: str
    connection_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    subscriptions: Set[str] = field(default_factory=set)

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Dict[str, WebSocketConnection]] = defaultdict(dict)
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.message_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.background_tasks = set()
    
    def get_connection_key(self, user_id: str, connection_id: str) -> str:
        return f"{user_id}:{connection_id}"
    
    async def connect(self, websocket: WebSocket, user_id: str, session_id: str) -> str:
        connection_id = str(uuid.uuid4())
        await websocket.accept()
        
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            session_id=session_id,
            connection_id=connection_id
        )
        
        self.connections[user_id][connection_id] = connection
        self.user_connections[user_id].add(connection_id)
        
        # Update presence
        await redis_manager.set_user_presence(user_id, 'online', {
            'session_id': session_id,
            'connection_id': connection_id
        })
        
        # Add session
        await redis_manager.add_user_session(user_id, session_id, connection_id)
        
        # Start heartbeat
        self.heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat_loop(connection)
        )
        
        WS_CONNECTIONS.inc()
        logger.info(f"User {user_id} connected with connection {connection_id}")
        
        # Send connection success
        await websocket.send_json({
            'type': 'connection_established',
            'connection_id': connection_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return connection_id
    
    async def disconnect(self, user_id: str, connection_id: str):
        if user_id in self.connections and connection_id in self.connections[user_id]:
            connection = self.connections[user_id][connection_id]
            
            # Stop heartbeat
            if connection_id in self.heartbeat_tasks:
                self.heartbeat_tasks[connection_id].cancel()
                del self.heartbeat_tasks[connection_id]
            
            # Remove connection
            del self.connections[user_id][connection_id]
            self.user_connections[user_id].discard(connection_id)
            
            if not self.connections[user_id]:
                del self.connections[user_id]
            
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # Set user as offline if no connections
                await redis_manager.set_user_presence(user_id, 'offline')
            
            # Remove session
            await redis_manager.remove_user_session(user_id, connection.session_id, connection_id)
            
            WS_CONNECTIONS.dec()
            logger.info(f"User {user_id} disconnected connection {connection_id}")
    
    async def _heartbeat_loop(self, connection: WebSocketConnection):
        try:
            while True:
                await asyncio.sleep(30)
                connection.last_heartbeat = datetime.utcnow()
                try:
                    await connection.websocket.send_json({
                        'type': 'heartbeat',
                        'timestamp': datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Heartbeat failed for connection {connection.connection_id}: {e}")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")
    
    async def send_to_user(self, user_id: str, message: Dict, exclude_connection_id: str = None):
        """Send message to all connections of a user"""
        if user_id in self.connections:
            for conn_id, connection in self.connections[user_id].items():
                if conn_id != exclude_connection_id:
                    try:
                        await connection.websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"Failed to send message to {user_id}: {e}")
    
    async def send_to_connection(self, user_id: str, connection_id: str, message: Dict):
        """Send message to specific connection"""
        if user_id in self.connections and connection_id in self.connections[user_id]:
            try:
                await self.connections[user_id][connection_id].websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to connection {connection_id}: {e}")
                return False
        return False
    
    async def broadcast(self, message: Dict, exclude_user_id: str = None):
        """Broadcast message to all connected users"""
        for user_id in self.connections:
            if user_id != exclude_user_id:
                await self.send_to_user(user_id, message)
    
    async def subscribe_to_channel(self, user_id: str, connection_id: str, channel: str):
        if user_id in self.connections and connection_id in self.connections[user_id]:
            self.connections[user_id][connection_id].subscriptions.add(channel)
            await redis_manager.subscribe([channel])
    
    async def unsubscribe_from_channel(self, user_id: str, connection_id: str, channel: str):
        if user_id in self.connections and connection_id in self.connections[user_id]:
            self.connections[user_id][connection_id].subscriptions.discard(channel)
            # Check if any other connection is subscribed to this channel
            subscriptions = []
            for uid in self.connections:
                for cid, conn in self.connections[uid].items():
                    if channel in conn.subscriptions:
                        subscriptions.append((uid, cid))
            if not subscriptions:
                await redis_manager.unsubscribe([channel])
    
    async def handle_pubsub_messages(self):
        """Process pubsub messages from Redis"""
        async for channel, data in redis_manager.listen():
            # Deliver to all subscribed connections
            for user_id in self.connections:
                for conn_id, connection in self.connections[user_id].items():
                    if channel in connection.subscriptions:
                        await self.send_to_connection(user_id, conn_id, {
                            'type': 'pubsub',
                            'channel': channel,
                            'data': data
                        })
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        total_connections = sum(len(conns) for conns in self.connections.values())
        total_users = len(self.connections)
        return {
            'total_connections': total_connections,
            'total_users': total_users,
            'connections_per_user': {
                user_id: len(conns) for user_id, conns in self.connections.items()
            }
        }

ws_manager = WebSocketManager()

# =============================================
# Notification Service
# =============================================
class NotificationService:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    async def create_notification(self, user_id: str, type: str, message: str, data: Dict = None) -> Dict:
        """Create and store a notification"""
        with self.db_session_factory() as session:
            notification = Notification(
                user_id=UUID(user_id),
                type=type,
                message=message,
                data=data
            )
            session.add(notification)
            session.commit()
            session.refresh(notification)
            
            notification_data = {
                'id': str(notification.id),
                'type': notification.type,
                'message': notification.message,
                'data': notification.data,
                'created_at': notification.created_at.isoformat(),
                'is_read': notification.is_read
            }
            
            # Send real-time notification
            await ws_manager.send_to_user(user_id, {
                'type': 'notification',
                'notification': notification_data
            })
            
            # Log to Cassandra
            await cassandra_activity.log_activity(
                user_id,
                'notification',
                str(notification.id),
                {'type': type, 'message': message}
            )
            
            NOTIFICATIONS_SENT.labels(type=type).inc()
            
            return notification_data
    
    async def get_notifications(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get user notifications"""
        with self.db_session_factory() as session:
            notifications = session.query(Notification).filter(
                Notification.user_id == UUID(user_id)
            ).order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
            
            return [{
                'id': str(n.id),
                'type': n.type,
                'message': n.message,
                'data': n.data,
                'created_at': n.created_at.isoformat(),
                'is_read': n.is_read
            } for n in notifications]
    
    async def mark_as_read(self, user_id: str, notification_id: str):
        """Mark notification as read"""
        with self.db_session_factory() as session:
            notification = session.query(Notification).filter(
                Notification.id == UUID(notification_id),
                Notification.user_id == UUID(user_id)
            ).first()
            
            if notification:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
                session.commit()
                return True
            return False
    
    async def mark_all_as_read(self, user_id: str):
        """Mark all notifications as read"""
        with self.db_session_factory() as session:
            notifications = session.query(Notification).filter(
                Notification.user_id == UUID(user_id),
                Notification.is_read == False
            ).all()
            
            for notification in notifications:
                notification.is_read = True
                notification.read_at = datetime.utcnow()
            
            session.commit()
            return len(notifications)

# =============================================
# Chat Service
# =============================================
class ChatService:
    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
    
    async def send_message(self, sender_id: str, receiver_id: str, text: str, media_url: str = None) -> Dict:
        """Send a direct message"""
        with self.db_session_factory() as session:
            # Create or get chat room
            chat_id = await self._get_or_create_chat_room(session, sender_id, receiver_id)
            
            message_id = str(uuid.uuid4())
            message = Message(
                id=UUID(message_id),
                sender_id=UUID(sender_id),
                receiver_id=UUID(receiver_id),
                text=text,
                media_url=media_url
            )
            session.add(message)
            session.commit()
            
            message_data = {
                'id': str(message.id),
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'text': text,
                'media_url': media_url,
                'created_at': message.created_at.isoformat(),
                'is_read': message.is_read
            }
            
            # Save to Cassandra
            await cassandra_activity.save_chat_message(
                chat_id,
                message_id,
                sender_id,
                text,
                media_url
            )
            
            # Send to receiver via WebSocket
            await ws_manager.send_to_user(receiver_id, {
                'type': 'message',
                'message': message_data
            })
            
            # Send confirmation to sender
            await ws_manager.send_to_user(sender_id, {
                'type': 'message_sent',
                'message': message_data
            })
            
            return message_data
    
    async def _get_or_create_chat_room(self, session, user1_id: str, user2_id: str) -> str:
        """Get or create a chat room for two users"""
        # Check if chat room exists
        room = session.query(ChatRoom).filter(
            ChatRoom.is_group == False,
            ChatRoom.members.any(user_id=UUID(user1_id)),
            ChatRoom.members.any(user_id=UUID(user2_id))
        ).first()
        
        if room:
            return str(room.id)
        
        # Create new chat room
        room = ChatRoom(
            is_group=False,
            created_by=UUID(user1_id)
        )
        session.add(room)
        session.flush()
        
        # Add members
        member1 = ChatRoomMember(room_id=room.id, user_id=UUID(user1_id))
        member2 = ChatRoomMember(room_id=room.id, user_id=UUID(user2_id))
        session.add_all([member1, member2])
        session.commit()
        
        return str(room.id)
    
    async def get_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user conversations"""
        with self.db_session_factory() as session:
            # Get all chat rooms for user
            rooms = session.query(ChatRoom).join(
                ChatRoomMember
            ).filter(ChatRoomMember.user_id == UUID(user_id)).all()
            
            conversations = []
            for room in rooms:
                # Get last message
                last_message = session.query(Message).filter(
                    Message.sender_id.in_([m.user_id for m in room.members]),
                    Message.receiver_id.in_([m.user_id for m in room.members])
                ).order_by(Message.created_at.desc()).first()
                
                # Get other user info (for direct chats)
                other_member = None
                if not room.is_group:
                    for member in room.members:
                        if str(member.user_id) != user_id:
                            other_member = member
            
                conversations.append({
                    'room_id': str(room.id),
                    'is_group': room.is_group,
                    'name': room.name if room.is_group else other_member.user_id if other_member else None,
                    'last_message': last_message.text if last_message else None,
                    'last_message_time': last_message.created_at.isoformat() if last_message else None,
                    'unread_count': 0  # Implement unread count
                })
            
            return conversations
    
    async def get_messages(self, user_id: str, chat_id: str, limit: int = 100, before: str = None) -> List[Dict]:
        """Get messages from a chat room"""
        with self.db_session_factory() as session:
            # Check if user is in room
            is_member = session.query(ChatRoomMember).filter(
                ChatRoomMember.room_id == UUID(chat_id),
                ChatRoomMember.user_id == UUID(user_id)
            ).first()
            
            if not is_member:
                raise HTTPException(status_code=403, detail="Not a member of this chat")
            
            # Get messages
            query = session.query(Message).filter(
                Message.chat_id == UUID(chat_id)
            ).order_by(Message.created_at.desc()).limit(limit)
            
            if before:
                query = query.filter(Message.created_at < datetime.fromisoformat(before))
            
            messages = query.all()
            
            return [{
                'id': str(m.id),
                'sender_id': str(m.sender_id),
                'text': m.text,
                'media_url': m.media_url,
                'created_at': m.created_at.isoformat(),
                'is_read': m.is_read
            } for m in messages[::-1]]
    
    async def mark_messages_as_read(self, user_id: str, chat_id: str, message_ids: List[str] = None):
        """Mark messages as read"""
        with self.db_session_factory() as session:
            query = session.query(Message).filter(
                Message.receiver_id == UUID(user_id),
                Message.is_read == False
            )
            
            if message_ids:
                query = query.filter(Message.id.in_([UUID(id) for id in message_ids]))
            else:
                query = query.filter(Message.chat_id == UUID(chat_id))
            
            updated = query.update({'is_read': True, 'read_at': datetime.utcnow()})
            session.commit()
            
            return updated

# =============================================
# Main Application
# =============================================
app = FastAPI(title="Instagram Realtime System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# Database Setup
# =============================================
engine = create_engine(config.POSTGRES_URL, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================================
# Services
# =============================================
notification_service = NotificationService(SessionLocal)
chat_service = ChatService(SessionLocal)

# =============================================
# Event Handlers
# =============================================
@app.on_event("startup")
async def startup_event():
    await redis_manager.connect()
    await cassandra_activity.connect()
    # Start background tasks
    asyncio.create_task(ws_manager.handle_pubsub_messages())
    logger.info("Realtime system started")

@app.on_event("shutdown")
async def shutdown_event():
    # Close all WebSocket connections
    for user_id in list(ws_manager.connections.keys()):
        for connection_id in list(ws_manager.connections[user_id].keys()):
            await ws_manager.disconnect(user_id, connection_id)
    
    if redis_manager.client:
        await redis_manager.client.close()
    if cassandra_activity.cluster:
        cassandra_activity.cluster.shutdown()

# =============================================
# Authentication Helper
# =============================================
async def authenticate_websocket(websocket: WebSocket) -> tuple[str, str]:
    """Authenticate WebSocket connection using JWT in query params"""
    token = websocket.query_params.get('token')
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return None, None
    
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get('sub')
        session_id = payload.get('sid')
        if not user_id:
            await websocket.close(code=4002, reason="Invalid token")
            return None, None
        return user_id, session_id
    except jwt.ExpiredSignatureError:
        await websocket.close(code=4003, reason="Token expired")
        return None, None
    except jwt.InvalidTokenError:
        await websocket.close(code=4004, reason="Invalid token")
        return None, None

# =============================================
# WebSocket Endpoint
# =============================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time communication"""
    user_id, session_id = await authenticate_websocket(websocket)
    if not user_id:
        return
    
    connection_id = await ws_manager.connect(websocket, user_id, session_id)
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=60)
                await handle_websocket_message(user_id, connection_id, data)
            except asyncio.TimeoutError:
                # Send heartbeat ping
                await websocket.send_json({
                    'type': 'ping',
                    'timestamp': datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, connection_id)
    
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await ws_manager.disconnect(user_id, connection_id)

# =============================================
# WebSocket Message Handlers
# =============================================
async def handle_websocket_message(user_id: str, connection_id: str, data: Dict):
    """Handle incoming WebSocket messages"""
    msg_type = data.get('type')
    
    if not msg_type:
        return
    
    WS_MESSAGES.labels(type=msg_type).inc()
    
    if msg_type == 'heartbeat':
        await handle_heartbeat(user_id, connection_id)
    
    elif msg_type == 'message':
        await handle_chat_message(user_id, connection_id, data)
    
    elif msg_type == 'typing':
        await handle_typing(user_id, connection_id, data)
    
    elif msg_type == 'notification_read':
        await handle_notification_read(user_id, connection_id, data)
    
    elif msg_type == 'presence':
        await handle_presence(user_id, connection_id, data)
    
    elif msg_type == 'subscribe':
        await handle_subscribe(user_id, connection_id, data)
    
    elif msg_type == 'unsubscribe':
        await handle_unsubscribe(user_id, connection_id, data)
    
    elif msg_type == 'message_read':
        await handle_message_read(user_id, connection_id, data)
    
    elif msg_type == 'get_messages':
        await handle_get_messages(user_id, connection_id, data)
    
    elif msg_type == 'get_notifications':
        await handle_get_notifications(user_id, connection_id, data)
    
    else:
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'error',
            'error': f'Unknown message type: {msg_type}'
        })

async def handle_heartbeat(user_id: str, connection_id: str):
    """Handle heartbeat message"""
    await ws_manager.send_to_connection(user_id, connection_id, {
        'type': 'heartbeat_ack',
        'timestamp': datetime.utcnow().isoformat()
    })

async def handle_chat_message(user_id: str, connection_id: str, data: Dict):
    """Handle chat message"""
    receiver_id = data.get('receiver_id')
    text = data.get('text')
    media_url = data.get('media_url')
    
    if not receiver_id or not text:
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'error',
            'error': 'Missing required fields'
        })
        return
    
    try:
        message = await chat_service.send_message(user_id, receiver_id, text, media_url)
        
        # If receiver is offline, store in message queue
        presence = await redis_manager.get_user_presence(receiver_id)
        if not presence or presence.get('status') != 'online':
            await redis_manager.add_to_message_queue(receiver_id, message)
        
    except Exception as e:
        logger.error(f"Chat message error: {e}")
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'error',
            'error': 'Failed to send message'
        })

async def handle_typing(user_id: str, connection_id: str, data: Dict):
    """Handle typing indicator"""
    chat_id = data.get('chat_id')
    is_typing = data.get('is_typing', True)
    
    if chat_id:
        await redis_manager.set_user_typing(user_id, chat_id, is_typing)
        
        # Notify other users in the chat
        await ws_manager.send_to_user(user_id, {
            'type': 'typing_status',
            'user_id': user_id,
            'chat_id': chat_id,
            'is_typing': is_typing
        })

async def handle_notification_read(user_id: str, connection_id: str, data: Dict):
    """Handle marking notification as read"""
    notification_id = data.get('notification_id')
    
    if notification_id:
        await notification_service.mark_as_read(user_id, notification_id)
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'notification_read_ack',
            'notification_id': notification_id
        })

async def handle_presence(user_id: str, connection_id: str, data: Dict):
    """Handle presence updates"""
    status = data.get('status', 'online')
    metadata = data.get('metadata', {})
    
    await redis_manager.set_user_presence(user_id, status, metadata)
    
    # Broadcast presence update to friends/followers
    await ws_manager.broadcast({
        'type': 'presence_update',
        'user_id': user_id,
        'status': status,
        'metadata': metadata
    }, exclude_user_id=user_id)

async def handle_subscribe(user_id: str, connection_id: str, data: Dict):
    """Handle subscription to channels"""
    channels = data.get('channels', [])
    
    for channel in channels:
        await ws_manager.subscribe_to_channel(user_id, connection_id, channel)
    
    await ws_manager.send_to_connection(user_id, connection_id, {
        'type': 'subscribe_ack',
        'channels': channels
    })

async def handle_unsubscribe(user_id: str, connection_id: str, data: Dict):
    """Handle unsubscription from channels"""
    channels = data.get('channels', [])
    
    for channel in channels:
        await ws_manager.unsubscribe_from_channel(user_id, connection_id, channel)
    
    await ws_manager.send_to_connection(user_id, connection_id, {
        'type': 'unsubscribe_ack',
        'channels': channels
    })

async def handle_message_read(user_id: str, connection_id: str, data: Dict):
    """Handle marking messages as read"""
    chat_id = data.get('chat_id')
    message_ids = data.get('message_ids')
    
    if chat_id:
        count = await chat_service.mark_messages_as_read(user_id, chat_id, message_ids)
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'message_read_ack',
            'chat_id': chat_id,
            'count': count
        })

async def handle_get_messages(user_id: str, connection_id: str, data: Dict):
    """Handle getting chat messages"""
    chat_id = data.get('chat_id')
    limit = data.get('limit', 100)
    before = data.get('before')
    
    if not chat_id:
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'error',
            'error': 'Missing chat_id'
        })
        return
    
    try:
        messages = await chat_service.get_messages(user_id, chat_id, limit, before)
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'messages_response',
            'chat_id': chat_id,
            'messages': messages
        })
    except Exception as e:
        await ws_manager.send_to_connection(user_id, connection_id, {
            'type': 'error',
            'error': str(e)
        })

async def handle_get_notifications(user_id: str, connection_id: str, data: Dict):
    """Handle getting notifications"""
    limit = data.get('limit', 50)
    offset = data.get('offset', 0)
    
    notifications = await notification_service.get_notifications(user_id, limit, offset)
    await ws_manager.send_to_connection(user_id, connection_id, {
        'type': 'notifications_response',
        'notifications': notifications,
        'limit': limit,
        'offset': offset
    })

# =============================================
# REST API Endpoints
# =============================================
@app.get("/api/realtime/stats")
async def get_realtime_stats():
    """Get real-time system statistics"""
    return {
        'connections': ws_manager.get_connection_stats(),
        'redis': {
            'connected': redis_manager.client is not None,
            'pool_size': redis_manager.connection_pool.max_connections if redis_manager.connection_pool else 0
        },
        'cassandra': {
            'connected': cassandra_activity.session is not None
        }
    }

@app.post("/api/realtime/notifications")
async def create_notification(
    user_id: str,
    type: str,
    message: str,
    data: Dict = None
):
    """Create a new notification via REST API"""
    notification = await notification_service.create_notification(user_id, type, message, data)
    return notification

@app.get("/api/realtime/notifications/{user_id}")
async def get_user_notifications(
    user_id: str,
    limit: int = 50,
    offset: int = 0
):
    """Get user notifications via REST API"""
    notifications = await notification_service.get_notifications(user_id, limit, offset)
    return {
        'notifications': notifications,
        'limit': limit,
        'offset': offset,
        'total': len(notifications)
    }

@app.post("/api/realtime/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: str
):
    """Mark notification as read via REST API"""
    result = await notification_service.mark_as_read(user_id, notification_id)
    return {'success': result}

@app.post("/api/realtime/notifications/{user_id}/read_all")
async def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read via REST API"""
    count = await notification_service.mark_all_as_read(user_id)
    return {'success': True, 'count': count}

@app.get("/api/realtime/messages/{user_id}/conversations")
async def get_user_conversations(user_id: str):
    """Get user conversations via REST API"""
    conversations = await chat_service.get_conversations(user_id)
    return {'conversations': conversations}

@app.get("/api/realtime/messages/{user_id}/{chat_id}")
async def get_chat_messages(
    user_id: str,
    chat_id: str,
    limit: int = 100,
    before: str = None
):
    """Get chat messages via REST API"""
    messages = await chat_service.get_messages(user_id, chat_id, limit, before)
    return {'messages': messages}

@app.post("/api/realtime/messages")
async def send_message(
    sender_id: str,
    receiver_id: str,
    text: str,
    media_url: str = None
):
    """Send a message via REST API"""
    message = await chat_service.send_message(sender_id, receiver_id, text, media_url)
    return {'message': message}

@app.get("/api/realtime/presence/{user_id}")
async def get_user_presence(user_id: str):
    """Get user presence via REST API"""
    presence = await redis_manager.get_user_presence(user_id)
    return presence or {'status': 'offline', 'last_seen': None}

@app.post("/api/realtime/presence/batch")
async def get_bulk_presence(user_ids: List[str]):
    """Get presence for multiple users via REST API"""
    presence = await redis_manager.get_users_presence(user_ids)
    return {'presence': presence}

# =============================================
# Health Check
# =============================================
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'redis': 'ok',
            'cassandra': 'ok',
            'postgres': 'ok',
            'websocket': 'ok'
        }
    }
    
    # Check Redis
    try:
        await redis_manager.client.ping()
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['services']['redis'] = f'error: {str(e)}'
    
    # Check Cassandra
    try:
        cassandra_activity.session.execute('SELECT now() FROM system.local')
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['services']['cassandra'] = f'error: {str(e)}'
    
    # Check PostgreSQL
    try:
        with SessionLocal() as session:
            session.execute('SELECT 1')
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['services']['postgres'] = f'error: {str(e)}'
    
    return health_status

# =============================================
# Main Entry Point
# =============================================
if __name__ == "__main__":
    uvicorn.run(
        "3_realtime_system:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        workers=4,
        loop="uvloop",
        log_level="info"
  )
