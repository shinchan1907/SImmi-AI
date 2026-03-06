import httpx
import asyncio
from fastapi import FastAPI, Request
import uvicorn
from core.agent import SimmiAgent
from core.logger import get_logger
from core.schemas import SimmiConfig
from core.security import decrypt_key
from integrations.speech_to_text import WhisperSTT
from integrations.tts_elevenlabs import ElevenLabsTTS
import threading
import subprocess
import os
from pathlib import Path

logger = get_logger("whatsapp")

class WhatsAppInterface:
    def __init__(self, config: SimmiConfig, agent: SimmiAgent):
        self.config = config
        self.agent = agent
        self.bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://localhost:3000")
        self.webhook_host = "0.0.0.0"
        self.webhook_port = 8001
        self.app = FastAPI()
        
        # Voice components
        self.stt = WhisperSTT(config.llm.api_key) if config.voice.enabled else None
        self.tts = ElevenLabsTTS(
            config.voice.elevenlabs_api_key, 
            config.voice.elevenlabs_voice_id
        ) if config.voice.enabled else None
        
        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/whatsapp/webhook")
        async def webhook(request: Request):
            try:
                data = await request.json()
                from_jid = data.get("from")
                text = data.get("text")
                audio_path = data.get("audio_path")
                is_voice = data.get("is_voice", False)
                push_name = data.get("pushName", "Unknown")
                
                log = logger.bind(user=from_jid, name=push_name)
                log.info("whatsapp_webhook_received", type=data.get("type"))
                
                # 1. Handle Voice Note Transcription
                if audio_path and self.stt:
                    log.info("transcribing_whatsapp_audio", path=audio_path)
                    # Convert to mp3 if needed (Whisper prefers mp3/m4a/wav)
                    # Baileys bridge might save as .ogg
                    processed_path = audio_path
                    if audio_path.endswith(".ogg"):
                        from pydub import AudioSegment
                        mp3_path = audio_path.replace(".ogg", ".mp3")
                        audio = AudioSegment.from_file(audio_path)
                        audio.export(mp3_path, format="mp3")
                        processed_path = mp3_path
                    
                    transcribed_text = self.stt.transcribe_audio(processed_path)
                    if transcribed_text:
                        text = transcribed_text
                        log.info("audio_transcribed", text=text)
                
                # 2. Authorization
                # For WhatsApp, we might use phone numbers or JIDs in the whitelist
                # For now, let's assume allowed_user_ids contains phone numbers or JIDs
                # If it's a list of ints, we might need a separate whatsapp whitelist
                # but standardizing on any list of authorized IDs is better.
                is_authorized = False
                for auth_id in self.config.telegram.allowed_user_ids:
                    if str(auth_id) in from_jid:
                        is_authorized = True
                        break
                
                if not is_authorized:
                    log.warning("unauthorized_whatsapp_access", jid=from_jid)
                    return {"status": "unauthorized"}

                # 3. Process with Agent
                user_id = from_jid 
                response_text = await self.agent.handle_message(user_id, text)
                
                # 3. Response: Voice or Text
                if self.config.voice.response_mode == "voice" and self.tts:
                    audio_reply_path = await self.tts.generate_voice(response_text)
                    if audio_reply_path:
                        await self.send_audio(from_jid, audio_reply_path, is_voice=True)
                    else:
                        await self.send_message(from_jid, response_text)
                else:
                    await self.send_message(from_jid, response_text)
                
                return {"status": "ok"}
            except Exception as e:
                logger.error("webhook_processing_failed", error=str(e))
                return {"status": "error", "message": str(e)}

    async def send_message(self, to_jid: str, text: str):
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{self.bridge_url}/send", json={
                    "to": to_jid,
                    "text": text
                }, timeout=30)
        except Exception as e:
            logger.error("whatsapp_send_failed", error=str(e))

    async def send_audio(self, to_jid: str, audio_path: str, is_voice: bool = True):
        try:
            # We need to ensure the bridge can access the file.
            # In local mode, we send the path. In Docker, we might need shared volumes.
            async with httpx.AsyncClient() as client:
                await client.post(f"{self.bridge_url}/send", json={
                    "to": to_jid,
                    "audio_path": str(Path(audio_path).absolute()),
                    "is_voice": is_voice
                }, timeout=30)
        except Exception as e:
            logger.error("whatsapp_audio_send_failed", error=str(e))

    def _start_bridge(self):
        """Starts the Node.js Baileys bridge in the background."""
        if os.getenv("DOCKER_ENV"):
            return # Let Docker handle the bridge
            
        logger.info("starting_baileys_bridge_process")
        bridge_path = Path("whatsapp_bridge")
        if not bridge_path.exists():
            logger.error("bridge_path_not_found")
            return

        # Start node bridge as a subprocess
        try:
            # Use shell=True for windows if node is in PATH
            subprocess.Popen(["node", "index.js"], cwd=bridge_path, shell=(os.name == 'nt'))
        except Exception as e:
            logger.error("bridge_start_failed", error=str(e))

    async def start(self):
        """Start the interface and its components."""
        # 1. Start Node Bridge locally if not in Docker
        self._start_bridge()
        
        # 2. Run Webhook Server
        config = uvicorn.Config(self.app, host=self.webhook_host, port=self.webhook_port, log_level="error")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        logger.info("whatsapp_interface_ready", host=self.webhook_host, port=self.webhook_port)
