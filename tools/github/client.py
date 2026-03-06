from github import Github
from tools.base import BaseTool, ToolResult
from core.logger import get_logger
import os

logger = get_logger("github_tool")

class GitHubManager(BaseTool):
    @property
    def name(self) -> str:
        return "github_manager"

    @property
    def description(self) -> str:
        return "Manages GitHub repositories (create, push). Args: action (str), repo_name (str), files (Dict[str, str]), token (str)"

    async def run(self, action: str, repo_name: str, token: str, files: dict = None, description: str = "") -> ToolResult:
        try:
            g = Github(token)
            user = g.get_user()

            if action == "create":
                repo = user.create_repo(repo_name, description=description, private=True)
                
                if files:
                    for path, content in files.items():
                        repo.create_file(path, f"Initial commit: {path}", content)
                
                return ToolResult(status="success", result={"url": repo.html_url, "full_name": repo.full_name})
            
            elif action == "push":
                repo = g.get_repo(repo_name)
                if files:
                    for path, content in files.items():
                        # This is a simple push (creates/updates)
                        try:
                            contents = repo.get_contents(path)
                            repo.update_file(path, f"Update: {path}", content, contents.sha)
                        except:
                            repo.create_file(path, f"Create: {path}", content)
                return ToolResult(status="success", result=f"Successfully pushed to {repo_name}")

            return ToolResult(status="error", result=None, error=f"Unknown action: {action}")
        except Exception as e:
            logger.error("github_action_failed", action=action, error=str(e))
            return ToolResult(status="error", result=None, error=str(e))
