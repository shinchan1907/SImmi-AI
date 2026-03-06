from typing import List, Dict, Any, Optional
import os
from pathlib import Path
from core.llm import LLMClient
from memory.manager import MemoryManager
from core.logger import get_logger

logger = get_logger("prompt_optimizer")

class PromptOptimizer:
    def __init__(self, llm: LLMClient, memory: MemoryManager):
        self.llm = llm
        self.memory = memory
        self.prompt_dir = Path("config/prompts")
        self.prompt_dir.mkdir(parents=True, exist_ok=True)

    async def optimize_agent_prompt(self, agent_name: str, performance_data: List[Dict[str, Any]], current_prompt: str):
        """
        Generates an improved version of an agent's system prompt.
        """
        self.log = logger.bind(agent=agent_name)
        self.log.info("prompt_optimization_started")

        perf_summary = str(performance_data)
        optimization_prompt = f"""
        Current System Prompt for {agent_name}:
        ---
        {current_prompt}
        ---

        Performance Feedback & Failures:
        {perf_summary}

        Task: Generate an improved version of this system prompt that addresses the identified failures and inefficiencies.
        Focus on:
        - Better reasoning instructions
        - Clearer output format constraints
        - Specific edge-case handling

        Output ONLY the improved system prompt text.
        """

        try:
            improved_prompt = await self.llm.generate_response(optimization_prompt)
            
            # Save to disk
            version_file = self.prompt_dir / f"{agent_name.lower()}_v.txt"
            # This is a simplification; a real versioning system would use timestamps/v numbers
            with open(version_file, "w") as f:
                f.write(improved_prompt)

            self.log.info("prompt_optimization_completed")
            return improved_prompt
        except Exception as e:
            self.log.error("prompt_optimization_failed", error=str(e))
            return None
