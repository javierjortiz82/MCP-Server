"""Demo Agent module entry point.

Allows running demo_agent as a module: python -m demo_agent

Security:
    Configures Uvicorn with proxy header support for secure IP extraction.
    Only enable proxy_headers if running behind a trusted proxy/load balancer.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 2.0.0
"""

import uvicorn

from demo_agent.config.settings import config
from demo_agent.logger import logger
from demo_agent.main import app

if __name__ == "__main__":
    # Parse forwarded_allow_ips from config
    forwarded_allow_ips = None
    if config.ENABLE_PROXY_HEADERS and config.TRUSTED_PROXIES:
        # Use specific trusted proxy IPs for security
        forwarded_allow_ips = config.TRUSTED_PROXIES
        logger.info(f"Proxy headers enabled with trusted proxies: {forwarded_allow_ips}")
    elif config.ENABLE_PROXY_HEADERS:
        # WARNING: Using '*' trusts ALL proxies - only for development!
        forwarded_allow_ips = "*"
        logger.warning(
            "Proxy headers enabled with forwarded_allow_ips='*'. "
            "This is INSECURE for production! Set TRUSTED_PROXIES in .env"
        )
    else:
        logger.info("Proxy headers disabled - using direct connection IPs only")

    uvicorn.run(
        app,
        host=config.DEMO_AGENT_HOST,
        port=config.DEMO_AGENT_PORT,
        reload=config.DEBUG_MODE,
        log_level=config.LOG_LEVEL.lower(),
        # Security: Enable proxy header support
        proxy_headers=config.ENABLE_PROXY_HEADERS,
        forwarded_allow_ips=forwarded_allow_ips,
    )
