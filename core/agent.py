import json
import re
import yaml
from typing import Dict, Any, List, Optional
from core.llm import LLMClient
from core.logger import get_logger
from memory.manager import MemoryManager
from core.schemas import SimmiConfig
from tools.base import ToolRegistry, ToolResult
from tools.core_tools import FileWriter, CodeGenerator
from core.orchestrator.manager import AgentOrchestrator

logger = get_logger("agent_core")

class SimmiAgent:
    def __init__(self, config: SimmiConfig):
        self.config = config
        self.llm = LLMClient(config.llm.provider, config.llm.api_key)
        self.memory = MemoryManager(config.database.url, config.database.redis_url)
        self._load_personality()
        
        # Tools
        self.registry = ToolRegistry()
        self.registry.register(FileWriter())
        self.registry.register(CodeGenerator())
        
        # Orchestrator
        self.orchestrator = AgentOrchestrator(self.llm, self.memory)

    def _load_personality(self):
        try:
            with open("config/personality.yaml", "r") as f:
                p = yaml.safe_load(f)
                self.personality_name = p.get("name", "Simmi")
                self.personality_owner = p.get("owner", "Sunny")
                self.personality_tone = p.get("tone", "playful but intelligent")
                self.personality_role = p.get("role", "assistant")
                self.personality_desc = p.get("description", "")
        except:
            self.personality_name = "Simmi"
            self.personality_owner = "Sunny"
            self.personality_tone = "playful"
            self.personality_role = "assistant"
            self.personality_desc = ""

    def _get_system_instruction(self, mem_context: str = "") -> str:
        tools_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in self.registry.list_tools()])
        return f"""
You are {self.personality_name}, a {self.personality_tone} autonomous AI agent.
Owner: {self.personality_owner}
Role: {self.personality_role}

{mem_context}

If a task is complex (e.g., 'build a website', 'create a SaaS'), use the specialized multi-agent system.
To activate the orchestrator, respond ONLY with: START_ORCHESTRATOR: <goal>

Otherwise, use your tools or chat:
AVAILABLE TOOLS:
{tools_desc}
...
"""

    async def handle_message(self, user_id: int, message: str) -> str:
        log = logger.bind(user_id=user_id)
        
        # Check for complex goal triggers
        if any(keyword in message.lower() for keyword in ["build", "create", "setup", "develop", "generate project"]):
            response = await self.orchestrator.plan_and_execute(user_id, message)
            return response

        # Standard handling...

        # 1. RETRIEVE context
        history = await self.memory.get_chat_history(user_id)
        query_embedding = await self.llm.get_embedding(message)
        relevant_mems = await self.memory.search_memory(user_id, query_embedding)
        
        mem_context = ""
        if relevant_mems:
            mem_context = "PAST CONTEXT & MEMORIES:\n" + "\n".join([f"- {m.content}" for m in relevant_mems])

        # 2. REASONING & PLANNING
        system_instruction = self._get_system_instruction(mem_context)
        
        # Initial thought/call
        response = await self.llm.generate_response(message, history, system_instruction)
        
        # 3. TOOL EXECUTION LOOP
        # Simple single-step tool detection for now
        tool_call_match = re.search(r"TOOL_CALL:\s*(\{.*\})", response)
        
        if tool_call_match:
            try:
                call_data = json.loads(tool_call_match.group(1))
                tool_name = call_data.get("tool")
                args = call_data.get("args", {})
                
                log.info("tool_call_detected", tool=tool_name, args=args)
                
                tool = self.registry.get_tool(tool_name)
                if tool:
                    # Execute tool
                    result: ToolResult = await tool.run(**args)
                    
                    # 4. RESPONSE SYNTHESIS
                    synthesis_prompt = f"""
                    The user said: "{message}"
                    You called tool '{tool_name}' with args {args}.
                    Tool Result Status: {result.status}
                    Tool Result Data: {result.result}
                    Tool Error: {result.error}
                    
                    Provide a final response to the user based on this outcome.
                    """
                    final_response = await self.llm.generate_response(synthesis_prompt, history, system_instruction)
                    response = final_response
                else:
                    response = f"I tried to use a tool named '{tool_name}' but I couldn't find it in my toolbox."
            except Exception as e:
                log.error("tool_execution_failed", error=str(e))
                response = f"I encountered an error while trying to execute a tool: {str(e)}"

        # 5. STORE
        await self.memory.add_chat_history(user_id, "user", message)
        await self.memory.add_chat_history(user_id, "assistant", response)
        
        # Auto-memory: If the user explicitly asks to remember
        if "remember" in message.lower():
            fact = message.lower().replace("remember", "").strip()
            emb = await self.llm.get_embedding(fact)
            await self.memory.store_memory(user_id, fact, emb, "fact")
            log.info("fact_remembered", fact=fact)
            
        return response
