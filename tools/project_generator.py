import os
import zipfile
import uuid
from typing import List, Dict, Any
from tools.base import BaseTool, ToolResult
from core.logger import get_logger

logger = get_logger("project_tool")

class ProjectGenerator(BaseTool):
    @property
    def name(self) -> str:
        return "project_generator"

    @property
    def description(self) -> str:
        return "Generates a complete project structure with multiple files. Args: project_name (str), files (Dict[str, str])"

    async def run(self, project_name: str, files: Dict[str, str], storage_path: str = "./storage/projects") -> ToolResult:
        try:
            task_id = str(uuid.uuid4())[:8]
            project_dir = os.path.join(storage_path, f"{project_name}_{task_id}")
            os.makedirs(project_dir, exist_ok=True)

            created_files = []
            for filepath, content in files.items():
                full_path = os.path.join(project_dir, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                created_files.append(filepath)

            # Create ZIP
            zip_path = f"{project_dir}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, filenames in os.walk(project_dir):
                    for filename in filenames:
                        file_full_path = os.path.join(root, filename)
                        arcname = os.path.relpath(file_full_path, project_dir)
                        zipf.write(file_full_path, arcname)

            return ToolResult(
                status="success",
                result={
                    "project_dir": project_dir,
                    "zip_path": zip_path,
                    "files_created": created_files,
                    "download_url": f"/download/{os.path.basename(zip_path)}" # Placeholder
                }
            )
        except Exception as e:
            logger.error("project_generation_failed", error=str(e))
            return ToolResult(status="error", result=None, error=str(e))
