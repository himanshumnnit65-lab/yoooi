import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.agents.budget_agent import EnhancedBudgetAgent
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
    """Run the budget worker"""
    logger.info("💰 Initializing Budget Worker...")
    
    try:
        # Create budget agent instance
        from app.messaging.redis_client import get_redis_client
        
        redis_client = get_redis_client()
        
        agent = EnhancedBudgetAgent(
            name="Quartermaster",
            role="Budget Planning Specialist",
            expertise="Cost estimation and financial planning",
            agent_type=AgentType.BUDGET,
            redis_client=redis_client
        )
        
        # Run worker
        await run_worker(agent, AgentType.BUDGET)
        
    except Exception as e:
        logger.error(f"Budget worker failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())