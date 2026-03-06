import json
from typing import List, Dict, Any
from core.llm import LLMClient
from memory.manager import MemoryManager
from core.logger import get_logger

logger = get_logger("reflection_engine")

class ReflectionEngine:
    def __init__(self, llm: LLMClient, memory: MemoryManager):
        self.llm = llm
        self.memory = memory

    async def reflect_on_task(self, task_id: str, goal: str, execution_history: List[Dict[str, Any]]):
        """
        Analyzes a completed task to extract lessons and improvements.
        """
        self.log = logger.bind(task_id=task_id)
        self.log.info("task_reflection_started")

        # Construct reflection prompt
        history_str = json.dumps(execution_history, indent=2)
        prompt = f"""
        Review the following completed task execution.
        Goal: {goal}
        Execution History:
        {history_str}

        Analyze the process and provide:
        1. Observations: What went well? What were the bottlenecks?
        2. Lessons Learned: What strategy should be used next time?
        3. Improvement Plan: specific suggestions for prompt optimization or tool changes.

        Format: JSON with fields 'observations', 'lessons_learned', 'improvement_plan'.
        """

        try:
            response = await self.llm.generate_response(prompt)
            # Clean JSON
            json_str = response.strip()
            if json_str.startswith("```json"): json_str = json_str[7:-3].strip()
            data = json.loads(json_str)

            # Store in DB
            await self.memory.store_reflection(
                task_id=task_id,
                observations=data.get("observations", ""),
                lessons=data.get("lessons_learned", ""),
                plan=data.get("improvement_plan", "")
            )
            
            # Store as Experience too
            status = "success" if "error" not in history_str.lower() else "failure"
            emb = await self.llm.get_embedding(goal)
            await self.memory.store_experience(
                task=goal,
                approach=data.get("lessons_learned", ""),
                result="See Reflection",
                status=status,
                embedding=emb
            )

            self.log.info("task_reflection_completed")
            return data
        except Exception as e:
            self.log.error("reflection_failed", error=str(e))
            return None
