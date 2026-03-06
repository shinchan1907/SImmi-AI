from openai import OpenAI
import os
from pathlib import Path
from typing import Optional
from core.logger import get_logger
from core.security import decrypt_key

logger = get_logger("speech_to_text")

class WhisperSTT:
    def __init__(self, api_key: str):
        self.api_key = decrypt_key(api_key)
        self.client = OpenAI(api_key=self.api_key)

    def transcribe_audio(self, file_path: str) -> Optional[str]:
        self.log = logger.bind(file=file_path)
        self.log.info("transcribing_audio")
        
        try:
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
            self.log.info("transcription_completed")
            return transcript
        except Exception as e:
            self.log.error("transcription_failed", error=str(e))
            return None
