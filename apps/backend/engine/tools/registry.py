from engine.tools.base import BaseTool, ToolResult
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' overwritten in registry.")
        self._tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> set[str]:
        return set(self._tools.keys())

    def run(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        if not tool:
            logger.error(f"Tool not found: {name}")
            return ToolResult(False, None, f"Tool not found: {name}")
        try:
            return tool.run(**kwargs)
        except Exception as e:
            logger.exception(f"Tool '{name}' raised exception: {e}")
            return ToolResult(False, None, str(e))

    def list_specs(self) -> list[dict]:
        return [t.to_mcp_spec() for t in self._tools.values()]

registry = ToolRegistry()
