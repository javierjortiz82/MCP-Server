# Agent Development Guide 🤖

**Complete guide for creating and extending agents in Lab01-MCP**

Version: 2.1.0 | Last Updated: 2025-10-11

---

## 📋 Table of Contents

1. [Quick Start (5 minutes)](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Creating Your First Agent](#creating-your-first-agent)
4. [Using AgentFactory](#using-agentfactory)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## 🚀 Quick Start

### Create an agent in 3 steps:

**Step 1**: Use AgentFactory (recommended)
```python
from multi_agent import AgentFactory

# Create and initialize in one step
agent = await AgentFactory.create("booking", mcp_tools=tools)
```

**Step 2**: Generate responses
```python
response = await agent.generate_response(
    "Quiero reservar una cita para mañana",
    customer_email="customer@example.com"
)
```

**Step 3**: Cleanup when done
```python
await agent.cleanup()
```

That's it! ✅

---

## 🏗️ Architecture Overview

### Class Hierarchy

```
BaseAgent (Abstract)
│
├── Provides common functionality:
│   ├─ Gemini client initialization
│   ├─ Conversation history (auto-trim to 20 items)
│   ├─ Generation configuration
│   ├─ Response generation pipeline
│   └─ Lifecycle management
│
└── Requires implementation:
    ├─ agent_name (property)
    └─ get_system_prompt(**kwargs) (method)

         ↓ inherits from

BookingAgent        GeneralAgent        SalesAgent
├─ Reservations     ├─ FAQ              ├─ Product sales
├─ With MCP tools   ├─ No tools needed  ├─ With MCP tools
└─ 266 lines        └─ 213 lines        └─ 252 lines
```

### Design Patterns Used

1. **Template Method Pattern**: BaseAgent defines algorithm skeleton
2. **Factory Pattern**: AgentFactory simplifies object creation
3. **Abstract Base Class**: Enforces implementation of required methods

---

## 🎓 Creating Your First Agent

### Example: Support Agent

Let's create a support agent from scratch in ~30 lines of code.

#### Step 1: Create the class file

Create `agent/src/multi_agent/support_agent.py`:

```python
"""Support Agent - Technical Support Specialist."""

from __future__ import annotations
from typing import Any, Optional

from gemini_agent.base_agent import BaseAgent
from multi_agent.prompt_manager import PromptManager


class SupportAgent(BaseAgent):
    """Specialized agent for technical support queries."""

    _prompt_manager: Optional[PromptManager] = None

    @property
    def agent_name(self) -> str:
        """Required by BaseAgent."""
        return "support_agent"

    def get_system_prompt(self, **kwargs) -> str:
        """Required by BaseAgent."""
        if self._prompt_manager is None:
            self._prompt_manager = PromptManager()

        # You would add get_support_prompt() to PromptManager
        # For now, return a simple prompt
        return """Eres un agente de soporte técnico experto.

Tu función es ayudar a resolver problemas técnicos con productos."""
```

#### Step 2: Register in factory (optional but recommended)

Edit `agent/src/multi_agent/agent_factory.py`:

```python
# Add import
from multi_agent.support_agent import SupportAgent

# Add to registry in _initialize_registry()
cls._AGENT_REGISTRY = {
    "booking": BookingAgent,
    "general": GeneralAgent,
    "sales": SalesAgent,
    "support": SupportAgent,  # ← Add this
}
```

#### Step 3: Export in package

Edit `agent/src/multi_agent/__init__.py`:

```python
from multi_agent.support_agent import SupportAgent

__all__ = [
    "AgentFactory",
    "BookingAgent",
    "GeneralAgent",
    "SalesAgent",
    "SupportAgent",  # ← Add this
    ...
]
```

#### Step 4: Use it!

```python
# Using factory
agent = await AgentFactory.create("support")

# Or manually
from multi_agent import SupportAgent
agent = SupportAgent()
await agent.initialize()

# Generate responses
response = await agent.generate_response(
    "Mi producto no enciende, ¿qué hago?"
)
```

**Done! You've created a new agent!** 🎉

---

## 🏭 Using AgentFactory

### Basic Usage

```python
from multi_agent import AgentFactory

# Create booking agent with tools
agent = await AgentFactory.create("booking", mcp_tools=booking_tools)

# Create general agent (no tools needed)
agent = await AgentFactory.create("general")

# Create sales agent with custom parameters
agent = await AgentFactory.create(
    "sales",
    mcp_tools=sales_tools,
    temperature=0.7,
    top_k=50
)
```

### Convenience Methods

```python
# Convenience methods for common agents
booking_agent = await AgentFactory.create_booking_agent(mcp_tools=tools)
general_agent = await AgentFactory.create_general_agent()
sales_agent = await AgentFactory.create_sales_agent(mcp_tools=tools)
```

### Available Agents

```python
# Get list of available agent types
agents = AgentFactory.get_available_agents()
print(agents)  # ['booking', 'general', 'sales']

# Check if agent type exists
if AgentFactory.is_registered("support"):
    agent = await AgentFactory.create("support")
```

### Manual Initialization (advanced)

```python
# Create without auto-initialization
agent = await AgentFactory.create(
    "booking",
    auto_initialize=False
)

# Initialize manually later
await agent.initialize()
```

---

## 🔧 Advanced Features

### 1. Adding MCP Tools

Agents that need function calling (like BookingAgent, SalesAgent) override `_build_generation_config()`:

```python
def _build_generation_config(self, **params) -> types.GenerateContentConfig:
    """Override to add MCP tools."""
    # Use settings defaults
    temp = params.get("temperature", settings.TEMPERATURE)
    # ... other params

    config_params = {
        "temperature": temp,
        # ... other config
    }

    # Add tools if available
    if self.mcp_tools:
        config_params["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
        config_params["tool_config"] = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO,
            )
        )

    return types.GenerateContentConfig(**config_params)
```

### 2. A/B Testing Integration

Agents automatically support A/B testing via PromptManager:

```python
# Agent uses user_id for deterministic bucketing
response = await agent.generate_response(
    "test query",
    user_id="user_12345"  # Same user always gets same variant
)
```

### 3. Conversation History

History is managed automatically:

```python
# History is maintained automatically
response1 = await agent.generate_response("First question")
response2 = await agent.generate_response("Follow-up question")
# response2 has context from response1

# Get history length
length = agent.get_history_length()

# Clear history (e.g., new customer)
agent.clear_history()

# History auto-trims to 20 items (10 conversation turns)
```

### 4. Memory System (Persistent Context)

**⭐ NEW FEATURE**: Agents now support persistent memory across sessions.

**Memory is disabled by default**. To enable memory:

```python
from multi_agent import BookingAgent
from mcp_server.utils.memory_manager import MemoryManager

# 1. Initialize memory system
memory = MemoryManager()

# 2. Create or resume session
session_id = memory.create_session(
    customer_email="user@example.com",
    metadata={"agent_type": "booking"}
)

# 3. Create agent WITH memory
agent = BookingAgent(
    session_id=session_id,        # ← Enable memory
    memory_manager=memory          # ← Enable memory
)

await agent.initialize()
# ✅ Log shows: Memory: ✅ Enabled (session: abc123...)
```

**Memory Features:**
- ✅ **Cross-session persistence**: Remembers user preferences across conversations
- ✅ **Semantic extraction**: Automatically extracts important facts
- ✅ **Priority scoring**: Prioritizes important information (0-10 scale)
- ✅ **TTL management**: Auto-expires old memories (default: 30 days)
- ✅ **Hybrid storage**: RAM (session) + PostgreSQL (long-term)

**For complete memory activation guide**, see: `../../docs/MEMORY_ACTIVATION_GUIDE.md`

### 5. Custom System Prompts

Two approaches:

**Approach A**: Use PromptManager (recommended)

```python
# Add to PromptManager
# In prompt_manager.py:
def get_support_prompt(self, user_id=None):
    return self._render_template(
        "support_system_prompt.j2",
        user_id=user_id
    )

# Use in agent
def get_system_prompt(self, **kwargs):
    if self._prompt_manager is None:
        self._prompt_manager = PromptManager()
    return self._prompt_manager.get_support_prompt(
        user_id=kwargs.get('user_id')
    )
```

**Approach B**: Hardcoded prompt (simple cases)

```python
def get_system_prompt(self, **kwargs):
    return """Your system prompt here..."""
```

### 6. Custom Parameters

Pass custom parameters through factory or constructor:

```python
# Via factory
agent = await AgentFactory.create(
    "sales",
    temperature=0.9,
    top_k=100,
    max_output_tokens=4096
)

# Via constructor
agent = SalesAgent(
    temperature=0.9,
    top_k=100
)
```

---

## ✅ Best Practices

### DO ✅

1. **Use AgentFactory** for creating agents
   ```python
   agent = await AgentFactory.create("booking")  # ✅ Good
   ```

2. **Always cleanup** when done
   ```python
   try:
       response = await agent.generate_response("query")
   finally:
       await agent.cleanup()
   ```

3. **Use PromptManager** for system prompts
   - Enables A/B testing
   - Supports templates
   - Centralized management

4. **Keep agents focused** - one responsibility per agent
   - BookingAgent: Only reservations
   - SalesAgent: Only products
   - Don't mix concerns

5. **Add logging** for debugging
   ```python
   self.logger.info("Processing booking request...")
   ```

6. **Test your agent** - create unit tests
   ```python
   async def test_my_agent():
       agent = await AgentFactory.create("myagent")
       response = await agent.generate_response("test")
       assert response
   ```

### DON'T ❌

1. **Don't instantiate BaseAgent directly**
   ```python
   agent = BaseAgent()  # ❌ Will fail - abstract class
   ```

2. **Don't skip cleanup**
   ```python
   agent = await AgentFactory.create("booking")
   await agent.generate_response("query")
   # ❌ Missing await agent.cleanup()
   ```

3. **Don't duplicate code** - use BaseAgent
   ```python
   # ❌ Bad
   class MyAgent:
       def __init__(self):
           # 200 lines of initialization code...

   # ✅ Good
   class MyAgent(BaseAgent):
       # Only implement required methods
   ```

4. **Don't hardcode API keys**
   ```python
   agent = SalesAgent(api_key="sk-123...")  # ❌ Bad
   # Use settings or environment variables
   ```

5. **Don't ignore errors**
   ```python
   try:
       await agent.generate_response("query")
   except Exception:
       pass  # ❌ Don't silently ignore
   ```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. "TypeError: Can't instantiate abstract class"

**Problem**: Trying to create BaseAgent directly or missing required methods.

**Solution**:
```python
class MyAgent(BaseAgent):
    @property
    def agent_name(self) -> str:  # ← Required
        return "my_agent"

    def get_system_prompt(self, **kwargs) -> str:  # ← Required
        return "prompt"
```

#### 2. "RuntimeError: Agent not initialized"

**Problem**: Called generate_response() before initialize().

**Solution**:
```python
# Option 1: Use factory (auto-initializes)
agent = await AgentFactory.create("booking")

# Option 2: Manual initialization
agent = BookingAgent()
await agent.initialize()  # ← Don't forget this
```

#### 3. "ModuleNotFoundError: No module named 'multi_agent'"

**Problem**: PYTHONPATH not set correctly.

**Solution**:
```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/agent/src:$PYTHONPATH

# Or in Python
import sys
sys.path.insert(0, "/path/to/agent/src")
```

#### 4. Agent not using MCP tools

**Problem**: Tools not configured correctly.

**Solution**:
```python
# Make sure you override _build_generation_config()
def _build_generation_config(self, **params):
    config = super()._build_generation_config(**params)
    if self.mcp_tools:
        config.tools = [types.Tool(function_declarations=self.mcp_tools)]
    return config
```

#### 5. History growing too large

**Problem**: Conversation history consuming too much memory.

**Solution**: History auto-trims to 20 items, but you can manually clear:
```python
# Clear history between customers
agent.clear_history()

# Or check size
if agent.get_history_length() > 10:
    agent.clear_history()
```

---

## 📖 API Reference

### BaseAgent

**Abstract Properties:**
- `agent_name: str` - Unique identifier for agent (e.g., "booking_agent")

**Abstract Methods:**
- `get_system_prompt(**kwargs) -> str` - Return system prompt for agent

**Inherited Methods:**
- `async initialize() -> None` - Initialize Gemini client
- `async generate_response(query: str, **kwargs) -> str` - Generate response
- `clear_history() -> None` - Clear conversation history
- `get_history_length() -> int` - Get history size
- `async cleanup() -> None` - Cleanup resources

**Properties:**
- `api_key: str` - Google API key
- `model_name: str` - Model identifier
- `mcp_tools: List[FunctionDeclaration]` - MCP tools
- `conversation_history: List[Content]` - Conversation history
- `logger: Logger` - Agent-specific logger

### AgentFactory

**Class Methods:**

```python
@classmethod
async def create(
    cls,
    agent_type: str,
    *,
    mcp_tools: Optional[List[FunctionDeclaration]] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    auto_initialize: bool = True,
    **kwargs
) -> BaseAgent
```

**Convenience Methods:**
- `create_booking_agent(**kwargs) -> BaseAgent`
- `create_general_agent(**kwargs) -> BaseAgent`
- `create_sales_agent(**kwargs) -> BaseAgent`

**Utility Methods:**
- `get_available_agents() -> List[str]`
- `is_registered(agent_type: str) -> bool`
- `register_agent(agent_type: str, agent_class: Type[BaseAgent]) -> None`

### Example: Complete Agent Lifecycle

```python
import asyncio
from multi_agent import AgentFactory

async def main():
    # Create agent
    agent = await AgentFactory.create("booking", mcp_tools=tools)

    try:
        # Generate responses
        response1 = await agent.generate_response(
            "Quiero reservar una cita",
            customer_email="user@example.com"
        )
        print(response1)

        # Follow-up (has context)
        response2 = await agent.generate_response(
            "Para mañana a las 10am"
        )
        print(response2)

    finally:
        # Always cleanup
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📚 Additional Resources

- **Memory Activation Guide**: `../../docs/MEMORY_ACTIVATION_GUIDE.md` ⭐ **NEW**
- **Architecture Documentation**: `docs/NOTAS_CLAUDE.md`
- **BaseAgent Tests**: `tests/test_base_agent.py`
- **Factory Tests**: `test_agent_factory.py`
- **Example Agents**:
  - `src/multi_agent/booking_agent.py`
  - `src/multi_agent/general_agent.py`
  - `src/multi_agent/sales_agent.py`

---

## 🤝 Contributing

When creating a new agent:

1. Create agent class inheriting from BaseAgent
2. Implement required methods: `agent_name`, `get_system_prompt()`
3. Add to AgentFactory registry
4. Export in `__init__.py`
5. Write unit tests
6. Update this guide if needed

---

## 📝 Version History

- **2.1.0** (2025-10-11): Added AgentFactory pattern
- **2.0.0** (2025-10-11): Refactored to BaseAgent architecture
- **1.0.0** (2025-10-10): Initial multi-agent system

---

**Questions?** Check `docs/NOTAS_CLAUDE.md` or file an issue.

Happy agent building! 🚀
