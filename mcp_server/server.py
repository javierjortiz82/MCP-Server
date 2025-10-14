"""
Official MCP-Compliant Server Implementation
Follows Anthropic's official MCP Python SDK specification exactly.
Uses official protocol version, capabilities, and types from mcp.types module.
"""

from mcp.server.fastmcp import FastMCP
from mcp.types import DEFAULT_NEGOTIATED_VERSION, LATEST_PROTOCOL_VERSION

import utils.db as db
from mcp_handlers import (
    booking_handlers,
    product_handlers,
    prompt_handlers,
    resource_handlers,
)
from utils.logger import setup_logging

# Setup logger for MCP server
logger = setup_logging("mcp_server")

# Create MCP server with official configuration
mcp = FastMCP(
    name="Product Search MCP Server",
    instructions=(
        "AI-powered product search and inventory management server with "
        "fuzzy search, semantic search, and database operations."
    ),
    debug=True,
    log_level="INFO",
    stateless_http=True,  # Enable stateless HTTP for proper remote client support
)

# Initialize handlers with MCP instance
product_handlers.init_product_handlers(mcp)
booking_handlers.init_booking_handlers(mcp)  # Register booking tools
resource_handlers.init_resource_handlers(mcp)
prompt_handlers.init_prompt_handlers(mcp)


# ============================================================================
# Server Lifecycle with Official MCP Patterns
# ============================================================================


async def startup():
    """Initialize database and other resources on server startup."""
    try:
        logger.info("Starting MCP server initialization...")
        db.init_db()
        logger.info("Database initialized successfully for official MCP server")
        logger.info("Server startup completed successfully")
    except Exception as e:
        logger.exception("Critical error during server initialization: %s", e)
        logger.error("Server startup failed - shutting down")
        raise


async def shutdown():
    """Clean up resources on server shutdown."""
    logger.info("Official MCP server shutting down...")


# Configure server lifecycle using official pattern
# Note: FastMCP handles lifecycle internally, no need to set lifespan manually


# ============================================================================
# Main Entry Point - Official MCP Configuration
# ============================================================================

if __name__ == "__main__":
    import sys

    import uvicorn

    # Configuration based on official MCP SDK patterns
    # Supported transports:
    # - stdio: For local CLI usage
    # - streamable-http: For remote HTTP access (default, recommended)
    transport = "streamable-http"
    host = "0.0.0.0"  # Listen on all interfaces for remote access
    port = 8009  # Unique port to avoid conflicts with other servers

    # Parse command line arguments
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--stdio":
            transport = "stdio"
        elif arg == "--port" and i + 2 < len(sys.argv):
            port = int(sys.argv[i + 2])
        elif arg == "--host" and i + 2 < len(sys.argv):
            host = sys.argv[i + 2]

    logger.info(f"Starting REFACTORED MCP server with transport: {transport}")
    logger.info(
        f"Protocol version support: {LATEST_PROTOCOL_VERSION} (latest), {DEFAULT_NEGOTIATED_VERSION} (default)"
    )

    if transport == "stdio":
        # For stdio transport (local CLI usage)
        logger.info("Running in stdio mode for local CLI clients")
        mcp.run(transport="stdio")
    else:
        # For streamable-http transport (remote access)
        logger.info(f"REFACTORED MCP server accessible at http://{host}:{port}/mcp")
        logger.info("Server supports all official MCP capabilities:")
        logger.info("  ✅ Tools (with Context support)")
        logger.info("  ✅ Resources (URI-based access)")
        logger.info("  ✅ Prompts (AI assistant templates)")
        logger.info("  ✅ Logging (structured logging)")
        logger.info("  ✅ Progress reporting")
        logger.info("  ✅ Session management")

        # Get the ASGI app from FastMCP
        app = mcp.streamable_http_app()

        # Add health check endpoint using Starlette routing
        import time

        from starlette.responses import JSONResponse
        from starlette.routing import Route

        from config import settings

        async def health_check(request):
            """Database health check endpoint."""
            start_time = time.time()
            health_status = {"status": "healthy", "timestamp": time.time(), "checks": {}}

            # Check database connection
            try:
                # Count products
                result = db.fetchone(
                    f"SELECT COUNT(*) as count FROM {settings.SCHEMA_NAME}.products"
                )
                product_count = result["count"] if result else 0

                # Count bookings/appointments
                booking_result = db.fetchone(
                    f"SELECT COUNT(*) as count FROM {settings.SCHEMA_NAME}.appointments"
                )
                booking_count = booking_result["count"] if booking_result else 0

                # Check extensions
                extensions = db.fetchall(
                    "SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'unaccent', 'vector')"
                )
                ext_names = [e["extname"] for e in extensions]

                # Check normalize_text function
                try:
                    db.fetchone(f"SELECT {settings.SCHEMA_NAME}.normalize_text('test')")
                    has_normalize = True
                except Exception:
                    has_normalize = False

                db_response_time = (time.time() - start_time) * 1000

                health_status["checks"]["database"] = {
                    "status": "healthy",
                    "response_time_ms": round(db_response_time, 2),
                    "product_count": product_count,
                    "booking_count": booking_count,
                    "schema": settings.SCHEMA_NAME,
                    "extensions": ext_names,
                    "normalize_text_available": has_normalize,
                }

                missing_extensions = {"pg_trgm", "unaccent", "vector"} - set(ext_names)
                if missing_extensions:
                    health_status["checks"]["database"]["status"] = "degraded"
                    health_status["checks"]["database"]["warning"] = (
                        f"Missing extensions: {list(missing_extensions)}"
                    )
                    health_status["status"] = "degraded"

                if not has_normalize:
                    health_status["checks"]["database"]["status"] = "degraded"
                    health_status["checks"]["database"]["warning"] = (
                        "normalize_text function not available"
                    )
                    health_status["status"] = "degraded"

            except Exception as e:
                health_status["status"] = "unhealthy"
                health_status["checks"]["database"] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "response_time_ms": round((time.time() - start_time) * 1000, 2),
                }

            # Set HTTP status code based on health
            status_code = 200 if health_status["status"] == "healthy" else 503

            return JSONResponse(content=health_status, status_code=status_code)

        # Add the route to the existing Starlette app
        health_route = Route("/health", health_check)
        app.routes.append(health_route)

        logger.info(f"✅ Health check endpoint available at http://{host}:{port}/health")

        # Run with uvicorn using official configuration
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
        )
