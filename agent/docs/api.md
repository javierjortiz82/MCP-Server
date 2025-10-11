# Agent Module API Documentation

## Overview

The Agent module provides a clean, abstracted interface for AI service providers. Currently implements Google Gemini with a design that supports easy addition of other providers.

## GeminiAgent Class

### Constructor

```python
GeminiAgent(api_key: str, model_name: str = "gemini-2.0-flash-exp")
```

**Parameters:**
- `api_key` (str): Google API key for Gemini access
- `model_name` (str): Model identifier (default: "gemini-2.0-flash-exp")

**Example:**
```python
agent = GeminiAgent(api_key="your-api-key", model_name="gemini-2.0-flash-exp")
```

### Methods

#### `async initialize() -> None`

Initializes the Gemini client and configuration.

**Example:**
```python
await agent.initialize()
```

**Raises:**
- `RuntimeError`: If client initialization fails

---

#### `async generate_response(...) -> GenerateContentResponse`

Generates AI response with optional tool calling support.

**Parameters:**
- `prompt` (str): User input prompt
- `system_prompt` (str, optional): System instructions for behavior
- `tools` (List[FunctionDeclaration], optional): Available tools for function calling
- `tool_config` (ToolConfig, optional): Configuration for tool usage
- `include_history` (bool): Whether to include conversation history (default: True)

**Returns:**
- `GenerateContentResponse`: Gemini response object

**Example:**
```python
response = await agent.generate_response(
    prompt="Find products under $50",
    system_prompt="You are a helpful sales assistant",
    tools=mcp_tools,
    include_history=True
)
```

---

#### `clear_history() -> None`

Clears conversation history.

**Example:**
```python
agent.clear_history()
```

---

#### `add_to_history(user_content: Content, model_content: Content) -> None`

Manually adds messages to conversation history.

**Parameters:**
- `user_content`: User message content
- `model_content`: Model response content

**Example:**
```python
agent.add_to_history(user_msg, model_msg)
```

---

#### `update_generation_config(**kwargs) -> None`

Updates generation parameters dynamically.

**Parameters:**
- `temperature` (float, optional): Sampling temperature (0.0-1.0)
- `top_k` (int, optional): Top-K sampling parameter
- `top_p` (float, optional): Top-P (nucleus) sampling parameter
- `max_output_tokens` (int, optional): Maximum tokens to generate

**Example:**
```python
agent.update_generation_config(
    temperature=0.7,
    top_k=40,
    top_p=0.95
)
```

---

#### `async cleanup() -> None`

Cleans up resources and clears state.

**Example:**
```python
await agent.cleanup()
```

## Usage Patterns

### Basic Usage

```python
from agent import GeminiAgent

# Initialize
agent = GeminiAgent(api_key="your-key")
await agent.initialize()

# Generate response
response = await agent.generate_response("Hello, how are you?")

# Cleanup
await agent.cleanup()
```

### With Context Manager (Recommended)

```python
class GeminiContextManager:
    def __init__(self, api_key):
        self.agent = GeminiAgent(api_key)

    async def __aenter__(self):
        await self.agent.initialize()
        return self.agent

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.agent.cleanup()

# Usage
async with GeminiContextManager("your-key") as agent:
    response = await agent.generate_response("Hello!")
```

### With Tool Calling

```python
# Define tools
tools = [
    types.FunctionDeclaration(
        name="search_products",
        description="Search for products",
        parameters={...}
    )
]

# Configure tool usage
tool_config = types.ToolConfig(
    function_calling_config=types.FunctionCallingConfig(
        mode=types.FunctionCallingConfig.Mode.AUTO
    )
)

# Generate with tools
response = await agent.generate_response(
    prompt="Find me a laptop",
    tools=tools,
    tool_config=tool_config
)
```

### Custom Configuration

```python
# Initialize with custom model
agent = GeminiAgent(
    api_key="your-key",
    model_name="gemini-pro-vision"
)

await agent.initialize()

# Update generation parameters
agent.update_generation_config(
    temperature=0.9,  # More creative
    max_output_tokens=2048  # Shorter responses
)
```

## Error Handling

```python
try:
    agent = GeminiAgent(api_key="your-key")
    await agent.initialize()
    response = await agent.generate_response("Hello")
except RuntimeError as e:
    print(f"Initialization failed: {e}")
except Exception as e:
    print(f"Generation failed: {e}")
finally:
    await agent.cleanup()
```

## Configuration Parameters

### Generation Config Options

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| temperature | float | 0.0-1.0 | 0.3 | Controls randomness |
| top_k | int | 1-100 | 40 | Top-K sampling |
| top_p | float | 0.0-1.0 | 0.9 | Nucleus sampling |
| max_output_tokens | int | 1-8192 | 8192 | Max response length |

### Model Options

| Model | Description | Use Case |
|-------|-------------|----------|
| gemini-2.0-flash-exp | Fast, efficient model | General purpose |
| gemini-pro | Advanced reasoning | Complex tasks |
| gemini-pro-vision | Multimodal support | Image + text |

## Best Practices

1. **Always Initialize**: Call `initialize()` before using the agent
2. **Clean Up Resources**: Always call `cleanup()` when done
3. **Handle Errors**: Wrap calls in try-catch blocks
4. **Manage History**: Clear history periodically for long conversations
5. **Configure Appropriately**: Adjust parameters based on use case

## Threading and Async

The GeminiAgent is designed for async operation:

```python
import asyncio

async def main():
    agent = GeminiAgent(api_key="key")
    await agent.initialize()

    # Concurrent requests
    tasks = [
        agent.generate_response("Query 1"),
        agent.generate_response("Query 2"),
        agent.generate_response("Query 3")
    ]

    responses = await asyncio.gather(*tasks)
    await agent.cleanup()

asyncio.run(main())
```

## Extending the Agent

To add new AI providers, implement the same interface:

```python
class ClaudeAgent:
    async def initialize(self) -> None: ...
    async def generate_response(...) -> Response: ...
    async def cleanup(self) -> None: ...
```

## Environment Variables

Recommended environment setup:

```env
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.0-flash-exp
TEMPERATURE=0.3
TOP_K=40
TOP_P=0.9
MAX_OUTPUT_TOKENS=8192
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Client not initialized" | Ensure `await agent.initialize()` is called |
| API key errors | Verify key is valid and has proper permissions |
| Rate limiting | Implement exponential backoff |
| Memory issues | Clear history regularly with `clear_history()` |

## Version Compatibility

- Python: 3.9+
- google-genai: 1.41.0+
- asyncio: Required for async operations