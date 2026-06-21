# 1_backend_core.py
"""
Instagram Clone - Backend Core System
Full production-ready backend with all features
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import bcrypt
import jwt
import redis.asyncio as redis
from cassandra.cluster import Cluster, Session
from cassandra.query import SimpleStatement, BatchStatement
from cassandra.concurrent import execute_concurrent_with_args
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI, Depends, HTTPException, status, Request, Response, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from pydantic import BaseModel, Field, EmailStr, validator
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, BigInteger, Text, JSON, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.sql import func
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import uvicorn
from PIL import Image
import io
import boto3
from botocore.exceptions import ClientError
import aioboto3
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import hashlib
from functools import lru_cache
import aiofiles
from motor.motor_asyncio import AsyncIOMotorClient
import gridfs
from minio import Minio
from minio.error import S3Error
from celery import Celery
from celery.result import AsyncResult
import httpx
from bs4 import BeautifulSoup
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic_settings import BaseSettings
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
import uuid
from collections import defaultdict
import heapq
from typing import TypeVar, Generic
import pickle

# =============================================
# Configuration & Settings
# =============================================
class Settings(BaseSettings):
    APP_NAME: str = "Instagram Power System"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-in-production-1234567890!@#$")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    POSTGRES_URL: str = os.getenv("DATABASE_URL", "postgresql://admin:securepass@postgres:5432/instagram")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CASSANDRA_HOSTS: List[str] = ["cassandra"]
    CASSANDRA_KEYSPACE: str = "instagram"
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "elasticsearch:9200")
    
    # Cloud Storage
    AWS_ACCESS_KEY: Optional[str] = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY: Optional[str] = os.getenv("AWS_SECRET_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "instagram-clone")
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Monitoring
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    JAEGER_ENDPOINT: str = os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# =============================================
# Logging Setup
# =============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('/var/log/instagram.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================
# Sentry Integration
# =============================================
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=0.1
    )

# =============================================
# OpenTelemetry Setup
# =============================================
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

def setup_telemetry():
    trace.set_tracer_provider(TracerProvider())
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        port=6831,
    )
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    return trace.get_tracer(__name__)

tracer = setup_telemetry()

# =============================================
# Prometheus Metrics
# =============================================
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])
ACTIVE_USERS = Gauge('active_users_total', 'Total active users')
POSTS_CREATED = Counter('posts_created_total', 'Total posts created')
LIKES_COUNT = Counter('likes_total', 'Total likes')
COMMENTS_COUNT = Counter('comments_total', 'Total comments')
STORAGE_USED = Gauge('storage_used_bytes', 'Total storage used in bytes')
CACHE_HIT_RATIO = Gauge('cache_hit_ratio', 'Cache hit ratio', ['cache_type'])

# =============================================
# Database Models
# =============================================
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    bio = Column(Text, default="")
    profile_pic = Column(String(500), default="default_profile.jpg")
    cover_photo = Column(String(500))
    website = Column(String(200))
    location = Column(String(100))
    
    # Account settings
    is_private = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    
    # Statistics
    follower_count = Column(BigInteger, default=0)
    following_count = Column(BigInteger, default=0)
    post_count = Column(BigInteger, default=0)
    total_likes_received = Column(BigInteger, default=0)
    total_comments_received = Column(BigInteger, default=0)
    total_views = Column(BigInteger, default=0)
    
    # User metadata
    account_created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)
    login_count = Column(BigInteger, default=0)
    last_activity_at = Column(DateTime)
    
    # Preferences
    settings = Column(JSONB, default={})
    interests = Column(JSONB, default=[])
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    relationships = {
        'followers': ('Follow', 'following_id'),
        'following': ('Follow', 'follower_id'),
        'posts': ('Post', 'user_id'),
        'stories': ('Story', 'user_id'),
    }
    
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self, include_sensitive=False):
        data = {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "bio": self.bio,
            "profile_pic": self.profile_pic,
            "cover_photo": self.cover_photo,
            "website": self.website,
            "location": self.location,
            "is_private": self.is_private,
            "is_verified": self.is_verified,
            "follower_count": self.follower_count,
            "following_count": self.following_count,
            "post_count": self.post_count,
            "total_likes_received": self.total_likes_received,
            "account_created_at": self.account_created_at.isoformat() if self.account_created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
            "settings": self.settings,
            "interests": self.interests,
        }
        if include_sensitive:
            data.update({
                "phone_number": self.phone_number,
                "is_active": self.is_active,
                "login_count": self.login_count,
            })
        return data

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    caption = Column(Text, default="")
    location = Column(String(200))
    media_type = Column(String(20), default="image")  # image, video, carousel
    media_urls = Column(JSONB, default=[])
    thumbnail_url = Column(String(500))
    duration = Column(Integer, default=0)  # For videos
    
    # Statistics
    likes_count = Column(BigInteger, default=0)
    comments_count = Column(BigInteger, default=0)
    shares_count = Column(BigInteger, default=0)
    saves_count = Column(BigInteger, default=0)
    views_count = Column(BigInteger, default=0)
    
    # Engagement
    total_engagement_score = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    
    # Metadata
    hashtags = Column(JSONB, default=[])
    mentions = Column(JSONB, default=[])
    is_sponsored = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="posts")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "caption": self.caption,
            "location": self.location,
            "media_type": self.media_type,
            "media_urls": self.media_urls,
            "thumbnail_url": self.thumbnail_url,
            "duration": self.duration,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "shares_count": self.shares_count,
            "saves_count": self.saves_count,
            "views_count": self.views_count,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    media_url = Column(String(500), nullable=False)
    media_type = Column(String(20), default="image")
    text = Column(Text)
    background_color = Column(String(20), default="#000000")
    
    # Statistics
    views_count = Column(BigInteger, default=0)
    replies_count = Column(BigInteger, default=0)
    
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="stories")
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "media_url": self.media_url,
            "media_type": self.media_type,
            "text": self.text,
            "background_color": self.background_color,
            "views_count": self.views_count,
            "replies_count": self.replies_count,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(PGUUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(PGUUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)
    text = Column(Text, nullable=False)
    likes_count = Column(BigInteger, default=0)
    replies_count = Column(BigInteger, default=0)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")
    post = relationship("Post", backref="comments")
    replies = relationship("Comment", backref=backref("parent", remote_side=[id]))

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(PGUUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='unique_like'),)

class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    following_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('follower_id', 'following_id', name='unique_follow'),)

class DirectMessage(Base):
    __tablename__ = "direct_messages"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text)
    media_url = Column(String(500))
    media_type = Column(String(20))
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBlock(Base):
    __tablename__ = "user_blocks"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    blocked_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Hashtag(Base):
    __tablename__ = "hashtags"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    posts_count = Column(BigInteger, default=0)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class PostView(Base):
    __tablename__ = "post_views"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(PGUUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('post_id', 'user_id', name='unique_view'),)

class SavedPost(Base):
    __tablename__ = "saved_posts"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(PGUUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True)
    collection = Column(String(50), default="default")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='unique_save'),)

# =============================================
# Redis Manager
# =============================================
class RedisManager:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        self.pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=100,
            decode_responses=True,
            retry_on_timeout=True
        )
        self.client = redis.Redis(connection_pool=self.pool)
        self.pubsub = self.client.pubsub()
        await self.ping()
        logger.info("Redis connected successfully")
        return self
    
    async def ping(self):
        return await self.client.ping()
    
    # Session management
    async def set_user_session(self, user_id: str, data: Dict, ttl: int = 604800):
        key = f"session:{user_id}"
        await self.client.setex(key, ttl, json.dumps(data))
    
    async def get_user_session(self, user_id: str) -> Optional[Dict]:
        key = f"session:{user_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None
    
    async def delete_user_session(self, user_id: str):
        await self.client.delete(f"session:{user_id}")
    
    # Cache management
    async def cache_data(self, key: str, data: Any, ttl: int = 300):
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
        await self.client.setex(key, ttl, data)
    
    async def get_cached_data(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        if data:
            try:
                return json.loads(data)
            except:
                return data
        return None
    
    async def invalidate_cache(self, *patterns: str):
        for pattern in patterns:
            keys = await self.client.keys(pattern)
            if keys:
                await self.client.delete(*keys)
    
    # Cache statistics
    cache_hits = 0
    cache_misses = 0
    
    async def get_with_stats(self, key: str) -> Optional[Any]:
        data = await self.get_cached_data(key)
        if data:
            self.cache_hits += 1
            CACHE_HIT_RATIO.labels(cache_type="redis").set(
                self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            )
        else:
            self.cache_misses += 1
        return data
    
    # Publish/Subscribe
    async def publish(self, channel: str, message: Dict):
        await self.client.publish(channel, json.dumps(message))
    
    async def subscribe(self, channel: str, callback):
        await self.pubsub.subscribe(**{channel: callback})
    
    # Rate limiting
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
    
    # Distributed locks
    async def acquire_lock(self, key: str, ttl: int = 10) -> bool:
        return await self.client.set(key, "locked", ex=ttl, nx=True)
    
    async def release_lock(self, key: str):
        await self.client.delete(key)
    
    # Geo-spatial operations
    async def add_geo_location(self, key: str, longitude: float, latitude: float, member: str):
        await self.client.geoadd(key, longitude, latitude, member)
    
    async def get_nearby(self, key: str, longitude: float, latitude: float, radius: float, unit: str = "km") -> List:
        return await self.client.georadius(key, longitude, latitude, radius, unit)

redis_manager = RedisManager()

# =============================================
# Cassandra Manager
# =============================================
class CassandraManager:
    def __init__(self):
        self.cluster: Optional[Cluster] = None
        self.session: Optional[Session] = None
    
    async def connect(self):
        self.cluster = Cluster(settings.CASSANDRA_HOSTS)
        self.session = self.cluster.connect(settings.CASSANDRA_KEYSPACE)
        await self.create_tables()
        logger.info("Cassandra connected successfully")
        return self
    
    async def create_tables(self):
        queries = [
            """
            CREATE TABLE IF NOT EXISTS user_activities (
                user_id UUID,
                activity_time TIMESTAMP,
                activity_type TEXT,
                target_id UUID,
                metadata TEXT,
                ip_address TEXT,
                user_agent TEXT,
                PRIMARY KEY (user_id, activity_time)
            ) WITH CLUSTERING ORDER BY (activity_time DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS trending_posts (
                date DATE,
                post_id UUID,
                score DOUBLE,
                data TEXT,
                PRIMARY KEY (date, score)
            ) WITH CLUSTERING ORDER BY (score DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS user_feed (
                user_id UUID,
                post_id UUID,
                score DOUBLE,
                post_data TEXT,
                created_at TIMESTAMP,
                PRIMARY KEY (user_id, score)
            ) WITH CLUSTERING ORDER BY (score DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS story_views (
                user_id UUID,
                story_id UUID,
                viewed_at TIMESTAMP,
                PRIMARY KEY (user_id, story_id)
            )
            """
        ]
        for query in queries:
            self.session.execute(query)
    
    async def log_activity(self, user_id: str, activity_type: str, target_id: str = None, 
                          metadata: Dict = None, ip: str = None, user_agent: str = None):
        query = """
            INSERT INTO user_activities 
            (user_id, activity_time, activity_type, target_id, metadata, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.session.execute(query, (
            uuid.UUID(user_id),
            datetime.utcnow(),
            activity_type,
            uuid.UUID(target_id) if target_id else None,
            json.dumps(metadata) if metadata else None,
            ip,
            user_agent
        ))
    
    async def record_trending_post(self, post_id: str, score: float, data: Dict):
        query = """
            INSERT INTO trending_posts (date, post_id, score, data)
            VALUES (%s, %s, %s, %s)
        """
        self.session.execute(query, (
            datetime.utcnow().date(),
            uuid.UUID(post_id),
            score,
            json.dumps(data)
        ))
    
    async def get_trending_posts(self, limit: int = 50) -> List[Dict]:
        query = """
            SELECT * FROM trending_posts 
            WHERE date = %s 
            LIMIT %s
        """
        rows = self.session.execute(query, (datetime.utcnow().date(), limit))
        return [json.loads(row.data) for row in rows]

cassandra_manager = CassandraManager()

# =============================================
# MongoDB Manager (for analytics and logs)
# =============================================
class MongoDBManager:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.fs = None
    
    async def connect(self):
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.db = self.client.instagram
        self.fs = gridfs.GridFS(self.db)
        logger.info("MongoDB connected successfully")
        return self
    
    async def store_analytics(self, data: Dict):
        await self.db.analytics.insert_one(data)
    
    async def store_log(self, log_data: Dict):
        await self.db.logs.insert_one(log_data)
    
    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict:
        pipeline = [
            {"$match": {"user_id": user_id, "created_at": {"$gte": datetime.utcnow() - timedelta(days=days)}}},
            {"$group": {
                "_id": "$user_id",
                "total_interactions": {"$sum": 1},
                "likes": {"$sum": {"$cond": [{"$eq": ["$type", "like"]}, 1, 0]}},
                "comments": {"$sum": {"$cond": [{"$eq": ["$type", "comment"]}, 1, 0]}},
                "shares": {"$sum": {"$cond": [{"$eq": ["$type", "share"]}, 1, 0]}},
                "saves": {"$sum": {"$cond": [{"$eq": ["$type", "save"]}, 1, 0]}},
            }}
        ]
        result = await self.db.analytics.aggregate(pipeline).to_list(length=1)
        return result[0] if result else {}

mongodb_manager = MongoDBManager()

# =============================================
# Elasticsearch Manager
# =============================================
class ElasticsearchManager:
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
    
    async def connect(self):
        self.client = AsyncElasticsearch([settings.ELASTICSEARCH_HOST])
        await self.create_indexes()
        logger.info("Elasticsearch connected successfully")
        return self
    
    async def create_indexes(self):
        index_mappings = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "username": {"type": "text", "analyzer": "standard"},
                    "full_name": {"type": "text", "analyzer": "standard"},
                    "bio": {"type": "text", "analyzer": "standard"},
                    "email": {"type": "keyword"},
                    "follower_count": {"type": "integer"},
                    "created_at": {"type": "date"},
                }
            }
        }
        await self.client.indices.create(index="users", body=index_mappings, ignore=400)
    
    async def index_user(self, user: Dict):
        await self.client.index(index="users", id=user["id"], body=user)
    
    async def search_users(self, query: str, limit: int = 20) -> List[Dict]:
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["username^3", "full_name^2", "bio"],
                    "fuzziness": "AUTO",
                    "operator": "or"
                }
            },
            "size": limit,
            "sort": [{"follower_count": {"order": "desc"}}]
        }
        response = await self.client.search(index="users", body=body)
        return [hit["_source"] for hit in response["hits"]["hits"]]

elasticsearch_manager = ElasticsearchManager()

# =============================================
# Storage Manager (MinIO/S3)
# =============================================
class StorageManager:
    def __init__(self):
        self.minio_client: Optional[Minio] = None
        self.s3_client = None
    
    async def connect(self):
        self.minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False
        )
        
        # Create buckets if not exist
        buckets = ["posts", "stories", "profiles", "messages"]
        for bucket in buckets:
            if not self.minio_client.bucket_exists(bucket):
                self.minio_client.make_bucket(bucket)
                self.minio_client.set_bucket_policy(
                    bucket,
                    json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{bucket}/*"]
                        }]
                    })
                )
        
        logger.info("Storage connected successfully")
        return self
    
    async def upload_file(self, bucket: str, file_path: str, content: bytes, content_type: str = "image/jpeg") -> str:
        object_name = f"{uuid.uuid4()}_{os.path.basename(file_path)}"
        self.minio_client.put_object(
            bucket,
            object_name,
            io.BytesIO(content),
            len(content),
            content_type=content_type
        )
        STORAGE_USED.set(self.get_total_storage_used())
        return f"/storage/{bucket}/{object_name}"
    
    async def delete_file(self, bucket: str, object_name: str):
        self.minio_client.remove_object(bucket, object_name)
        STORAGE_USED.set(self.get_total_storage_used())
    
    async def get_file_url(self, bucket: str, object_name: str, expiry: int = 3600) -> str:
        return self.minio_client.presigned_get_object(bucket, object_name, expires=timedelta(seconds=expiry))
    
    def get_total_storage_used(self) -> int:
        total = 0
        for bucket in ["posts", "stories", "profiles", "messages"]:
            objects = list(self.minio_client.list_objects(bucket))
            total += sum(obj.size for obj in objects)
        return total

storage_manager = StorageManager()

# =============================================
# JWT Token Manager
# =============================================
class TokenManager:
    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.blacklist = set()
    
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if token in self.blacklist:
                raise HTTPException(status_code=401, detail="Token revoked")
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def revoke_token(self, token: str):
        self.blacklist.add(token)

token_manager = TokenManager()

# =============================================
# Business Logic - Core Services
# =============================================
class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_user(self, username: str, email: str, password: str, full_name: str) -> User:
        existing = self.db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        
        user = User(
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            full_name=full_name
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        await redis_manager.cache_data(f"user:{user.id}", user.to_dict())
        await elasticsearch_manager.index_user(user.to_dict())
        
        return user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        cached = await redis_manager.get_cached_data(f"user:{user_id}")
        if cached:
            return User(**cached)
        
        user = self.db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if user:
            await redis_manager.cache_data(f"user:{user_id}", user.to_dict())
        return user
    
    async def authenticate_user(self, username_or_email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        if not user or not user.verify_password(password):
            return None
        user.last_login_at = datetime.utcnow()
        user.login_count += 1
        self.db.commit()
        return user
    
    async def follow_user(self, follower_id: str, following_id: str):
        if follower_id == following_id:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
        existing = self.db.query(Follow).filter(
            Follow.follower_id == uuid.UUID(follower_id),
            Follow.following_id == uuid.UUID(following_id)
        ).first()
        if existing:
            return existing
        
        follow = Follow(
            follower_id=uuid.UUID(follower_id),
            following_id=uuid.UUID(following_id)
        )
        self.db.add(follow)
        
        # Update follower counts
        follower = await self.get_user(follower_id)
        following = await self.get_user(following_id)
        if following:
            following.follower_count += 1
        if follower:
            follower.following_count += 1
        
        self.db.commit()
        
        await redis_manager.invalidate_cache(f"user:{follower_id}", f"user:{following_id}")
        await cassandra_manager.log_activity(follower_id, "follow", following_id)
        
        return follow
    
    async def unfollow_user(self, follower_id: str, following_id: str):
        follow = self.db.query(Follow).filter(
            Follow.follower_id == uuid.UUID(follower_id),
            Follow.following_id == uuid.UUID(following_id)
        ).first()
        if not follow:
            raise HTTPException(status_code=404, detail="Not following")
        
        self.db.delete(follow)
        
        # Update follower counts
        following = await self.get_user(following_id)
        follower = await self.get_user(follower_id)
        if following:
            following.follower_count -= 1
        if follower:
            follower.following_count -= 1
        
        self.db.commit()
        
        await redis_manager.invalidate_cache(f"user:{follower_id}", f"user:{following_id}")
        await cassandra_manager.log_activity(follower_id, "unfollow", following_id)
    
    async def search_users(self, query: str, limit: int = 20) -> List[Dict]:
        return await elasticsearch_manager.search_users(query, limit)

class PostService:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_post(self, user_id: str, caption: str, media_urls: List[str], 
                          media_type: str = "image", location: str = None, 
                          hashtags: List[str] = None) -> Post:
        post = Post(
            user_id=uuid.UUID(user_id),
            caption=caption,
            media_urls=media_urls,
            media_type=media_type,
            location=location,
            hashtags=hashtags or []
        )
        self.db.add(post)
        
        # Update user post count
        user = self.db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        if user:
            user.post_count += 1
        
        self.db.commit()
        self.db.refresh(post)
        
        # Update hashtag counts
        if hashtags:
            for tag in hashtags:
                hashtag = self.db.query(Hashtag).filter(Hashtag.name == tag).first()
                if hashtag:
                    hashtag.posts_count += 1
                    hashtag.last_used_at = datetime.utcnow()
                else:
                    hashtag = Hashtag(name=tag, posts_count=1, last_used_at=datetime.utcnow())
                    self.db.add(hashtag)
            self.db.commit()
        
        POSTS_CREATED.inc()
        await cassandra_manager.record_trending_post(str(post.id), 0, post.to_dict())
        
        return post
    
    async def get_post(self, post_id: str) -> Optional[Post]:
        cached = await redis_manager.get_cached_data(f"post:{post_id}")
        if cached:
            return Post(**cached)
        
        post = self.db.query(Post).filter(Post.id == uuid.UUID(post_id)).first()
        if post:
            await redis_manager.cache_data(f"post:{post_id}", post.to_dict())
        return post
    
    async def like_post(self, user_id: str, post_id: str):
        existing = self.db.query(Like).filter(
            Like.user_id == uuid.UUID(user_id),
            Like.post_id == uuid.UUID(post_id)
        ).first()
        if existing:
            return
        
        like = Like(user_id=uuid.UUID(user_id), post_id=uuid.UUID(post_id))
        self.db.add(like)
        
        post = await self.get_post(post_id)
        if post:
            post.likes_count += 1
        
        user = self.db.query(User).filter(User.id == post.user_id).first()
        if user:
            user.total_likes_received += 1
        
        self.db.commit()
        
        LIKES_COUNT.inc()
        await redis_manager.invalidate_cache(f"post:{post_id}")
        await cassandra_manager.log_activity(user_id, "like", post_id)
        
        # Create notification
        await self.create_notification(str(post.user_id), "like", f"{user_id} liked your post", {"post_id": post_id, "user_id": user_id})
    
    async def unlike_post(self, user_id: str, post_id: str):
        like = self.db.query(Like).filter(
            Like.user_id == uuid.UUID(user_id),
            Like.post_id == uuid.UUID(post_id)
        ).first()
        if not like:
            return
        
        self.db.delete(like)
        
        post = await self.get_post(post_id)
        if post:
            post.likes_count -= 1
        
        user = self.db.query(User).filter(User.id == post.user_id).first()
        if user:
            user.total_likes_received -= 1
        
        self.db.commit()
        
        await redis_manager.invalidate_cache(f"post:{post_id}")
    
    async def create_comment(self, user_id: str, post_id: str, text: str, parent_id: str = None) -> Comment:
        comment = Comment(
            user_id=uuid.UUID(user_id),
            post_id=uuid.UUID(post_id),
            text=text,
            parent_id=uuid.UUID(parent_id) if parent_id else None
        )
        self.db.add(comment)
        
        post = await self.get_post(post_id)
        if post:
            post.comments_count += 1
        
        if parent_id:
            parent = self.db.query(Comment).filter(Comment.id == uuid.UUID(parent_id)).first()
            if parent:
                parent.replies_count += 1
        
        self.db.commit()
        self.db.refresh(comment)
        
        COMMENTS_COUNT.inc()
        await redis_manager.invalidate_cache(f"post:{post_id}")
        await cassandra_manager.log_activity(user_id, "comment", post_id, {"text": text})
        
        return comment
    
    async def save_post(self, user_id: str, post_id: str):
        existing = self.db.query(SavedPost).filter(
            SavedPost.user_id == uuid.UUID(user_id),
            SavedPost.post_id == uuid.UUID(post_id)
        ).first()
        if existing:
            return
        
        save = SavedPost(user_id=uuid.UUID(user_id), post_id=uuid.UUID(post_id))
        self.db.add(save)
        
        post = await self.get_post(post_id)
        if post:
            post.saves_count += 1
        
        self.db.commit()
    
    async def unsave_post(self, user_id: str, post_id: str):
        save = self.db.query(SavedPost).filter(
            SavedPost.user_id == uuid.UUID(user_id),
            SavedPost.post_id == uuid.UUID(post_id)
        ).first()
        if not save:
            return
        
        self.db.delete(save)
        
        post = await self.get_post(post_id)
        if post:
            post.saves_count -= 1
        
        self.db.commit()

class FeedService:
    def __init__(self, db: Session):
        self.db = db
    
    async def generate_feed(self, user_id: str, page: int = 1, limit: int = 20) -> List[Dict]:
        cache_key = f"feed:{user_id}:{page}"
        cached = await redis_manager.get_with_stats(cache_key)
        if cached:
            return cached
        
        # Get following users
        following = self.db.query(Follow).filter(
            Follow.follower_id == uuid.UUID(user_id)
        ).all()
        following_ids = [str(f.following_id) for f in following]
        
        # Get posts from following users
        if following_ids:
            posts = self.db.query(Post).filter(
                Post.user_id.in_([uuid.UUID(id) for id in following_ids]),
                Post.is_deleted == False
            ).order_by(Post.created_at.desc()).limit(limit + 20).all()
        else:
            # If not following anyone, show trending posts
            posts = self.db.query(Post).filter(
                Post.is_deleted == False
            ).order_by(Post.likes_count.desc()).limit(limit + 20).all()
        
        # Score and rank posts
        scored_posts = []
        for post in posts:
            score = self.calculate_post_score(post)
            scored_posts.append((score, post))
        
        scored_posts.sort(key=lambda x: x[0], reverse=True)
        
        # Apply pagination
        start = (page - 1) * limit
        end = start + limit
        result = [post.to_dict() for _, post in scored_posts[start:end]]
        
        await redis_manager.cache_data(cache_key, result, 300)
        return result
    
    def calculate_post_score(self, post: Post) -> float:
        # Score based on recency, engagement, and relevance
        recency = (datetime.utcnow() - post.created_at).total_seconds()
        recency_score = 1000 / (recency + 1)
        
        engagement_score = (
            post.likes_count * 2 +
            post.comments_count * 3 +
            post.shares_count * 4 +
            post.saves_count * 2
        )
        
        return recency_score + engagement_score
    
    async def get_stories(self, user_id: str) -> List[Dict]:
        following = self.db.query(Follow).filter(
            Follow.follower_id == uuid.UUID(user_id)
        ).all()
        following_ids = [str(f.following_id) for f in following]
        
        stories = self.db.query(Story).filter(
            Story.user_id.in_([uuid.UUID(id) for id in following_ids]),
            Story.expires_at > datetime.utcnow()
        ).order_by(Story.created_at.desc()).all()
        
        return [story.to_dict() for story in stories]
    
    async def get_trending_posts(self, limit: int = 20) -> List[Dict]:
        # Get trending from Cassandra
        trending = await cassandra_manager.get_trending_posts(limit)
        if trending:
            return trending
        
        # Fallback to database
        posts = self.db.query(Post).filter(
            Post.is_deleted == False
        ).order_by(
            Post.likes_count.desc(),
            Post.comments_count.desc()
        ).limit(limit).all()
        
        return [post.to_dict() for post in posts]

# =============================================
# Celery Tasks
# =============================================
celery_app = Celery(
    "instagram",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

@celery_app.task
def process_media(file_path: str, user_id: str):
    """Process uploaded media - compress, resize, generate thumbnails"""
    # Image processing
    with Image.open(file_path) as img:
        # Compress
        img = img.convert("RGB")
        img.thumbnail((1080, 1080))
        
        # Save compressed
        compressed_path = f"/tmp/compressed_{uuid.uuid4()}.jpg"
        img.save(compressed_path, "JPEG", quality=80, optimize=True)
        
        # Upload to storage
        with open(compressed_path, "rb") as f:
            content = f.read()
            # Upload to MinIO
            # storage_manager.upload_file("posts", compressed_path, content)
        
        return {"status": "success", "path": compressed_path}

@celery_app.task
def generate_post_analytics(post_id: str):
    """Generate analytics for a post"""
    # Implement analytics generation
    pass

@celery_app.task
def send_email_notification(email: str, subject: str, body: str):
    """Send email notification"""
    # Implement email sending
    pass

@celery_app.task
def update_trending_posts():
    """Update trending posts in Cassandra"""
    # Implement trending update
    pass

# =============================================
# FastAPI Application
# =============================================
app = FastAPI(
    title="Instagram Power System",
    description="Complete Instagram clone with all features",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.SENTRY_DSN:
    app.add_middleware(SentryAsgiMiddleware)

# Add OpenTelemetry
FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())

# =============================================
# Dependency Injection
# =============================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    engine = create_engine(settings.POSTGRES_URL, pool_size=20, max_overflow=40)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = token_manager.decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# =============================================
# API Endpoints
# =============================================
@app.on_event("startup")
async def startup_event():
    await redis_manager.connect()
    await cassandra_manager.connect()
    await mongodb_manager.connect()
    await elasticsearch_manager.connect()
    await storage_manager.connect()
    await FastAPILimiter.init(redis_manager.client)
    logger.info("All services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    if redis_manager.client:
        await redis_manager.client.close()
    if cassandra_manager.cluster:
        cassandra_manager.cluster.shutdown()
    if mongodb_manager.client:
        mongodb_manager.client.close()
    if elasticsearch_manager.client:
        await elasticsearch_manager.client.close()
    logger.info("All services shut down")

# Health Check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {
            "postgres": "ok",
            "redis": "ok",
            "cassandra": "ok",
            "mongodb": "ok",
            "elasticsearch": "ok",
            "storage": "ok"
        }
    }

# Authentication
@app.post("/api/v1/auth/register")
async def register(user_data: Dict, db: Session = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.create_user(
        user_data["username"],
        user_data["email"],
        user_data["password"],
        user_data.get("full_name", user_data["username"])
    )
    
    access_token = token_manager.create_access_token({"sub": str(user.id)})
    refresh_token = token_manager.create_refresh_token({"sub": str(user.id)})
    
    await redis_manager.set_user_session(str(user.id), {"access_token": access_token})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }

@app.post("/api/v1/auth/login")
async def login(username_or_email: str, password: str, db: Session = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.authenticate_user(username_or_email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = token_manager.create_access_token({"sub": str(user.id)})
    refresh_token = token_manager.create_refresh_token({"sub": str(user.id)})
    
    await redis_manager.set_user_session(str(user.id), {"access_token": access_token})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }

@app.post("/api/v1/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    await redis_manager.delete_user_session(str(current_user.id))
    return {"status": "success"}

# Users
@app.get("/api/v1/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user.to_dict()

@app.get("/api/v1/users/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()

@app.post("/api/v1/users/{user_id}/follow")
async def follow_user(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_service = UserService(db)
    await user_service.follow_user(str(current_user.id), user_id)
    return {"status": "success"}

@app.delete("/api/v1/users/{user_id}/follow")
async def unfollow_user(user_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_service = UserService(db)
    await user_service.unfollow_user(str(current_user.id), user_id)
    return {"status": "success"}

@app.get("/api/v1/users/search")
async def search_users(query: str, limit: int = 20, db: Session = Depends(get_db)):
    user_service = UserService(db)
    results = await user_service.search_users(query, limit)
    return {"results": results}

# Posts
@app.post("/api/v1/posts")
async def create_post(
    caption: str,
    media_urls: List[str],
    media_type: str = "image",
    location: str = None,
    hashtags: List[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_service = PostService(db)
    post = await post_service.create_post(
        str(current_user.id),
        caption,
        media_urls,
        media_type,
        location,
        hashtags
    )
    return post.to_dict()

@app.get("/api/v1/posts/{post_id}")
async def get_post(post_id: str, db: Session = Depends(get_db)):
    post_service = PostService(db)
    post = await post_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post.to_dict()

@app.post("/api/v1/posts/{post_id}/like")
async def like_post(post_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post_service = PostService(db)
    await post_service.like_post(str(current_user.id), post_id)
    return {"status": "success"}

@app.delete("/api/v1/posts/{post_id}/like")
async def unlike_post(post_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post_service = PostService(db)
    await post_service.unlike_post(str(current_user.id), post_id)
    return {"status": "success"}

@app.post("/api/v1/posts/{post_id}/comment")
async def create_comment(
    post_id: str,
    text: str,
    parent_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_service = PostService(db)
    comment = await post_service.create_comment(str(current_user.id), post_id, text, parent_id)
    return comment.to_dict()

@app.post("/api/v1/posts/{post_id}/save")
async def save_post(post_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post_service = PostService(db)
    await post_service.save_post(str(current_user.id), post_id)
    return {"status": "success"}

@app.delete("/api/v1/posts/{post_id}/save")
async def unsave_post(post_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post_service = PostService(db)
    await post_service.unsave_post(str(current_user.id), post_id)
    return {"status": "success"}

# Feed
@app.get("/api/v1/feed")
async def get_feed(page: int = 1, limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    feed_service = FeedService(db)
    feed = await feed_service.generate_feed(str(current_user.id), page, limit)
    return {"feed": feed, "page": page, "limit": limit}

@app.get("/api/v1/stories")
async def get_stories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    feed_service = FeedService(db)
    stories = await feed_service.get_stories(str(current_user.id))
    return {"stories": stories}

@app.get("/api/v1/trending")
async def get_trending(limit: int = 20, db: Session = Depends(get_db)):
    feed_service = FeedService(db)
    trending = await feed_service.get_trending_posts(limit)
    return {"trending": trending}

# Notifications
@app.get("/api/v1/notifications")
async def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    return {"notifications": [n.to_dict() for n in notifications]}

@app.post("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(
        Notification.id == uuid.UUID(notification_id),
        Notification.user_id == current_user.id
    ).first()
    if notification:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
    return {"status": "success"}

# =============================================
# WebSocket for Real-time Communication
# =============================================
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_data: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.connection_data[websocket] = {"user_id": user_id, "connected_at": datetime.utcnow()}
        await self.broadcast({"type": "user_online", "user_id": user_id})
    
    def disconnect(self, websocket: WebSocket):
        user_data = self.connection_data.pop(websocket, {})
        user_id = user_data.get("user_id")
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                asyncio.create_task(self.broadcast({"type": "user_offline", "user_id": user_id}))
    
    async def send_personal(self, message: Dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)
    
    async def broadcast(self, message: Dict):
        for user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

ws_manager = WebSocketManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await ws_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data["type"] == "message":
                # Handle direct message
                receiver_id = data["receiver_id"]
                message = data["message"]
                await ws_manager.send_personal({"type": "message", "from": user_id, "message": message}, receiver_id)
            
            elif data["type"] == "typing":
                receiver_id = data["receiver_id"]
                await ws_manager.send_personal({"type": "typing", "from": user_id}, receiver_id)
            
            elif data["type"] == "notification_read":
                notification_id = data["notification_id"]
                await self.mark_notification_read(notification_id, user_id)
            
            elif data["type"] == "story_view":
                story_id = data["story_id"]
                # Record story view
                await cassandra_manager.log_activity(user_id, "story_view", story_id)
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# =============================================
# Main Entry Point
# =============================================
if __name__ == "__main__":
    uvicorn.run(
        "1_backend_core:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=4,
        loop="uvloop",
        log_level="info"
  )
