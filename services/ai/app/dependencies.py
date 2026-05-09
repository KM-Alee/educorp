from __future__ import annotations

from collections.abc import AsyncGenerator

from aiokafka import AIOKafkaProducer
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from educorp_common.auth.dependencies import CurrentUser, get_current_user, require_roles
from educorp_common.kafka_json_schema_sr import KafkaJsonSchemaPublisher

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_redis: Redis | None = None
_mongo_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_mongo_db: AsyncIOMotorDatabase | None = None  # type: ignore[type-arg]
_qdrant: QdrantClient | None = None
_kafka_producer: AIOKafkaProducer | None = None
_kafka_schema_publisher: KafkaJsonSchemaPublisher | None = None


def set_engine(engine: AsyncEngine) -> None:
    """Set the database engine (called during lifespan startup)."""
    global _engine, _session_factory
    _engine = engine
    from educorp_common.database.session import create_session_factory

    _session_factory = create_session_factory(engine)


def set_redis(client: Redis) -> None:
    """Set the Redis client (called during lifespan startup)."""
    global _redis
    _redis = client


def set_mongo(client: AsyncIOMotorClient, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
    """Set the MongoDB client and database (called during lifespan startup)."""
    global _mongo_client, _mongo_db
    _mongo_client = client
    _mongo_db = db


def set_qdrant(client: QdrantClient) -> None:
    """Set the Qdrant client (called during lifespan startup)."""
    global _qdrant
    _qdrant = client


def set_kafka_producer(producer: AIOKafkaProducer | None) -> None:
    """Set the Kafka producer (called during lifespan startup)."""
    global _kafka_producer
    _kafka_producer = producer


def set_kafka_schema_publisher(publisher: KafkaJsonSchemaPublisher | None) -> None:
    global _kafka_schema_publisher
    _kafka_schema_publisher = publisher


def get_kafka_schema_publisher() -> KafkaJsonSchemaPublisher | None:
    return _kafka_schema_publisher


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as session:
        yield session


async def get_redis() -> Redis:
    """Provide the Redis client."""
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis


def get_mongo_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """Provide the MongoDB database handle."""
    if _mongo_db is None:
        raise RuntimeError("MongoDB not initialized")
    return _mongo_db


def get_qdrant() -> QdrantClient:
    """Provide the Qdrant client."""
    if _qdrant is None:
        raise RuntimeError("Qdrant not initialized")
    return _qdrant


def get_kafka_producer() -> AIOKafkaProducer | None:
    """Provide the Kafka producer if available."""
    return _kafka_producer


__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_kafka_producer",
    "get_kafka_schema_publisher",
    "get_mongo_db",
    "get_qdrant",
    "get_redis",
    "get_session",
    "require_roles",
    "set_engine",
    "set_kafka_producer",
    "set_kafka_schema_publisher",
    "set_mongo",
    "set_qdrant",
    "set_redis",
]
