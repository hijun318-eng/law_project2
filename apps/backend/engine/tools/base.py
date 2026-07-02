from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = ""


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    input_schema: dict = {}
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 서브클래스가 input_schema를 정의하지 않으면 독립 복사본 부여
        if "input_schema" not in cls.__dict__:
            cls.input_schema = {}

    def run(self, **kwargs) -> ToolResult:
        try:
            self._validate(kwargs)
            return self._execute(**kwargs)
        except Exception as e:
            return ToolResult(False, None, str(e))

    @abstractmethod
    def _execute(self, **kwargs) -> ToolResult:
        pass

    def _validate(self, kwargs: dict):
        for r in self.input_schema.get("required", []):
            if r not in kwargs:
                raise ValueError(f"Missing required argument: {r}")

    def to_mcp_spec(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
