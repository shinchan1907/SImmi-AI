import httpx
import os
import uuid
import yaml
from typing import Optional
from pathlib import Path
from core.logger import get_logger
from core.security import decrypt_key

logger = get_logger("tts_elevenlabs")

class ElevenLabsTTS:
    def __init__(self, api_key: str, voice_id: str):
        self.api_key = decrypt_key(api_key)
        self.voice_id = voice_id
        self.base_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        self.storage_path = Path("storage/audio")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load settings if exists
        self.stability = 0.5
        self.similarity_boost = 0.75
        self._load_voice_settings()

    def _load_voice_settings(self):
        voice_config = Path("config/voice.yaml")
        if voice_config.exists():
            with open(voice_config, "r") as f:
                config = yaml.safe_load(f)
                self.stability = config.get("stability", self.stability)
                self.similarity_boost = config.get("similarity_boost", self.similarity_boost)

    async def generate_voice(self, text: str) -> Optional[str]:
        self.log = logger.bind(text_length=len(text))
        self.log.info("generating_speech")
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, headers=headers, json=data, timeout=60)
                
                if response.status_code == 200:
                    file_name = f"simmi_{uuid.uuid4().hex}.mp3"
                    file_path = self.storage_path / file_name
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                    self.log.info("speech_generated", path=str(file_path))
                    return str(file_path)
                else:
                    self.log.error("elevenlabs_api_error", status=response.status_code, detail=response.text)
                    return None
        except Exception as e:
            self.log.error("tts_failed", error=str(e))
            return None
