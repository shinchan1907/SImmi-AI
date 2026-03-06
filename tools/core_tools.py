import os
import logging
from .base import BaseTool, ToolResult
from typing import Any

logger = logging.getLogger("tools")

class FileWriter(BaseTool):
    @property
    def name(self) -> str:
        return "file_writer"

    @property
    def description(self) -> str:
        return "Writes content to a file. Args: filename (str), content (str)"

    async def run(self, filename: str, content: str, storage_path: str = "./storage") -> ToolResult:
        try:
            # Secure path handling
            if ".." in filename or filename.startswith("/"):
                return ToolResult(status="error", result=None, error="Invalid filename: Path traversal detected")
            
            full_path = os.path.join(storage_path, filename)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info("tool_executed", tool=self.name, file=filename)
            return ToolResult(status="success", result=f"File '{filename}' written successfully.")
        except Exception as e:
            logger.error("tool_failed", tool=self.name, error=str(e))
            return ToolResult(status="error", result=None, error=str(e))

class CodeGenerator(BaseTool):
    @property
    def name(self) -> str:
        return "code_generator"

    @property
    def description(self) -> str:
        return "Generates complex code structures. Args: language (str), requirements (str)"

    async def run(self, language: str, requirements: str) -> ToolResult:
        # Placeholder for real generation logic
        return ToolResult(
            status="success", 
            result={
                "language": language,
                "structure": ["main.py", "requirements.txt", "README.md"],
                "content": "Generated code based on: " + requirements
            }
        )
