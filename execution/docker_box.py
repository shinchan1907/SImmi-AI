import docker
import os

class SandboxExecutor:
    def __init__(self):
        self.client = docker.from_env()

    async def execute_python(self, code: str, timeout: int = 30):
        """Runs python code inside a secure Docker container."""
        try:
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=f'python -c "{code}"',
                detach=True,
                mem_limit="128m",
                cpu_quota=50000, # 50% of one CPU
                network_disabled=True,
                # read_only=True # Should be careful with this if code needs to write temp files
            )
            
            result = container.wait(timeout=timeout)
            output = container.logs().decode()
            container.remove()
            
            return {
                "exit_code": result["StatusCode"],
                "output": output
            }
        except Exception as e:
            return {"error": str(e)}
