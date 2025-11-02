from typing import Annotated

from fastapi import FastAPI, File

app = FastAPI()


@app.get("/")
async def root():
    return {}


@app.post("/transcribe")
async def transcribe(audio_bytes: Annotated[bytes, File()]):
    return {"message": f"Got the file! First bytes: {audio_bytes[:10]}"}
