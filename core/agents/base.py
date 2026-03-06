from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.llm import LLMClient
from core.logger import get_logger

logger = get_logger("agent_base")

class BaseAgent(ABC):
    def __init__(self, name: str, role: str, llm: LLMClient, system_prompt: str):
        self.name = name
        self.role = role
        self.llm = llm
        self.system_prompt = system_prompt
        self.log = logger.bind(agent=name, role=role)

    async def chat(self, user_id: int, message: str, history: List[Dict[str, str]] = None) -> str:
        self.log.info("agent_chat_started", message=message)
        response = await self.llm.generate_response(message, history, self.system_prompt)
        self.log.info("agent_chat_completed", response_length=len(response))
        return response

    @abstractmethod
    def get_specialized_prompt(self) -> str:
        """Return the specialized prompt for this agent."""
        pass
