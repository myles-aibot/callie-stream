import asyncio
import base64
import json
import os

from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from openai import AsyncOpenAI

# Import from vendored local agents-sdk
from agents_sdk import Agent
from agents_sdk.voice import VoicePipeline, AudioInput, SingleAgentVoiceWorkflow

# Initialize OpenAI client
openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define your agent
agent = Agent(
    name="Callie",
    instructions=(
        "You're a helpful, friendly receptionist. Greet the caller, ask how you can help, "
        "and respond in a natural voice."
    ),
    model="gpt-4o"
)

# Set voice
agent.voice = "alloy"

# Set up the voice pipeline
pipeline = VoicePipeline(workflow=SingleAgentVoiceWorkflow(agent))

# WebSocket handler
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
            print("🔊 Responding with audio (not yet returned to Twilio)")
            # You’ll return audio back to Twilio in the next stage

# Setup WebSocket route
routes = [
    WebSocketRoute("/media", handle_twilio_stream)
]

app = Starlette(debug=True, routes=routes)
