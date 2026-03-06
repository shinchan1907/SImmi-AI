import json
from typing import List, Dict, Any, Optional
from core.agents.specialized import PlannerAgent, CoderAgent, ResearchAgent, DebuggerAgent, SecurityAgent, DevOpsAgent
from core.tasks.models import Task, TaskGraph, TaskStatus
from core.llm import LLMClient
from core.logger import get_logger
from core.evolution.reflection import ReflectionEngine
from memory.manager import MemoryManager

logger = get_logger("orchestrator")

class AgentOrchestrator:
    def __init__(self, llm: LLMClient, memory: MemoryManager):
        self.llm = llm
        self.memory = memory
        self.planner = PlannerAgent(llm)
        self.coder = CoderAgent(llm)
        self.researcher = ResearchAgent(llm)
        self.debugger = DebuggerAgent(llm)
        self.security = SecurityAgent(llm)
        self.devops = DevOpsAgent(llm)
        
        self.reflector = ReflectionEngine(llm, memory)
        
        self.agent_map = {
            "planner": self.planner,
            "coder": self.coder,
            "researcher": self.researcher,
            "debugger": self.debugger,
            "security": self.security,
            "devops": self.devops
        }

    async def plan_and_execute(self, user_id: int, goal: str):
        # 1. RETRIEVE PAST EXPERIENCES
        self.log = logger.bind(user_id=user_id, goal=goal[:50])
        self.log.info("searching_experience_memory")
        
        goal_emb = await self.llm.get_embedding(goal)
        past_experiences = await self.memory.search_experiences(goal_emb)
        exp_context = "\n".join([f"- Past Task: {e.task_description}\n  Approach: {e.approach}\n  Status: {e.status}" for e in past_experiences])

        # 2. PLAN with Experience context
        self.log.info("creating_execution_plan")
        prompt = f"Goal: {goal}\n\nPast Experience Context:\n{exp_context if exp_context else 'None'}"
        plan_raw = await self.planner.chat(user_id, prompt)
        
        try:
            json_str = plan_raw.strip()
            if json_str.startswith("```json"): json_str = json_str[7:-3].strip()
            elif json_str.startswith("```"): json_str = json_str[3:-3].strip()
            plan_data = json.loads(json_str)
            graph = self._build_graph(plan_data)
        except Exception as e:
            self.log.error("plan_parsing_failed", error=str(e), raw=plan_raw)
            return f"I had trouble creating a plan: {str(e)}"

        # 3. EXECUTE DAG
        final_result = await self._execute_graph(user_id, graph)

        # 4. REFLECTION
        history = [{"task": t.description, "result": t.result, "status": t.status, "error": t.error} for t in graph.tasks.values()]
        await self.reflector.reflect_on_task(graph.id, goal, history)

        return final_result

    def _build_graph(self, plan_data: Dict[str, Any]) -> TaskGraph:
        graph = TaskGraph()
        for t_data in plan_data.get("tasks", []):
            task = Task(
                id=t_data.get("id"),
                description=t_data.get("description"),
                dependencies=t_data.get("dependencies", []),
                agent_assigned=t_data.get("agent", "coder") # Fallback to coder
            )
            graph.tasks[task.id] = task
        return graph

    async def _execute_graph(self, user_id: int, graph: TaskGraph):
        max_iterations = 20
        iteration = 0
        
        while not graph.is_complete() and not graph.has_failed() and iteration < max_iterations:
            ready_tasks = graph.get_ready_tasks()
            if not ready_tasks:
                break
            
            for task in ready_tasks:
                task.status = TaskStatus.RUNNING
                agent = self.agent_map.get(task.agent_assigned, self.coder)
                
                self.log.info("executing_task", task_id=task.id, agent=agent.name)
                
                # SELF-CORRECTION LOOP (RETRIES)
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        context = self._get_task_context(graph, task)
                        prompt = f"Task: {task.description}\n\nContext:\n{context}"
                        if attempt > 0:
                            prompt += f"\n\nERROR FROM PREVIOUS ATTEMPT:\n{task.error}\nPlease fix the issues and provide the correct solution."

                        result = await agent.chat(user_id, prompt)
                        
                        # If the task involves code, we might want to validate it in sandbox
                        # This is a simplification; in a real system we'd check if the task 'type' is code
                        if "sandbox" in task.metadata.get("execution_type", ""):
                            # Use SandboxExecutor here (Mocking call for now)
                            # sandbox_result = await self.sandbox.execute_python(extracted_code)
                            # if sandbox_result['exit_code'] != 0:
                            #     raise Exception(f"Sandbox Error: {sandbox_result['output']}")
                            pass

                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        task.error = None
                        break # Success
                        
                    except Exception as e:
                        task.error = str(e)
                        self.log.warn("task_attempt_failed", task_id=task.id, attempt=attempt+1, error=str(e))
                        if attempt == max_retries - 1:
                            task.status = TaskStatus.FAILED
                            self.log.error("task_execution_failed_final", task_id=task.id, error=str(e))
            
            iteration += 1

        if graph.has_failed():
            return "The execution plan failed at some step. Please check the logs."
        
        return self._synthesize_final_result(graph)

    def _get_task_context(self, graph: TaskGraph, task: Task) -> str:
        context = ""
        for dep_id in task.dependencies:
            dep_task = graph.tasks.get(dep_id)
            if dep_task:
                context += f"Result from {dep_id} ({dep_task.description}):\n{dep_task.result}\n\n"
        return context

    def _synthesize_final_result(self, graph: TaskGraph) -> str:
        # Simple synthesis: return results of tasks without further dependencies (leaves)
        # Or just the last completed task.
        results = []
        for task in graph.tasks.values():
            results.append(f"### {task.description}\n{task.result}")
        return "\n\n".join(results)
