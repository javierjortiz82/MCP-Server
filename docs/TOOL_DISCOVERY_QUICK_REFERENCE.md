# Tool Discovery System - Quick Reference

## Check System Status

```bash
# View tool discovery validation
docker logs mcp-server | grep -i "tool discovery"

# See what tools are registered
docker logs mcp-server | grep "Registered.*tools"

# Check for any errors
docker logs mcp-server | grep -i "error\|failed" | grep -v "skipped"

# Full server status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Expected Output

```
✅ Tool discovery system is READY FOR PRODUCTION
   - 22 tools registered
   - 3 categories configured
   - booking: 17 tools
   - product: 5 tools
   - pageable: 2 tools
```

## Adding a New Tool - 3 Steps

### Step 1: Define Tool

```python
# In appropriate handler file

@mcp.tool()
async def my_new_tool(ctx: Context, param: str) -> dict:
    """Tool description"""
    return {"result": "value"}
```

### Step 2: Register Tool

```python
# At end of register_*_tools() function

my_tools = ["my_new_tool"]
registry.register_tools(my_tools, "category")
```

### Step 3: Deploy

```bash
docker-compose build --no-cache mcp-server
docker-compose up -d
docker logs mcp-server | grep "Tool discovery"  # Verify
```

## Troubleshooting

### Tool Not Appearing

```bash
# 1. Check if tool is defined
grep -r "async def my_tool" mcp_server/mcp_handlers/

# 2. Check if it's registered
grep -r "register_tools.*my_tool" mcp_server/mcp_handlers/

# 3. Check logs for errors
docker logs mcp-server | grep "my_tool\|validation"

# 4. Verify rebuild happened
docker-compose build --no-cache mcp-server
```

### Validation Errors

```bash
# See detailed errors
docker logs mcp-server | grep -A 10 "validation.*ERROR"

# Common fixes:
# - Check tool name spelling
# - Verify category name
# - Ensure handler initialization completed
```

## System Health Commands

```bash
# Full validation report
docker logs mcp-server | grep -A 5 "is READY FOR PRODUCTION"

# Check all categories
docker logs mcp-server | grep "^   -"

# Verify container health
docker ps | grep mcp-server

# Check database connection
docker logs mcp-server | grep "database\|Database"
```

## Tool Categories

### Booking (17 tools)
Booking, user management, and session management for BookingAgent

### Product (5 tools)
Product search and retrieval for SalesAgent

### Pageable (2 tools)
Tools that support pagination (subset of product)

## Development Workflow

```bash
# 1. Edit handler file
vim mcp_server/mcp_handlers/booking_handlers.py

# 2. Build
docker-compose build --no-cache mcp-server

# 3. Restart
docker-compose restart mcp-server

# 4. Verify
docker logs mcp-server | grep "Tool discovery"

# 5. Test in app
# ...use the tool through agents...
```

## Important Files

- `mcp_server/mcp_handlers/tool_registry.py` - Registry implementation
- `mcp_server/mcp_handlers/tool_discovery_validator.py` - Validator
- `mcp_server/mcp_handlers/booking_handlers.py` - Booking tools
- `mcp_server/mcp_handlers/product_handlers.py` - Product tools
- `mcp_server/server.py` - Validation trigger

## Key Metrics

- Total tools: 22
- Total categories: 3
- Validation status: ✅ PASSING
- Server status: 🟢 HEALTHY
- Last validation: 2025-11-19 05:16:50

## Support

- Full guide: `docs/TOOL_DISCOVERY_USAGE_GUIDE.md`
- Technical details: `docs/TOOL_DISCOVERY_COMPLETE_REPORT.md`
- Issues? Check logs: `docker logs mcp-server`

---

**System Status: ✨ PRODUCTION READY**
