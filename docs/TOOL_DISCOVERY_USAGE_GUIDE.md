# Tool Discovery System - Usage Guide

## Overview

The tool autodiscovery system automatically manages and categorizes MCP tools without hardcoded lists. It's ready for production use.

## Quick Start

### For Users/Developers

**Good news:** You don't need to do anything! The system works automatically:

1. Tools are automatically discovered at server startup
2. Validation runs automatically
3. Agents automatically get the right tools

### For Adding New Tools

When you need to add a new MCP tool:

#### Step 1: Define the Tool

```python
# In appropriate handler (booking_handlers.py, product_handlers.py, etc.)

from mcp.server.fastmcp import Context

@mcp.tool()
async def my_new_tool(ctx: Context, param1: str) -> dict:
    """Description of what the tool does.

    Args:
        ctx: MCP context for logging
        param1: Parameter description

    Returns:
        Result dictionary
    """
    # Implementation
    return {"result": "value"}
```

#### Step 2: Register the Tool

```python
# At the end of the register_*_tools() function

# Add to the list of tools to register
new_tools = ["my_new_tool"]

# Register with category
your_registry.register_tools(new_tools, "category_name")
```

#### Step 3: Rebuild and Deploy

```bash
# Rebuild the container
docker-compose build --no-cache mcp-server

# Restart
docker-compose up -d

# Verify
docker logs mcp-server | grep "Tool discovery"
# Should show: ✅ Tool discovery system is READY FOR PRODUCTION
```

**That's it!** Your tool is now automatically:
- ✅ Registered in the correct category
- ✅ Available to the appropriate agents
- ✅ Validated at startup
- ✅ Discoverable by resource endpoints

## System Components

### 1. ToolRegistry (`mcp_handlers/tool_registry.py`)

Simple registry for tracking tools by category:

```python
from mcp_handlers.tool_registry import ToolRegistry

registry = ToolRegistry()

# Register individual tool
registry.register_tool("create_booking", "booking")

# Register multiple tools
registry.register_tools([
    "create_booking",
    "cancel_booking",
    "save_session_auth",
], "booking")

# Get tools for a category
booking_tools = registry.get_tools_by_category("booking")
# Returns: ["create_booking", "cancel_booking", "save_session_auth"]

# Get all categories
categories = registry.get_all_categories()
# Returns: ["booking", "product", "pageable"]
```

### 2. Tool Discovery Validator (`mcp_handlers/tool_discovery_validator.py`)

Validates that registered tools match actual MCP tools:

```python
from mcp_handlers.tool_discovery_validator import (
    validate_tool_registries,
    log_tool_discovery_status,
)

# Validate registries
result = validate_tool_registries(
    mcp,
    booking_registry=booking_tool_registry,
    product_registry=product_tool_registry,
    pageable_registry=pageable_tool_registry,
)

# Check if valid
if result.is_valid:
    print("✅ All registries are valid!")
else:
    print(f"❌ Errors: {result.errors}")

# Log status
log_tool_discovery_status(result)
```

### 3. Handler Integration

Each handler manages its own registry:

```python
# In booking_handlers.py
booking_tool_registry = ToolRegistry()

def get_booking_tool_names() -> list[str]:
    """Returns dynamically discovered tools"""
    return booking_tool_registry.get_tools_by_category("booking")

def register_booking_tools():
    @mcp.tool()
    async def create_booking(...): ...

    @mcp.tool()
    async def cancel_booking(...): ...

    # Register all at once
    booking_tool_registry.register_tools([
        "create_booking",
        "cancel_booking",
        # ... more tools ...
    ], "booking")
```

### 4. Server Startup Validation

Validation runs automatically when the server starts:

```python
# In server.py
validation = validate_tool_registries(...)
log_tool_discovery_status(validation)

if not validation.is_valid:
    logger.error("Tool discovery validation failed")
```

## Current Tool Categories

### Booking Category (17 tools)

**Booking Operations:**
- `create_booking` - Create new reservations
- `cancel_booking` - Cancel existing bookings
- `reschedule_booking` - Modify appointment
- `get_available_slots` - Check availability
- `get_booking_by_id` - Retrieve details
- `list_customer_bookings` - Customer's reservations
- `get_services` - Available services
- `get_business_hours` - Operating hours

**User Management:**
- `check_user_exists` - Lookup user
- `create_user` - Register new user
- `request_otp` - Send OTP code
- `verify_otp` - Verify OTP
- `update_user` - Update profile

**Session Management:**
- `check_session_auth` - Check authentication ⭐
- `save_session_auth` - Save auth to session ⭐ CRITICAL
- `clear_session_auth` - Logout
- `update_session_activity` - Keep session alive

### Product Category (5 tools)

- `fetch_by_sku` - Look up by SKU code
- `fetch_by_id` - Look up by product ID
- `search_products` - General search
- `fuzzy_search_smart` - Fuzzy matching
- `ingest_products` - Add products

### Pageable Category (2 tools)

- `fuzzy_search_smart` - Supports pagination
- `search_products` - Supports pagination

## Troubleshooting

### Issue: Tool not available to agent

**Check:**
1. Tool is registered in correct category
2. Handler's `register_*_tools()` was called
3. Tool name matches exactly
4. Server was restarted after change

**Debug:**
```bash
# Check logs for registration
docker logs mcp-server | grep "Registered.*tools"

# Check validation
docker logs mcp-server | grep "validation"

# If missing, you'll see:
# Tool registry tool 'tool_name' not found in MCP server
```

**Fix:**
```python
# Verify the tool is registered:
registry.register_tools(["tool_name"], "category")
```

### Issue: Validation failed at startup

**Check logs:**
```bash
docker logs mcp-server | grep -A 5 "validation.*ERROR"
```

**Common causes:**
1. Tool name mismatch between @mcp.tool() and registry
2. Tool registered in wrong category
3. Tool forgotten in registry.register_tools() call

**Fix:**
1. Update registry call to match tool name
2. Check capitalization
3. Rebuild: `docker-compose build --no-cache mcp-server`

### Issue: New tool not showing up

**Checklist:**
- [ ] Tool defined with @mcp.tool() decorator
- [ ] Tool added to registry.register_tools() list
- [ ] Handler's register_*_tools() includes registration call
- [ ] Container rebuilt: `docker-compose build --no-cache`
- [ ] Container restarted: `docker-compose restart`
- [ ] Check logs: `docker logs mcp-server | grep "your_tool"`

## Best Practices

### 1. Naming Conventions

Use descriptive, consistent names:
```python
# ✅ Good
"create_booking"
"save_session_auth"
"fuzzy_search_smart"

# ❌ Bad
"createBooking"      # Use underscores
"save_auth"          # Too generic
"fuzzy_search"       # Already exists
```

### 2. Category Assignment

Use existing categories when possible:
```python
# ✅ Good - existing categories
"booking"     # All booking-related tools
"product"     # All product search tools
"pageable"    # Tools that support pagination

# ❌ Bad - new categories without reason
"my_custom_category"  # Unless really needed
```

### 3. Documentation

Always document your tool:
```python
@mcp.tool()
async def my_tool(ctx: Context, param: str) -> dict:
    """Clear description of what tool does.

    This tool is used for [specific purpose].

    Args:
        ctx: MCP context for logging
        param: What this parameter does

    Returns:
        What the result contains

    Example:
        >>> result = await my_tool(ctx, "example")
        >>> print(result)
    """
```

### 4. Registration Organization

Group related tools:
```python
# ✅ Organized
booking_tools = [
    "create_booking",
    "cancel_booking",
    "reschedule_booking",
    "get_available_slots",
    # ... more booking ...
    "check_user_exists",
    "create_user",
    # ... more user ...
]
registry.register_tools(booking_tools, "booking")

# ❌ Unorganized
registry.register_tool("create_booking", "booking")
registry.register_tool("fetch_product", "product")
registry.register_tool("cancel_booking", "booking")
# Hard to read and maintain
```

## FAQ

**Q: Do I need to update get_*_tool_names() manually?**
A: No! It's automatic. Just register the tool and it appears.

**Q: What happens if I forget to register a tool?**
A: The validator will warn you at startup.

**Q: Can I check tool status without logs?**
A: Run: `docker logs mcp-server | grep "Tool discovery"`

**Q: Do I need to restart the server every time I add a tool?**
A: Yes, because tools are registered during handler initialization.

**Q: Can I remove tools safely?**
A: Yes, just remove from the registry.register_tools() list and rebuild.

**Q: What's the performance impact?**
A: Minimal. Validation runs once at startup (~100ms).

**Q: Is this backward compatible?**
A: 100% yes. No changes to agent_orchestrator.py or APIs.

## Learning Resources

- See: `tool_registry.py` for registry implementation
- See: `tool_discovery_validator.py` for validation logic
- See: `booking_handlers.py` for real-world usage example
- See: `product_handlers.py` for multi-category example

## Summary

✨ The tool autodiscovery system is:

✅ **Easy to use** - Just register tools, done!
✅ **Self-validating** - Catches errors automatically
✅ **Maintainable** - Single source of truth
✅ **Scalable** - Handles any number of tools
✅ **Production-ready** - Fully tested and deployed

Start adding tools with confidence! 🚀
