"""
MCP Tool Registry — Customer Success Digital FTE (Stage 2)

Central registry for all MCP tools. Tools are registered with the
@register decorator and invoked through call_tool().

This decouples the agent from specific tool implementations and
provides a clean interface for tool substitution and extension.

Usage:
    # Register a tool (in tool module):
    @register("search_kb")
    def search_kb(query: str, db: Session, max_results: int = 3) -> dict:
        ...

    # Call a tool (in agent/workflow):
    result = call_tool("search_kb", query="password reset", db=db)
"""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Callable] = {}


def register(name: str) -> Callable:
    """
    Decorator that registers a function as a named MCP tool.

    Args:
        name: Tool name used when calling via call_tool().

    Returns:
        Decorator function that registers and returns the original function.
    """
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[name] = fn
        logger.debug("Registered MCP tool: %s", name)
        return fn
    return decorator


def call_tool(name: str, **kwargs) -> Any:
    """
    Invoke a registered MCP tool by name.

    Args:
        name: The registered tool name.
        **kwargs: Arguments forwarded to the tool function.

    Returns:
        Whatever the tool function returns.

    Raises:
        ValueError: If the tool name is not registered.
    """
    if name not in _REGISTRY:
        available = list(_REGISTRY.keys())
        raise ValueError(
            f"MCP tool '{name}' not found in registry. "
            f"Available tools: {available}"
        )
    logger.info("Calling MCP tool: %s | args: %s", name, list(kwargs.keys()))
    return _REGISTRY[name](**kwargs)


def list_tools() -> list[str]:
    """Return names of all registered tools."""
    return sorted(_REGISTRY.keys())


def is_registered(name: str) -> bool:
    """Check if a tool is registered."""
    return name in _REGISTRY


def init_tools() -> None:
    """
    Import all tool modules to trigger @register decorators.
    Must be called once at application startup (before any tool calls).
    """
    from backend.mcp.tools import (  # noqa: F401 — side-effect: registration
        create_ticket,
        escalate_issue,
        get_customer_context,
        kb_search,
        send_channel_response,
    )
    logger.info("MCP tools registered: %s", list_tools())
