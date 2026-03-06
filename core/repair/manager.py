import traceback
import sys
from typing import Optional
from core.llm import LLMClient
from core.logger import get_logger
from execution.docker_box import SandboxExecutor

logger = get_logger("self_repair")

class SelfRepairManager:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.sandbox = SandboxExecutor()

    async def attempt_repair(self, error_trace: str, context_code: Optional[str] = None):
        """
        Analyzes a system error and attempts to generate a patch.
        """
        self.log = logger.bind(event="repair_attempt")
        self.log.info("detecting_fault")

        prompt = f"""
        A system error occurred in the Simmi Agent framework.
        Error Traceback:
        {error_trace}
        
        Relevant Code:
        {context_code if context_code else "Not provided."}

        Task: Analyze the error and provide a Python patch to fix it.
        Return ONLY the corrected python code or the patch logic.
        """

        try:
            fix_suggestion = await self.llm.generate_response(prompt)
            
            # test in sandbox first
            test_result = await self.sandbox.execute_python(fix_suggestion)
            
            if test_result.get("exit_code") == 0:
                self.log.info("repair_validated_in_sandbox")
                return fix_suggestion
            else:
                self.log.warn("repair_failed_validation", error=test_result.get("output"))
                return None
        except Exception as e:
            self.log.error("repair_system_failed", error=str(e))
            return None
