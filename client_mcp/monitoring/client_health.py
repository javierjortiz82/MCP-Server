"""Health monitoring for Client MCP (Odiseo Bot).

This module provides health checks for the client application,
monitoring bot status, MCP connectivity, and resource usage.
"""

import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check result."""

    component: str
    status: HealthStatus
    message: str
    response_time_ms: float
    details: dict[str, Any] | None = None
    timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": round(self.response_time_ms, 2),
        }
        if self.details:
            result["details"] = self.details
        if self.timestamp:
            result["timestamp"] = self.timestamp.isoformat()
        return result


class ClientHealthMonitor:
    """Health monitoring for Odiseo Bot client."""

    def __init__(self):
        """Initialize health monitor."""
        self.start_time = time.time()
        self.bot_instance = None
        self.last_activity = time.time()
        self.message_count = 0
        self.error_count = 0
        self.logger = logger

    def set_bot_instance(self, bot) -> None:
        """Set the bot instance for monitoring.

        Args:
            bot: OdiseoBot instance
        """
        self.bot_instance = bot

    def record_activity(self) -> None:
        """Record bot activity."""
        self.last_activity = time.time()
        self.message_count += 1

    def record_error(self) -> None:
        """Record an error occurrence."""
        self.error_count += 1

    async def check_bot_status(self) -> HealthCheck:
        """Check if bot is properly initialized and running.

        Returns:
            HealthCheck for bot status
        """
        start = time.time()

        try:
            if not self.bot_instance:
                return HealthCheck(
                    component="bot",
                    status=HealthStatus.UNHEALTHY,
                    message="Bot not initialized",
                    response_time_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now(UTC),
                )

            # Check bot initialization
            if not hasattr(self.bot_instance, "client") or not self.bot_instance.client:
                return HealthCheck(
                    component="bot",
                    status=HealthStatus.UNHEALTHY,
                    message="Bot client not initialized",
                    response_time_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now(UTC),
                )

            # Check for recent activity
            inactive_seconds = time.time() - self.last_activity
            if inactive_seconds > 300:  # 5 minutes
                status = HealthStatus.DEGRADED
                message = f"No activity for {int(inactive_seconds)}s"
            else:
                status = HealthStatus.HEALTHY
                message = "Bot active and running"

            return HealthCheck(
                component="bot",
                status=status,
                message=message,
                response_time_ms=(time.time() - start) * 1000,
                details={
                    "message_count": self.message_count,
                    "error_count": self.error_count,
                    "last_activity_seconds_ago": int(inactive_seconds),
                    "uptime_seconds": int(time.time() - self.start_time),
                },
                timestamp=datetime.now(UTC),
            )

        except Exception as e:
            self.logger.exception(f"Bot status check failed: {e}")
            return HealthCheck(
                component="bot",
                status=HealthStatus.UNHEALTHY,
                message=f"Status check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000,
                timestamp=datetime.now(UTC),
            )

    async def check_mcp_connectivity(self) -> HealthCheck:
        """Check MCP server connectivity.

        Returns:
            HealthCheck for MCP connectivity
        """
        start = time.time()

        try:
            if not self.bot_instance:
                return HealthCheck(
                    component="mcp_connection",
                    status=HealthStatus.UNKNOWN,
                    message="Bot not initialized",
                    response_time_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now(UTC),
                )

            # Check if MCP connector exists
            if not hasattr(self.bot_instance, "mcp_client"):
                return HealthCheck(
                    component="mcp_connection",
                    status=HealthStatus.DEGRADED,
                    message="No MCP connector configured",
                    response_time_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now(UTC),
                )

            # Check MCP tools availability
            if hasattr(self.bot_instance, "mcp_tools"):
                tool_count = (
                    len(self.bot_instance.mcp_tools)
                    if self.bot_instance.mcp_tools
                    else 0
                )
                if tool_count > 0:
                    status = HealthStatus.HEALTHY
                    message = f"Connected with {tool_count} tools available"
                else:
                    status = HealthStatus.DEGRADED
                    message = "Connected but no tools available"
            else:
                status = HealthStatus.DEGRADED
                message = "MCP tools not initialized"

            return HealthCheck(
                component="mcp_connection",
                status=status,
                message=message,
                response_time_ms=(time.time() - start) * 1000,
                details={
                    "tool_count": tool_count if "tool_count" in locals() else 0,
                    "mcp_host": os.getenv("MCP_HOST", "localhost"),
                    "mcp_port": os.getenv("MCP_PORT", "3000"),
                },
                timestamp=datetime.now(UTC),
            )

        except Exception as e:
            self.logger.exception(f"MCP connectivity check failed: {e}")
            return HealthCheck(
                component="mcp_connection",
                status=HealthStatus.UNHEALTHY,
                message=f"Connectivity check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000,
                timestamp=datetime.now(UTC),
            )

    async def check_gemini_api(self) -> HealthCheck:
        """Check Google Gemini API connectivity.

        Returns:
            HealthCheck for Gemini API
        """
        start = time.time()

        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return HealthCheck(
                    component="gemini_api",
                    status=HealthStatus.UNHEALTHY,
                    message="API key not configured",
                    response_time_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now(UTC),
                )

            if api_key.startswith("YOUR_") or api_key == "CHANGE_ME":
                return HealthCheck(
                    component="gemini_api",
                    status=HealthStatus.UNHEALTHY,
                    message="API key not properly set",
                    response_time_ms=(time.time() - start) * 1000,
                    timestamp=datetime.now(UTC),
                )

            # Check if bot has Gemini client
            if self.bot_instance and hasattr(self.bot_instance, "client"):
                status = HealthStatus.HEALTHY
                message = "Gemini API configured"
                details = {
                    "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
                    "api_key_configured": True,
                }
            else:
                status = HealthStatus.DEGRADED
                message = "Gemini client not initialized"
                details = {"api_key_configured": True}

            return HealthCheck(
                component="gemini_api",
                status=status,
                message=message,
                response_time_ms=(time.time() - start) * 1000,
                details=details,
                timestamp=datetime.now(UTC),
            )

        except Exception as e:
            self.logger.exception(f"Gemini API check failed: {e}")
            return HealthCheck(
                component="gemini_api",
                status=HealthStatus.UNHEALTHY,
                message=f"API check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000,
                timestamp=datetime.now(UTC),
            )

    async def check_system_resources(self) -> HealthCheck:
        """Check system resource usage.

        Returns:
            HealthCheck for system resources
        """
        start = time.time()

        try:
            # Get current process
            process = psutil.Process(os.getpid())

            # CPU usage (for this process)
            cpu_percent = process.cpu_percent(interval=0.1)

            # Memory usage (for this process)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # System-wide memory
            system_memory = psutil.virtual_memory()

            # Determine health status
            if memory_mb > 1000 or cpu_percent > 80:
                status = HealthStatus.DEGRADED
                message = "High resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Resource usage normal"

            return HealthCheck(
                component="system_resources",
                status=status,
                message=message,
                response_time_ms=(time.time() - start) * 1000,
                details={
                    "process_cpu_percent": round(cpu_percent, 2),
                    "process_memory_mb": round(memory_mb, 2),
                    "system_memory_percent": round(system_memory.percent, 2),
                    "python_version": sys.version.split()[0],
                },
                timestamp=datetime.now(UTC),
            )

        except Exception as e:
            self.logger.exception(f"System resources check failed: {e}")
            return HealthCheck(
                component="system_resources",
                status=HealthStatus.UNKNOWN,
                message=f"Resource check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000,
                timestamp=datetime.now(UTC),
            )

    async def get_full_health(self) -> dict[str, Any]:
        """Get comprehensive health status.

        Returns:
            Complete health status dictionary
        """
        # Run all health checks in parallel
        checks = await asyncio.gather(
            self.check_bot_status(),
            self.check_mcp_connectivity(),
            self.check_gemini_api(),
            self.check_system_resources(),
            return_exceptions=True,
        )

        # Process results
        results = []
        for check in checks:
            if isinstance(check, Exception):
                self.logger.error(f"Health check failed with exception: {check}")
                results.append(
                    HealthCheck(
                        component="unknown",
                        status=HealthStatus.UNKNOWN,
                        message=f"Check failed: {str(check)}",
                        response_time_ms=0,
                        timestamp=datetime.now(UTC),
                    )
                )
            else:
                results.append(check)

        # Determine overall status
        statuses = [c.status for c in results]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.UNKNOWN

        return {
            "status": overall.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "checks": [c.to_dict() for c in results],
            "summary": {
                "total_checks": len(results),
                "healthy": sum(1 for c in results if c.status == HealthStatus.HEALTHY),
                "degraded": sum(
                    1 for c in results if c.status == HealthStatus.DEGRADED
                ),
                "unhealthy": sum(
                    1 for c in results if c.status == HealthStatus.UNHEALTHY
                ),
                "unknown": sum(1 for c in results if c.status == HealthStatus.UNKNOWN),
            },
        }

    def print_health_status(self, health_data: dict[str, Any]) -> None:
        """Print formatted health status to console.

        Args:
            health_data: Health status dictionary
        """
        print("\n" + "=" * 50)
        print("CLIENT HEALTH STATUS")
        print("=" * 50)
        print(f"Overall Status: {health_data['status'].upper()}")
        print(f"Uptime: {health_data['uptime_seconds']}s")
        print(f"Timestamp: {health_data['timestamp']}")
        print("\nComponent Status:")
        print("-" * 50)

        for check in health_data["checks"]:
            status_symbol = {
                "healthy": "✓",
                "degraded": "⚠",
                "unhealthy": "✗",
                "unknown": "?",
            }.get(check["status"], "?")

            print(f"{status_symbol} {check['component']}: {check['message']}")
            if "details" in check and check["details"]:
                for key, value in check["details"].items():
                    print(f"    {key}: {value}")

        print("\nSummary:")
        print("-" * 50)
        summary = health_data["summary"]
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Healthy: {summary['healthy']}")
        print(f"Degraded: {summary['degraded']}")
        print(f"Unhealthy: {summary['unhealthy']}")
        print(f"Unknown: {summary['unknown']}")
        print("=" * 50)


# Global health monitor instance
health_monitor = ClientHealthMonitor()


async def run_health_check() -> dict[str, Any]:
    """Run a complete health check.

    Returns:
        Health status dictionary
    """
    return await health_monitor.get_full_health()


def setup_health_monitoring(bot_instance) -> None:
    """Set up health monitoring for a bot instance.

    Args:
        bot_instance: OdiseoBot instance
    """
    health_monitor.set_bot_instance(bot_instance)
