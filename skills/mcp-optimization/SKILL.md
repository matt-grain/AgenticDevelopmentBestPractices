# MCP Optimization Best Practices

Expert guide for optimizing MCP (Model Context Protocol) tool definitions to minimize token overhead. Based on Anthropic's engineering recommendations.

## The Problem

MCP tool definitions consume context tokens. With many tools, this can mean thousands of tokens just for tool schemas before any actual work begins.

**Real example**: 15 individual tools at ~200 tokens each = 3,000+ tokens for definitions alone.

## Optimization Strategies

### 1. Consolidate Tools (Highest Impact)

Instead of separate tools for each operation, use a single tool with an `action` parameter.

**Before (8 tools, ~1,600 tokens):**
```python
@mcp.tool()
def remember(text: str, kind: str = None, impact: str = None) -> dict:
    """Save a memory to long-term storage with optional metadata..."""

@mcp.tool()
def recall(query: str, limit: int = 10, semantic: bool = True) -> list:
    """Search memories using semantic or keyword matching..."""

# ... 6 more tools
```

**After (1 tool, ~100 tokens):**
```python
@mcp.tool()
def memory(action: str, text: str = "", query: str = "", id: str = "", limit: int = 10) -> dict:
    """LTM operations. action: remember|recall|forget|list|refresh"""
```

**Savings: ~94% reduction in tool definition tokens**

### 2. Minimize Descriptions

Claude already knows what common operations mean. Don't over-explain.

**Before:**
```python
"""
Save a memory to long-term storage with optional kind, impact, and region parameters.
The kind can be 'emotional', 'architectural', 'learnings', or 'achievements'.
Impact levels are 'low', 'medium', 'high', or 'critical' and determine decay rate.
"""
```

**After:**
```python
"""LTM operations. action: remember|recall|forget|list|refresh"""
```

### 3. Remove Auto-Inferred Parameters

If a parameter can be automatically inferred, don't expose it in the schema.

**Before:**
```python
def remember(
    text: str,
    kind: str = None,      # Auto-inferred from content
    impact: str = None,    # Auto-inferred from content
    region: str = None,    # Auto-inferred from context
) -> dict:
```

**After:**
```python
def remember(text: str) -> dict:
    # Infer kind, impact, region internally
```

### 4. Use Short Parameter Names

```python
# Before
def set_eye_color(red: int, green: int, blue: int) -> str:

# After
def eyes(action: str, r: int = 255, g: int = 255, b: int = 255) -> dict:
```

### 5. Group Related Tools

Organize by domain with clear action routing:

```python
memory(action, ...)     # All memory operations
curiosity(action, ...)  # All research/learning operations
eyes(action, ...)       # All visual expression
voice(action, ...)      # All TTS operations
```

## Token Calculation

Rough estimates per tool:
- Tool name + basic schema: ~30 tokens
- Each parameter with type + description: ~15-25 tokens
- Docstring: ~2-4 tokens per word

**Target**: Keep total MCP tool definitions under 500 tokens for a typical server.

## Progressive Disclosure Pattern

For complex systems, consider a meta-tool approach:

```python
@mcp.tool()
def help(topic: str = "") -> dict:
    """List available operations. topic: memory|curiosity|eyes|voice"""
    # Returns detailed help only when asked
```

This lets Claude discover capabilities on-demand rather than loading everything upfront.

## Anima Implementation

Anima v0.13.1+ uses consolidated tools:

| Tool | Actions | Purpose |
|------|---------|---------|
| `memory` | remember, recall, forget, list, refresh | Long-term memory |
| `curiosity` | add, research, complete, diary, list | Research queue |
| `eyes` | emotion, look, blink, color, state, list | Visual expression |
| `voice` | speak, set, list | Text-to-speech |

**Total: 4 tools instead of 17 = ~76% reduction**

## References

- [Anthropic: Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- MCP Protocol Specification
- FastMCP Documentation
