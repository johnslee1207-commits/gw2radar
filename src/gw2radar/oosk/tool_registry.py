from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolDef:
    tool_id: str
    description: str = ""
    handler: Callable[..., dict] | None = None
    input_schema: dict[str, str] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, tool_id: str, handler: Callable[..., dict], description: str = "",
                 input_schema: dict[str, str] | None = None) -> None:
        self._tools[tool_id] = ToolDef(
            tool_id=tool_id,
            handler=handler,
            description=description,
            input_schema=input_schema or {},
        )

    def get(self, tool_id: str) -> ToolDef | None:
        return self._tools.get(tool_id)

    def execute(self, tool_id: str, payload: dict) -> dict:
        tool = self._tools.get(tool_id)
        if not tool or not tool.handler:
            return {"error": f"Tool '{tool_id}' not found or has no handler"}
        return tool.handler(**payload)

    def list_tools(self) -> dict[str, ToolDef]:
        return dict(self._tools)


class ToolGraph:
    def __init__(self) -> None:
        self._edges: dict[str, set[str]] = {}

    def add_dependency(self, caller: str, callee: str) -> None:
        self._edges.setdefault(caller, set()).add(callee)

    def analyze_impact(self, tool_id: str) -> dict:
        affected: set[str] = set()

        def _walk(tid: str) -> None:
            for caller, callees in self._edges.items():
                if tid in callees:
                    affected.add(caller)
                    _walk(caller)

        _walk(tool_id)
        return {"tool_id": tool_id, "downstream_dependents": sorted(affected)}


class AgentToolLayer:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry
        self._forbidden: set[str] = set()

    def forbid_operation(self, tool_name: str) -> None:
        self._forbidden.add(tool_name)

    def call(self, tool_name: str, arguments: dict) -> dict:
        if tool_name in self._forbidden:
            return {"error": f"Operation '{tool_name}' is forbidden"}
        result = self._registry.execute(tool_name, arguments)
        return result
