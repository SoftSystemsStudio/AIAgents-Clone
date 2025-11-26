"""
Message Queue Implementation using Redis.

Provides pub/sub and task queue capabilities for agent communication.
"""

import asyncio
import json
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from src.domain.exceptions import MessageQueueError
from src.domain.interfaces import IMessageQueue


class RedisMessageQueue(IMessageQueue):
    """
    Redis-based message queue implementation.
    
    Uses Redis pub/sub for real-time messaging and Redis lists for task queues.
    
    RISK: Redis is in-memory, so messages are lost on crash.
    For critical workflows, consider persistent message queues (RabbitMQ, Kafka).
    
    TODO: Add message acknowledgment and retry logic
    TODO: Add dead letter queue support
    TODO: Add message TTL configuration
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        decode_responses: bool = True,
        url: Optional[str] = None,
        ssl: bool = False,
    ):
        """
        Initialize Redis message queue.
        
        Args:
            host: Redis host
            port: Redis port
            password: Optional password
            db: Database number
            decode_responses: Decode responses to strings
        """
        try:
            import redis.asyncio as aioredis
        except ImportError:
            raise ImportError(
                "Redis package not installed. Install with: pip install redis"
            )

        if url:
            self.redis = aioredis.from_url(
                url,
                ssl=ssl,
                decode_responses=decode_responses,
            )
        else:
            self.redis = aioredis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=decode_responses,
                ssl=ssl,
            )
        self._pubsub = None
        self._subscriptions: Dict[str, asyncio.Task] = {}

    @classmethod
    def from_config(cls, redis_config) -> "RedisMessageQueue":
        """Build a message queue from RedisConfig (supports Upstash URLs)."""

        kwargs = redis_config.connection_kwargs()
        return cls(
            host=kwargs.get("host", "localhost"),
            port=kwargs.get("port", 6379),
            password=kwargs.get("password"),
            db=kwargs.get("db", 0),
            decode_responses=kwargs.get("decode_responses", True),
            url=kwargs.get("url"),
            ssl=kwargs.get("ssl", False),
        )

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        priority: int = 0,
    ) -> str:
        """
        Publish a message to a topic.
        
        Messages are serialized to JSON.
        """
        try:
            message_id = str(uuid4())
            payload = {
                "id": message_id,
                "priority": priority,
                "data": message,
            }

            # Use Redis pub/sub for broadcast
            serialized = json.dumps(payload)
            await self.redis.publish(topic, serialized)

            # Also push to list for task queue pattern
            await self.redis.lpush(f"queue:{topic}", serialized)

            return message_id

        except Exception as e:
            raise MessageQueueError(f"Failed to publish message: {str(e)}") from e

    async def subscribe(
        self,
        topic: str,
        callback: Callable[[Dict[str, Any]], Any],
    ) -> str:
        """
        Subscribe to a topic with a callback.
        
        The callback is invoked for each message received.
        Returns a subscription ID that can be used to unsubscribe.
        """
        try:
            subscription_id = str(uuid4())

            # Create pubsub instance if not exists
            if self._pubsub is None:
                self._pubsub = self.redis.pubsub()

            # Subscribe to topic
            await self._pubsub.subscribe(topic)

            # Create listener task
            async def listener():
                """Background task that listens for messages."""
                async for message in self._pubsub.listen():
                    if message["type"] == "message":
                        try:
                            payload = json.loads(message["data"])
                            # Invoke callback
                            result = callback(payload)
                            # Handle async callbacks
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            # Log error but continue listening
                            print(f"Error in subscription callback: {e}")

            # Start listener task
            task = asyncio.create_task(listener())
            self._subscriptions[subscription_id] = task

            return subscription_id

        except Exception as e:
            raise MessageQueueError(f"Failed to subscribe: {str(e)}") from e

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a topic."""
        try:
            if subscription_id in self._subscriptions:
                task = self._subscriptions[subscription_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._subscriptions[subscription_id]

        except Exception as e:
            raise MessageQueueError(f"Failed to unsubscribe: {str(e)}") from e

    async def get_message(
        self,
        topic: str,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a message from a queue (blocking with timeout).
        
        Uses Redis BRPOP for blocking pop with timeout.
        Good for task queue pattern.
        """
        try:
            queue_name = f"queue:{topic}"

            if timeout is None:
                timeout = 0  # Block indefinitely

            # BRPOP returns (key, value) or None on timeout
            result = await self.redis.brpop(queue_name, timeout=int(timeout))

            if result is None:
                return None

            _, message_data = result
            payload = json.loads(message_data)
            return payload

        except Exception as e:
            raise MessageQueueError(f"Failed to get message: {str(e)}") from e

    async def close(self) -> None:
        """Close all connections and cancel subscriptions."""
        # Cancel all subscription tasks
        for task in self._subscriptions.values():
            task.cancel()

        # Wait for cancellation
        if self._subscriptions:
            await asyncio.gather(
                *self._subscriptions.values(),
                return_exceptions=True,
            )

        # Close pubsub
        if self._pubsub:
            await self._pubsub.close()

        # Close Redis connection
        await self.redis.close()
