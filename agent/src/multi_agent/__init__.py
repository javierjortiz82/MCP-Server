"""Multi-Agent System for Lab01-MCP.

This package provides specialized agents for routing customer queries:
- AgentFactory: Factory pattern for creating agents (recommended)
- AgentRouter: Intent classification and routing
- BookingAgent: Handles reservation/appointment queries
- GeneralAgent: Handles FAQ and general information queries
- SalesAgent: Handles product sales and recommendations (advanced features)
- MemoryManager: Persistent memory management (NEW in v3.1.0)

All agents inherit from BaseAgent for code reuse and consistency.

Quickstart (using Factory - recommended):
    >>> from multi_agent import AgentFactory
    >>> agent = await AgentFactory.create("booking", mcp_tools=tools)
    >>> response = await agent.generate_response("Quiero reservar")

Quickstart (manual - Sales):
    >>> from multi_agent import SalesAgent
    >>> agent = SalesAgent(mcp_client=client, mcp_tools=tools)
    >>> await agent.initialize()
    >>> response = await agent.send_message("Busco laptop gaming")

Quickstart (manual - Booking):
    >>> from multi_agent import BookingAgent
    >>> agent = BookingAgent(mcp_tools=tools)
    >>> await agent.initialize()
    >>> response = await agent.generate_response("Quiero reservar")

Quickstart (Memory):
    >>> from multi_agent import MemoryManager
    >>> memory = MemoryManager()
    >>> session_id = memory.create_session("user@example.com")

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 3.1.0 (Added MemoryManager for persistent context)
"""

import sys
from pathlib import Path

# CRITICAL: Add mcp_server to sys.path BEFORE any imports
# This allows memory_manager to import from mcp_server
project_root = Path(__file__).resolve().parent.parent.parent.parent
mcp_server_path = project_root / "mcp_server"

# Remove client_mcp from sys.path temporarily if present, to avoid utils conflict
_client_mcp_path = str(project_root / "client_mcp")
_client_mcp_was_in_path = _client_mcp_path in sys.path
if _client_mcp_was_in_path:
    sys.path.remove(_client_mcp_path)

# Add mcp_server at position 0
if mcp_server_path.exists():
    _mcp_path_str = str(mcp_server_path)
    if _mcp_path_str in sys.path:
        sys.path.remove(_mcp_path_str)
    sys.path.insert(0, _mcp_path_str)

# Now safe to import modules
from multi_agent.agent_factory import AgentFactory
from multi_agent.agent_router import AgentRouter, Intent
from multi_agent.booking_agent import BookingAgent
from multi_agent.general_agent import GeneralAgent
from multi_agent.sales_agent import SalesAgent

# Import MemoryManager from mcp_server using absolute file path
# NOTE: Complex import required due to client_mcp/utils and mcp_server/utils namespace conflict
try:
    import importlib.util

    # CRITICAL: Temporarily prioritize mcp_server over client_mcp to avoid namespace conflicts
    # Save current state
    _saved_paths = []
    _paths_to_remove = [p for p in sys.path if "client_mcp" in p]
    for _p in _paths_to_remove:
        _saved_paths.append((_p, sys.path.index(_p)))
        sys.path.remove(_p)

    # Ensure mcp_server is at position 0
    _mcp_str = str(mcp_server_path)
    if _mcp_str in sys.path:
        sys.path.remove(_mcp_str)
    sys.path.insert(0, _mcp_str)

    # Clear module cache for utils and config modules (client_mcp pollutes sys.modules)
    _saved_modules = {}
    _modules_to_clear = [
        k for k in sys.modules.keys() if k.startswith(("utils", "config"))
    ]
    for _mod in _modules_to_clear:
        _saved_modules[_mod] = sys.modules.pop(_mod)

    try:
        # Load MemoryManager directly from file path
        _memory_manager_file = mcp_server_path / "utils" / "memory_manager.py"

        if not _memory_manager_file.exists():
            raise ImportError(f"MemoryManager file not found at {_memory_manager_file}")

        # Load module from file path
        _spec = importlib.util.spec_from_file_location(
            "mcp_memory_manager", _memory_manager_file
        )
        if _spec is None or _spec.loader is None:
            raise ImportError("Failed to create module spec")

        _memory_module = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_memory_module)
        MemoryManager = _memory_module.MemoryManager

        MEMORY_AVAILABLE = True
    finally:
        # Restore client_mcp paths and modules
        for _p, _idx in reversed(_saved_paths):
            sys.path.insert(_idx, _p)
        for _mod, _obj in _saved_modules.items():
            if _mod not in sys.modules:  # Only restore if not replaced
                sys.modules[_mod] = _obj

except (ImportError, AttributeError, FileNotFoundError) as e:
    import logging

    logging.warning(f"MemoryManager not available: {e}")
    MemoryManager = None  # type: ignore[misc,assignment]
    MEMORY_AVAILABLE = False

__all__ = [
    "MEMORY_AVAILABLE",
    "AgentFactory",
    "AgentRouter",
    "BookingAgent",
    "GeneralAgent",
    "Intent",
    "MemoryManager",
    "SalesAgent",
]

__version__ = "3.1.0"  # Added MemoryManager
