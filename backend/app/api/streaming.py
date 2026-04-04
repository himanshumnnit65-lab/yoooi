# ============================================
# BACKEND: app/api/streaming.py (FIXED)
# ============================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json
import logging
from app.messaging.redis_client import get_redis_client, RedisChannels

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stream/{session_id}")
async def stream_session_updates(session_id: str):
    """
    Server-Sent Events endpoint for real-time streaming updates
    
    Frontend connects to this endpoint to receive updates as agents complete
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = get_redis_client()
        message_queue = asyncio.Queue()
        subscription_id = None
        
        try:
            # Connect to Redis
            await redis_client.connect()
            logger.info(f"📡 SSE: Client connected for session {session_id}")
            
            # Handler to receive messages from Redis
            async def message_handler(data: dict):
                await message_queue.put(data)
            
            # Subscribe to the streaming channel
            channel = RedisChannels.get_streaming_channel(session_id)
            subscription_id = await redis_client.subscribe(channel, message_handler)
            logger.info(f"📡 SSE: Subscribed to channel {channel}")
            
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            # Stream messages as they arrive
            while True:
                try:
                    # Wait for message with timeout to send keep-alive
                    data = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    
                    # Format as SSE and send to frontend
                    message = f"data: {json.dumps(data)}\n\n"
                    yield message
                    
                    logger.debug(f"📡 SSE: Sent update from {data.get('agent', 'unknown')}")
                    
                    # Check if workflow is complete
                    if data.get('type') == 'workflow_complete':
                        logger.info(f"📡 SSE: Workflow complete for session {session_id}")
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        break
                        
                except asyncio.TimeoutError:
                    # Send keep-alive comment to prevent timeout
                    yield ": keep-alive\n\n"
                    continue
                    
        except asyncio.CancelledError:
            logger.info(f"📡 SSE: Client disconnected from session {session_id}")
            raise
            
        except Exception as e:
            logger.error(f"📡 SSE: Error in stream for session {session_id}: {str(e)}")
            error_message = {
                'type': 'error',
                'error': str(e),
                'session_id': session_id
            }
            yield f"data: {json.dumps(error_message)}\n\n"
            
        finally:
            # Cleanup
            if subscription_id:
                await redis_client.unsubscribe(subscription_id)
                logger.info(f"📡 SSE: Unsubscribed from session {session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/stream/{session_id}/status")
async def get_stream_status(session_id: str):
    """
    Check if there are active subscribers for a session
    """
    redis_client = get_redis_client()
    
    try:
        await redis_client.connect()
        channel = RedisChannels.get_streaming_channel(session_id)
        
        # Publish a test message to see how many receivers
        test_msg = {"type": "ping", "timestamp": "test"}
        receivers = await redis_client.publish(channel, test_msg)
        
        return {
            "session_id": session_id,
            "active_subscribers": receivers,
            "channel": channel
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await redis_client.disconnect()