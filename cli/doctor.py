import asyncio
import yaml
import httpx
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine
from pathlib import Path
import docker
from typing import Dict, Any
from core.security import SecurityManager

from sqlalchemy import text

async def check_postgres(url: str) -> Dict[str, Any]:
    try:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def check_redis(url: str) -> Dict[str, Any]:
    try:
        client = redis.from_url(url)
        await client.ping()
        return {"status": "ok", "message": "Connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_docker() -> Dict[str, Any]:
    try:
        client = docker.from_env()
        client.ping()
        return {"status": "ok", "message": f"Docker Engine {client.version()['Version']}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def check_telegram(bot_token: str) -> Dict[str, Any]:
    try:
        sm = SecurityManager()
        token = sm.decrypt(bot_token)
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if response.status_code == 200:
                data = response.json()
                bot_name = data["result"]["first_name"]
                return {"status": "ok", "message": f"Valid (as {bot_name})"}
            else:
                return {"status": "error", "message": f"Invalid Token (HTTP {response.status_code})"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def check_api_server() -> Dict[str, Any]:
    try:
        # Check if local FastAPI is running (default port 8000)
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=1.0)
            if response.status_code == 200:
                return {"status": "ok", "message": "Operational"}
        return {"status": "warning", "message": "FastAPI Health Check Failed"}
    except:
        return {"status": "warning", "message": "Not running (start with 'simmi start')"}

async def check_whatsapp() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3000/status", timeout=1.0)
            if response.status_code == 200:
                data = response.json()
                if data.get("connected"):
                    return {"status": "ok", "message": f"Linked: {data.get('number')}"}
                return {"status": "warning", "message": "Bridge up but NOT linked"}
        return {"status": "error", "message": "Bridge error"}
    except:
        return {"status": "error", "message": "Bridge not responding"}

async def check_voice(config: dict) -> Dict[str, Any]:
    if not config.get("voice", {}).get("enabled"):
        return {"status": "error", "message": "Disabled"}
    if config.get("voice", {}).get("elevenlabs_api_key"):
        return {"status": "ok", "message": "Ready (ElevenLabs)"}
    return {"status": "warning", "message": "Enabled but NO API KEY"}

async def run_diagnostics() -> Dict[str, Any]:
    config_path = Path("config/config.yaml")
    results = {}
    
    if not config_path.exists():
        return {"config": {"status": "error", "message": "config.yaml not found"}}
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        return {"config": {"status": "error", "message": f"Failed to parse: {str(e)}"}}
    
    results["PostgreSQL"] = await check_postgres(config["database"]["url"])
    results["Redis"] = await check_redis(config["database"]["redis_url"])
    results["Telegram"] = await check_telegram(config["telegram"]["bot_token"])
    results["WhatsApp"] = await check_whatsapp()
    results["Voice"] = await check_voice(config)
    results["Docker"] = check_docker()
    results["API Server"] = await check_api_server()
    
    return results
