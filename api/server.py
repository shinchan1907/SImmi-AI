from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import os
import secrets
from pathlib import Path
from redis import Redis

app = FastAPI(title="Simmi Agent API")
redis_client = Redis(host='localhost', port=6379, db=1) # Using DB 1 for temp links

STORAGE_PATH = Path("./storage")

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Simmi API is operational"}

@app.get("/download/{token}")
async def download_file(token: str):
    """Serve a file using a temporary token."""
    file_path = redis_client.get(f"download:{token}")
    if not file_path:
        raise HTTPException(status_code=404, detail="Link expired or invalid")
    
    path = Path(file_path.decode())
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(path)

def create_temp_link(file_path: str, expire_seconds: int = 600) -> str:
    """Create a temporary download link."""
    token = secrets.token_urlsafe(16)
    redis_client.setex(f"download:{token}", expire_seconds, file_path)
    # This URL should be the public URL of the server
    return f"https://your-domain.com/download/{token}"
