import asyncio
import base64
import json
import os
import numpy as np

from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute

from openai import AsyncOpenAI
from agents.voice import AudioInput, VoicePipeline, SingleAgentVoiceWorkflow
from agents import Agent

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🔁 Manual replacement for deprecated AudioInput.from_raw_bytes()
def from_raw_bytes(raw_bytes: bytes, sample_rate: int = 8000) -> AudioInput:
    buffer = np.frombuffer(raw_bytes, dtype=np.int16)
    return AudioInput(buffer=buffer, frame_rate=sample_rate)

# 🎙️ Define your GPT-4o voice agent
agent = Agent(
    name="Callie",
    instructions="You're a helpful receptionist. Greet the caller and ask how you can help.",
    model="gpt-4o",
)
agent.voice = "alloy"

pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))

async def handle_twilio_stream(websocket: WebSocket):
    await websocket.accept()
    print("📞 Twilio stream connected")

    audio_chunks = []

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("event") == "media":
                chunk_b64 = data["media"]["payload"]
                audio_chunk = base64.b64decode(chunk_b64)
                audio_chunks.append(audio_chunk)

            if data.get("event") == "stop":
                print("📴 Stream ended")
                break

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")

    # 🧠 Process audio with Callie
    raw_audio = b"".join(audio_chunks)
    buffer = from_raw_bytes(raw_audio, sample_rate=8000)

    print("🧠 Running Callie pipeline on received audio...")
    result = await pipeline.run(buffer)

    # For now, just log the audio event (we’ll send it to Twilio soon)
    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            print("🎤 Callie is speaking...")

routes = [
    WebSocketRoute("/media", handle_twilio_stream)
]

app = Starlette(debug=True, routes=routes)
