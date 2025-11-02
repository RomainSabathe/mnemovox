from pathlib import Path

import httpx
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    audio_file = Path("/home/romain/Downloads/2023-12-23_11-10-23.mp3")
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "http://localhost:8001/transcribe",
            files={"audio_bytes": audio_file.open("rb")},
        )
    return r.json()
