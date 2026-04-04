import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.maps_agent import MapsAgent
from app.messaging.protocols import AgentType
from app.workers.base_worker import run_worker
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Run the maps worker"""
    logger.info("🗺️ Initializing Maps Worker...")
    
    try:
        # Create maps agent instance
        from app.messaging.redis_client import get_redis_client
        
        redis_client = get_redis_client()
        
        agent = MapsAgent(
            name="Trailblazer",
            role="Route Planning Expert",
            expertise="Navigation and route optimization",
            agent_type=AgentType.MAPS,
            redis_client=redis_client
        )
        
        # Run worker
        await run_worker(agent, AgentType.MAPS)
        
    except Exception as e:
        logger.error(f"Maps worker failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())