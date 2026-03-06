import httpx
import asyncio
from fastapi import FastAPI, Request
import uvicorn
from core.agent import SimmiAgent
from core.logger import get_logger
from core.schemas import SimmiConfig
import threading
import subprocess
import os

logger = get_logger("whatsapp")

class WhatsAppInterface:
    def __init__(self, config: SimmiConfig, agent: SimmiAgent):
        self.config = config
        self.agent = agent
        self.bridge_url = "http://localhost:3000"
        self.webhook_port = 8001
        self.app = FastAPI()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/whatsapp/webhook")
        async def webhook(request: Request):
            data = await request.json()
            from_jid = data.get("from")
            text = data.get("text")
            push_name = data.get("pushName", "Unknown")
            
            logger.info("whatsapp_message_received", user=from_jid, first_name=push_name)
            
            # Process with Agent
            # For simplicity, using a mock user ID based on JID
            user_id = int(from_jid.split("@")[0].split("-")[-1]) if "@" in from_jid else 0
            
            response_text = await self.agent.handle_message(user_id, text)
            
            # Send back to WhatsApp
            await self.send_message(from_jid, response_text)
            
            return {"status": "ok"}

    async def send_message(self, to_jid: str, text: str):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{self.bridge_url}/send", json={
                    "to": to_jid,
                    "text": text
                })
        except Exception as e:
            logger.error("whatsapp_send_failed", error=str(e))

    def _start_bridge(self):
        """Starts the Node.js Baileys bridge."""
        logger.info("starting_baileys_bridge")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        bridge_path = os.path.join(os.path.dirname(current_dir), "whatsapp_bridge")
        
        # Start node bridge as a subprocess
        subprocess.Popen(["node", "index.js"], cwd=bridge_path)

    def run(self):
        # 1. Start Node Bridge
        self._start_bridge()
        
        # 2. Run Webhook Server
        logger.info("starting_whatsapp_webhook_server", port=self.webhook_port)
        uvicorn.run(self.app, host="0.0.0.0", port=self.webhook_port, log_level="error")

    async def start(self):
        """Async version to run within main event loop."""
        # 1. Start Node Bridge
        self._start_bridge()
        
        # 2. Start Webhook Server in a separate thread because uvicorn.run is blocking
        # Alternatively, we could use uvicorn Config + Server and await its serve()
        config = uvicorn.Config(self.app, host="0.0.0.0", port=self.webhook_port, log_level="error")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        logger.info("whatsapp_interface_ready")
