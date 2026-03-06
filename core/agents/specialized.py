from .base import BaseAgent
from core.llm import LLMClient

class PlannerAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        prompt = """You are the PlannerAgent for the Simmi Agent platform.
Your job is to break down complex user requests into a Directed Acyclic Graph (DAG) of actionable tasks.
Each task should have a clear ID, description, and dependencies.
Output MUST be in JSON format: {"tasks": [{"id": "task1", "description": "...", "dependencies": []}]}.
Focus on logical flow and parallelism where possible."""
        super().__init__("Planner", "Task Planner", llm, prompt)

    def get_specialized_prompt(self) -> str:
        return self.system_prompt

class CoderAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        prompt = """You are the CoderAgent. Your job is to write high-quality, production-ready code.
Follow best practices for the requested language. Organize code into proper file structures.
Output code blocks clearly labeled with filenames."""
        super().__init__("Coder", "Software Engineer", llm, prompt)

    def get_specialized_prompt(self) -> str:
        return self.system_prompt

class ResearchAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        prompt = """You are the ResearchAgent. Your job is to gather information, search documentation, and find best practices.
Provide concise but comprehensive summaries of your findings."""
        super().__init__("Researcher", "Information Specialist", llm, prompt)

    def get_specialized_prompt(self) -> str:
        return self.system_prompt

class DebuggerAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        prompt = """You are the DebuggerAgent. Your job is to analyze error logs and fix broken code.
You will receive code snippets and their corresponding error outputs from a sandbox.
Identify the root cause and provide the corrected version."""
        super().__init__("Debugger", "QA & Fix Specialist", llm, prompt)

    def get_specialized_prompt(self) -> str:
        return self.system_prompt

class SecurityAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        prompt = """You are the SecurityAgent. Your job is to audit code for vulnerabilities, secrets exposure, and insecure patterns.
Ensure everything generated follows security hardening standards."""
        super().__init__("Security", "Security Auditor", llm, prompt)

    def get_specialized_prompt(self) -> str:
        return self.system_prompt

class DevOpsAgent(BaseAgent):
    def __init__(self, llm: LLMClient):
        prompt = """You are the DevOpsAgent. Your job is to prepare deployment configurations, Dockerfiles, and CI/CD pipelines.
Focus on containerization and cloud-ready setups."""
        super().__init__("DevOps", "Infrastructure Engineer", llm, prompt)

    def get_specialized_prompt(self) -> str:
        return self.system_prompt
