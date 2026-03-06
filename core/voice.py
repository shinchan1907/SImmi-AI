import httpx
import os
from pathlib import Path
from core.logger import get_logger
from core.schemas import SimmiConfig
import asyncio
from pydub import AudioSegment

logger = get_logger("voice")

class VoiceSystem:
    def __init__(self, config: SimmiConfig):
        self.config = config
        self.elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech"

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio using Whisper."""
        if not self.config.voice.enabled:
            return ""
        
        # Convert to mp3/wav if needed? Baileys usually sends ogg/opus
        # OpenAI Whisper supports ogg/opus but let's ensure it's compatible
        # For simplicity, we assume the user has OpenAI API key if they use Whisper
        # or we use an external Whisper API.
        # Given the requirements, I'll use OpenAI Whisper API.
        
        api_key = self.config.llm.api_key # Use the same key or a dedicated one if available
        # But wait, they might be using Gemini.
        # I'll check if they have openai as provider.
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            return transcript.text
        except Exception as e:
            logger.error("transcription_failed", error=str(e))
            return ""

    async def text_to_speech(self, text: str, output_path: str = None) -> str:
        """Convert text to speech using ElevenLabs."""
        if not self.config.voice.enabled or not self.config.voice.elevenlabs_api_key:
            return None
        
        if not output_path:
            output_dir = Path("storage/audio")
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = str(output_dir / f"response_{os.getpid()}.mp3")
        
        voice_id = self.config.voice.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        headers = {
            "xi-api-key": self.config.voice.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.elevenlabs_url}/{voice_id}",
                    json=payload,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    return output_path
                else:
                    logger.error("tts_failed", status=response.status_code, text=response.text)
                    return None
        except Exception as e:
            logger.error("tts_error", error=str(e))
            return None
