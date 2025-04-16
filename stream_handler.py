import asyncio
import base64
import json
import os
import sys

# ✅ Add the vendored SDK to Python's path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "agents-sdk/src")))

from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from openai import AsyncOpenAI
from agents import Agent
from agents.voice import VoicePipeline, AudioInput, SingleAgentVoiceWorkflow

# 🔑 OpenAI Client
openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🤖 Define Callie Agent
agent = Agent(
    name="Callie",
    instructions="You're a helpful, friendly receptionist named Callie. Greet callers, ask what they need help with, and respond in a natural, polite voice.",
    model="gpt-4o"
)
agent.voice = "alloy"

# 🔁 Voice Pipeline
pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))

# 🎧 Twilio Media Stream Handler
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

            elif data.get("event") == "stop":
                print("📴 Stream ended")
                break

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")

    raw_audio = b''.join(audio_chunks)

    try:
        buffer = AudioInput.from_raw_bytes(raw_audio, sample_rate=8000)
        print("🧠 Running Callie pipeline on received audio...")

        result = await pipeline.run(buffer)

        async for event in result.stream():
            if event.type == "voice_stream_event_audio":
                print("🎤 Callie is speaking...")

    except Exception as e:
        print("❌ Error during audio processing:", e)

# 🌐 WebSocket Route
routes = [
    WebSocketRoute("/media", handle_twilio_stream)
]

app = Starlette(debug=True, routes=routes)
