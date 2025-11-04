"""Demo Agent module entry point.

Allows running demo_agent as a module: python -m demo_agent

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

import uvicorn

from demo_agent.config.settings import config
from demo_agent.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.DEMO_AGENT_HOST,
        port=config.DEMO_AGENT_PORT,
        reload=config.DEBUG_MODE,
        log_level=config.LOG_LEVEL.lower(),
    )
