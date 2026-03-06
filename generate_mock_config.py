import yaml
from core.security import SecurityManager
from pathlib import Path

sm = SecurityManager()

config = {
    "personality": {
        "name": "Simmi",
        "owner": "Sunny",
        "tone": "playful but intelligent",
        "role": "personal AI assistant and executor",
        "description": "A highly capable autonomous agent."
    },
    "llm": {
        "provider": "gemini",
        "api_key": sm.encrypt("GEMINI_MOCK_KEY")
    },
    "telegram": {
        "bot_token": sm.encrypt("TELEGRAM_MOCK_TOKEN"),
        "allowed_user_ids": [123456789]
    },
    "database": {
        "url": "postgresql+asyncpg://postgres:password@localhost:5432/simmiadb",
        "redis_url": "redis://localhost:6379/0"
    },
    "whatsapp": {
        "enabled": False,
        "mode": "none"
    },
    "voice": {
        "enabled": False,
        "elevenlabs_api_key": None,
        "elevenlabs_voice_id": None,
        "response_mode": "text"
    },
    "storage_path": "./storage"
}

with open("config/config.yaml", "w") as f:
    yaml.dump(config, f)

print("Config generated successfully!")
