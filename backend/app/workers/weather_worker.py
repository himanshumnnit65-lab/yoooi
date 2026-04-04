import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.weather_agent import WeatherAgent
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
    """Run the weather worker"""
    logger.info("🌤️ Initializing Weather Worker...")
    
    try:
        # Create weather agent instance
        from app.messaging.redis_client import get_redis_client
        
        redis_client = get_redis_client()
        
        agent = WeatherAgent(
            name="Sky Gazer",
            role="Weather Forecaster",
            expertise="Providing accurate weather forecasts",
            agent_type=AgentType.WEATHER,
            redis_client=redis_client
        )
        
        # Run worker
        await run_worker(agent, AgentType.WEATHER)
        
    except Exception as e:
        logger.error(f"Weather worker failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())