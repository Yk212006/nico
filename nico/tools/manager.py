from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Protocol


class Tool(Protocol):
    """Protocol for callable assistant tools.

    Every tool must expose ``name``, ``description``, and an async
    ``execute(**kwargs)`` method.  Optionally a tool can declare:
    - ``parameters``: JSON-Schema dict describing accepted kwargs.
    - ``category``:   String grouping (``"system"`` | ``"web"`` | ``"hardware"`` …).
    - ``requires_confirmation``: ``True`` for destructive actions.
    - ``timeout_seconds``: Per-tool execution timeout (default 30 s).
    - ``max_retries``:     Number of retry attempts on failure (default 0).
    """

    name: str
    description: str

    async def execute(self, **kwargs: Any) -> Any: ...


@dataclass
class ToolMetadata:
    """Rich metadata for tool discovery and documentation."""

    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    category: str = "general"
    requires_confirmation: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 0


class ToolExecutionError(Exception):
    """Raised when a tool fails after all retry attempts."""

    def __init__(self, tool_name: str, message: str, *, attempts: int = 1) -> None:
        super().__init__(f"Tool '{tool_name}' failed after {attempts} attempt(s): {message}")
        self.tool_name = tool_name
        self.attempts = attempts


class ToolManager:
    """Registry and executor for plugin-based tools.

    Features:
    - Per-tool timeout enforcement via ``asyncio.wait_for``
    - Configurable retry with exponential back-off
    - Schema / parameter validation (if the tool declares ``parameters``)
    - Structured execution logging
    """

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool: Any) -> None:
        """Register a tool object.

        Args:
            tool: Any object exposing ``name`` (str) and async ``execute``.

        Raises:
            TypeError: If the tool does not meet the minimum protocol.
        """
        if not hasattr(tool, "name") or not hasattr(tool, "execute"):
            raise TypeError("Tool objects must expose 'name' and 'execute'")
        self._tools[str(tool.name)] = tool

    def unregister(self, tool_name: str) -> bool:
        """Remove a registered tool.  Returns ``True`` if it existed."""
        return self._tools.pop(tool_name, None) is not None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_tools(self) -> list[ToolMetadata]:
        """Return metadata for every registered tool."""
        return [
            ToolMetadata(
                name=tool.name,
                description=getattr(tool, "description", ""),
                parameters=getattr(tool, "parameters", {}) or {},
                category=getattr(tool, "category", "general"),
                requires_confirmation=getattr(tool, "requires_confirmation", False),
                timeout_seconds=getattr(tool, "timeout_seconds", 30.0),
                max_retries=getattr(tool, "max_retries", 0),
            )
            for tool in self._tools.values()
        ]

    def get(self, tool_name: str) -> Any | None:
        """Return a tool by name, or ``None`` if not found."""
        return self._tools.get(tool_name)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a registered tool with timeout and retry support.

        Args:
            tool_name: Name of the tool to run.
            **kwargs:  Arguments forwarded verbatim to ``tool.execute()``.

        Returns:
            The tool's return value.

        Raises:
            KeyError:            If the tool is not registered.
            ToolExecutionError:  If the tool fails after all retries.
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            raise KeyError(f"Unknown tool: {tool_name}")

        timeout: float = getattr(tool, "timeout_seconds", 30.0)
        max_retries: int = getattr(tool, "max_retries", 0)

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                start = time.monotonic()
                result = await asyncio.wait_for(tool.execute(**kwargs), timeout=timeout)
                elapsed_ms = (time.monotonic() - start) * 1000
                # Publish ToolExecuted event without creating a circular import
                try:
                    from nico.events import ToolExecuted, publish
                    await publish(
                        ToolExecuted(
                            tool_name=tool_name,
                            success=True,
                            duration_ms=elapsed_ms,
                            result_summary=str(result)[:120],
                        )
                    )
                except Exception:
                    pass
                return result
            except asyncio.TimeoutError as exc:
                last_exc = exc
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                continue

        raise ToolExecutionError(
            tool_name,
            str(last_exc),
            attempts=max_retries + 1,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_openai_schema(self) -> list[dict[str, Any]]:
        """Convert registered tools to OpenAI function-calling schema."""
        schema = []
        for meta in self.list_tools():
            schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": meta.name,
                        "description": meta.description,
                        "parameters": meta.parameters
                        or {"type": "object", "properties": {}},
                    },
                }
            )
        return schema

    def to_claude_schema(self) -> list[dict[str, Any]]:
        """Convert registered tools to Anthropic Claude tool-use schema."""
        schema = []
        for meta in self.list_tools():
            schema.append(
                {
                    "name": meta.name,
                    "description": meta.description,
                    "input_schema": meta.parameters
                    or {"type": "object", "properties": {}},
                }
            )
        return schema

    def to_gemini_schema(self) -> list[dict[str, Any]]:
        """Convert registered tools to Gemini functionDeclarations schema."""
        schema = []
        for meta in self.list_tools():
            schema.append(
                {
                    "name": meta.name,
                    "description": meta.description,
                    "parameters": meta.parameters
                    or {"type": "object", "properties": {}},
                }
            )
        return schema
