import redis.asyncio as redis
from redis.asyncio import Redis
from typing import Optional, Dict, Any, Callable
import json
import logging
from contextlib import asynccontextmanager
import asyncio
from app.config.settings import settings


logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client manager for Upstash Redis"""
    
    def __init__(self, redis_url: str):
        """
        Initialize Redis client
        
        Args:
            redis_url: Upstash Redis URL (format: redis://default:password@endpoint:port)
        """
        self.redis_url = redis_url
        self._client: Optional[Redis] = None
        self._pubsub_client: Optional[Redis] = None
        self._subscribers: Dict[str, asyncio.Task] = {}
        
    async def connect(self):
        """Establish connection to Redis"""
        if self._client is None:
            try:
                self._client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                    health_check_interval=30
                )
                
                # Separate client for pub/sub
                self._pubsub_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                
                await self._client.ping()
                logger.info("✅ Connected to Upstash Redis")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis: {str(e)}")
                raise
    
    async def disconnect(self):
        """Close Redis connections"""
        # Cancel all subscribers
        for task in self._subscribers.values():
            task.cancel()
        
        if self._client:
            await self._client.close()
            logger.info("Redis client closed")
        
        if self._pubsub_client:
            await self._pubsub_client.close()
            logger.info("Redis pub/sub client closed")
    
    @property
    def client(self) -> Redis:
        """Get Redis client instance"""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client
    
    # ==================== KEY-VALUE OPERATIONS ====================
    
    async def set_state(self, session_id: str, state: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Store state in Redis with TTL
        
        Args:
            session_id: Unique session identifier
            state: State dictionary to store
            ttl: Time to live in seconds (default 1 hour)
        """
        try:
            key = f"state:{session_id}"
            serialized = json.dumps(state)
            await self.client.setex(key, ttl, serialized)
            logger.debug(f"State saved for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save state: {str(e)}")
            return False
    
    async def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve state from Redis
        
        Args:
            session_id: Unique session identifier
        """
        try:
            key = f"state:{session_id}"
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get state: {str(e)}")
            return None
    
    async def delete_state(self, session_id: str) -> bool:
        """Delete state from Redis"""
        try:
            key = f"state:{session_id}"
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete state: {str(e)}")
            return False
    
    async def extend_state_ttl(self, session_id: str, ttl: int = 3600) -> bool:
        """Extend TTL for existing state"""
        try:
            key = f"state:{session_id}"
            await self.client.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to extend TTL: {str(e)}")
            return False
    
    # ==================== PUB/SUB OPERATIONS ====================
    
    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """
        Publish message to a channel
        
        Args:
            channel: Channel name
            message: Message dictionary to publish
            
        Returns:
            Number of subscribers that received the message
        """
        try:
            serialized = json.dumps(message,default=str)
            receivers = await self.client.publish(channel, serialized)
            logger.debug(f"Published to {channel}: {receivers} receivers")
            return receivers
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {str(e)}")
            raise
    
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[Dict[str, Any]], None],
        error_handler: Optional[Callable[[Exception], None]] = None
    ) -> str:
        """
        Subscribe to a channel with message handler
        
        Args:
            channel: Channel name to subscribe to
            handler: Async function to handle received messages
            error_handler: Optional async function to handle errors
            
        Returns:
            Subscription ID
        """
        subscription_id = f"{channel}:{id(handler)}"
        
        async def _subscribe_loop():
            try:
                pubsub = self._pubsub_client.pubsub()
                await pubsub.subscribe(channel)
                logger.info(f"📡 Subscribed to channel: {channel}")
                
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            await handler(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode message: {str(e)}")
                            if error_handler:
                                await error_handler(e)
                        except Exception as e:
                            logger.error(f"Handler error: {str(e)}")
                            if error_handler:
                                await error_handler(e)
            except asyncio.CancelledError:
                logger.info(f"Subscription cancelled: {channel}")
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception as e:
                logger.error(f"Subscription error on {channel}: {str(e)}")
                if error_handler:
                    await error_handler(e)
        
        # Create background task for subscription
        task = asyncio.create_task(_subscribe_loop())
        self._subscribers[subscription_id] = task
        
        return subscription_id
    
    async def unsubscribe(self, subscription_id: str):
        """Cancel a subscription by ID"""
        if subscription_id in self._subscribers:
            self._subscribers[subscription_id].cancel()
            del self._subscribers[subscription_id]
            logger.info(f"Unsubscribed: {subscription_id}")
    
    async def publish_and_wait(
        self,
        request_channel: str,
        response_channel: str,
        message: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Publish a message and wait for response on another channel
        
        Args:
            request_channel: Channel to send request
            response_channel: Channel to listen for response
            message: Request message
            timeout: Timeout in seconds
            
        Returns:
            Response message or None if timeout
        """
        response_future = asyncio.Future()
        
        async def response_handler(data: Dict[str, Any]):
            if not response_future.done():
                response_future.set_result(data)
        
        # Subscribe to response channel
        subscription_id = await self.subscribe(response_channel, response_handler)
        
        try:
            # Publish request
            await self.publish(request_channel, message)
            
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response on {response_channel}")
            return None
        finally:
            # Cleanup subscription
            await self.unsubscribe(subscription_id)
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    async def get_info(self) -> Dict[str, Any]:
        """Get Redis server info"""
        try:
            info = await self.client.info()
            return {
                "connected": True,
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_days": info.get("uptime_in_days")
            }
        except Exception as e:
            logger.error(f"Failed to get info: {str(e)}")
            return {"connected": False, "error": str(e)}


# ==================== GLOBAL INSTANCE ====================

# Singleton instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    global _redis_client
    
    if _redis_client is None:
        redis_url = getattr(settings, 'redis_url', None)
        if not redis_url:
            raise ValueError("Redis URL not configured in settings")
        
        _redis_client = RedisClient(redis_url)
    
    return _redis_client


@asynccontextmanager
async def get_redis_connection():
    """Context manager for Redis connection"""
    client = get_redis_client()
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()


# ==================== CHANNEL CONSTANTS ====================

class RedisChannels:
    """Redis channel name constants"""
    
    # Request channels (Orchestrator -> Agents)
    WEATHER_REQUEST = "agent:weather:request"
    EVENTS_REQUEST = "agent:events:request"
    MAPS_REQUEST = "agent:maps:request"
    BUDGET_REQUEST = "agent:budget:request"
    ITINERARY_REQUEST = "agent:itinerary:request"
    
    # Response channels (Agents -> Orchestrator)
    WEATHER_RESPONSE = "agent:weather:response:{session_id}"
    EVENTS_RESPONSE = "agent:events:response:{session_id}"
    MAPS_RESPONSE = "agent:maps:response:{session_id}"
    BUDGET_RESPONSE = "agent:budget:response:{session_id}"
    ITINERARY_RESPONSE = "agent:itinerary:response:{session_id}"
    
    # Control channels
    HEALTH_CHECK = "agent:health"
    CANCEL = "agent:cancel:{session_id}"
    STREAMING_UPDATE = "streaming:update:{session_id}"
    
    @staticmethod
    def get_response_channel(agent_name: str, session_id: str) -> str:
        """Get response channel for specific agent and session"""
        return f"agent:{agent_name}:response:{session_id}"
    
    @staticmethod
    def get_request_channel(agent_name: str) -> str:
        """Get request channel for specific agent"""
        return f"agent:{agent_name}:request"
    
    @staticmethod
    def get_streaming_channel(session_id: str) -> str:
        """Get streaming update channel for session"""
        return f"streaming:update:{session_id}"