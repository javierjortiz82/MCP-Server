"""Routes Package for Demo Agent.

Modular route organization for FastAPI endpoints.

Author: Lab01-MCP Team
Created: 2025-11-10
Version: 1.0.0
"""

from demo_agent.routes.health import router as health_router
from demo_agent.routes.auth import router as auth_router
from demo_agent.routes.webhooks import router as webhooks_router
from demo_agent.routes.demo import router as demo_router
from demo_agent.routes.forms import router as forms_router

__all__ = [
    "health_router",
    "auth_router",
    "webhooks_router",
    "demo_router",
    "forms_router",
]
