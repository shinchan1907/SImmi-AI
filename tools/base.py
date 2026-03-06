from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ToolResult(BaseModel):
    status: str # "success" or "error"
    result: Any
    error: Optional[str] = None

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "timeout": 30, # Default timeout in seconds
            "permissions": []
        }

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        """Execute the tool and return a structured ToolResult."""
        pass

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.metadata for t in self.tools.values()]
