import sys
import os
import asyncio
import base64
import json

from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from openai import AsyncOpenAI

# 🔧 Force Python to use the vendored agents-sdk instead of pip version
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "agents-sdk")))

# ✅ Import from vendored SDK (no prefix needed now)
from agents import Agent
from agents.voice import VoicePipeline, AudioInput, SingleAgentVoiceWorkflow

# 🔐 OpenAI client
openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 🤖 Define Callie
agent = Agent(
    name="Callie",
    instructions="You're a helpful, friendly receptionist. Greet the caller, ask how you can help, and respond in a natural voice.",
    model="gpt-4o"
)
agent.voice = "alloy"

pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))

# 🎙️ WebSocket Handler
async def handle_twilio_stream(websocket: WebSocket):
    await websocket.accept()
    print("📞 Twilio stream connected")

    audio_chunks = []

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)

            if data.get("event") == "media":
                audio_chunk = base64.b64decode(data["media"]["payload"])
                audio_chunks.append(audio_chunk)

            if data.get("event") == "stop":
                print("📴 Stream ended")
                break

    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")

    raw_audio = b"".join(audio_chunks)
    buffer = AudioInput.from_raw_bytes(raw_audio, sample_rate=8000)

    print("🧠 Running Callie pipeline...")

    result = await pipeline.run(buffer)

    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            print("🔊 Callie is speaking... (not returned to Twilio yet)")
            # In future: stream back to Twilio here

# 🛣️ Set up the WebSocket route
routes = [
    WebSocketRoute("/media", handle_twilio_stream)
]

app = Starlette(debug=True, routes=routes)
