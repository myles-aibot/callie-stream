import asyncio
import base64
import json
import os
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.applications import Starlette
from starlette.routing import WebSocketRoute
from openai import AsyncOpenAI
from agents import Agent
from agents.voice import VoicePipeline, AudioInput, SingleAgentVoiceWorkflow

openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

agent = Agent(
    name="Callie",
    instructions="You're a helpful, friendly receptionist. Greet the caller, ask how you can help, and respond in a natural voice.",
    model="gpt-4o"
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

    raw_audio = b''.join(audio_chunks)
    buffer = AudioInput.from_raw_bytes(raw_audio, sample_rate=8000)

    print("🧠 Running Callie pipeline on received audio...")

    result = await pipeline.run(buffer)

    async for event in result.stream():
        if event.type == "voice_stream_event_audio":
            print("🎤 Callie is speaking... (not returned to Twilio)")
            # We'll stream this back in a future step

routes = [
    WebSocketRoute("/media", handle_twilio_stream)
]

app = Starlette(debug=True, routes=routes)
