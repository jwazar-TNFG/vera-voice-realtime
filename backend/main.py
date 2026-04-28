"""
Vera Voice Realtime - WebSocket relay to OpenAI Realtime API
Sub-second latency voice conversations
"""

import asyncio
import json
import base64
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import websockets
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"

app = FastAPI(title="Vera Voice Realtime API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vera's system prompt
VERA_SYSTEM_PROMPT = """You are Vera, an AI executive assistant. Your personality:

- Warm, professional, and concise
- You speak naturally, like a helpful colleague
- Keep responses SHORT (1-3 sentences) since this is a voice conversation
- Be direct and efficient - no filler words
- If asked about data you don't have access to, say you're in demo mode

You're having a real-time voice conversation. Respond conversationally."""


@app.get("/")
async def root():
    return {"status": "ok", "service": "Vera Voice Realtime API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(client_ws: WebSocket):
    """
    WebSocket endpoint that relays audio between browser and OpenAI Realtime API
    """
    await client_ws.accept()
    print("Client connected")
    
    openai_ws = None
    
    try:
        # Connect to OpenAI Realtime API
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        openai_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            extra_headers=headers
        )
        print("Connected to OpenAI Realtime API")
        
        # Configure the session
        session_config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": VERA_SYSTEM_PROMPT,
                "voice": "shimmer",  # Options: alloy, echo, fable, onyx, nova, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                }
            }
        }
        await openai_ws.send(json.dumps(session_config))
        print("Session configured")
        
        # Create tasks for bidirectional relay
        async def relay_client_to_openai():
            """Relay messages from browser to OpenAI"""
            try:
                while True:
                    data = await client_ws.receive_text()
                    message = json.loads(data)
                    
                    if message.get("type") == "audio":
                        # Forward audio to OpenAI
                        audio_event = {
                            "type": "input_audio_buffer.append",
                            "audio": message.get("audio")  # base64 PCM16
                        }
                        await openai_ws.send(json.dumps(audio_event))
                    
                    elif message.get("type") == "commit":
                        # Commit the audio buffer (user finished speaking)
                        await openai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                        await openai_ws.send(json.dumps({"type": "response.create"}))
                    
                    elif message.get("type") == "interrupt":
                        # User interrupted - cancel current response
                        await openai_ws.send(json.dumps({"type": "response.cancel"}))
                    
                    elif message.get("type") == "text":
                        # Text message from user
                        text = message.get("text", "")
                        print(f"User text: {text}")
                        
                        # Send text as conversation item
                        conversation_item = {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "user",
                                "content": [{
                                    "type": "input_text",
                                    "text": text
                                }]
                            }
                        }
                        await openai_ws.send(json.dumps(conversation_item))
                        
                        # Trigger response
                        await openai_ws.send(json.dumps({"type": "response.create"}))
                        
            except WebSocketDisconnect:
                print("Client disconnected")
            except Exception as e:
                print(f"Client relay error: {e}")
        
        async def relay_openai_to_client():
            """Relay messages from OpenAI to browser"""
            try:
                async for message in openai_ws:
                    event = json.loads(message)
                    event_type = event.get("type")
                    
                    # Log all events for debugging
                    if event_type not in ["response.audio.delta", "response.audio_transcript.delta"]:
                        print(f"OpenAI event: {event_type}")
                    
                    # Forward relevant events to client
                    if event_type == "response.audio.delta":
                        # Audio chunk from OpenAI
                        await client_ws.send_text(json.dumps({
                            "type": "audio",
                            "audio": event.get("delta")
                        }))
                    
                    elif event_type == "response.audio_transcript.delta":
                        # Transcript of what Vera is saying
                        await client_ws.send_text(json.dumps({
                            "type": "transcript",
                            "text": event.get("delta")
                        }))
                    
                    elif event_type == "input_audio_buffer.speech_started":
                        # User started speaking
                        await client_ws.send_text(json.dumps({
                            "type": "speech_started"
                        }))
                    
                    elif event_type == "input_audio_buffer.speech_stopped":
                        # User stopped speaking
                        await client_ws.send_text(json.dumps({
                            "type": "speech_stopped"
                        }))
                    
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        # User's speech transcription
                        transcript_text = event.get("transcript", "")
                        print(f"User said: {transcript_text}")
                        await client_ws.send_text(json.dumps({
                            "type": "user_transcript",
                            "text": transcript_text
                        }))
                    
                    elif event_type == "response.audio.done":
                        # Vera finished speaking
                        await client_ws.send_text(json.dumps({
                            "type": "response_done"
                        }))
                    
                    elif event_type == "error":
                        print(f"OpenAI error: {event}")
                        await client_ws.send_text(json.dumps({
                            "type": "error",
                            "message": event.get("error", {}).get("message", "Unknown error")
                        }))
                        
            except websockets.exceptions.ConnectionClosed:
                print("OpenAI connection closed")
            except Exception as e:
                print(f"OpenAI relay error: {e}")
        
        # Run both relays concurrently
        await asyncio.gather(
            relay_client_to_openai(),
            relay_openai_to_client()
        )
        
    except Exception as e:
        print(f"WebSocket error: {e}")
        
    finally:
        if openai_ws:
            await openai_ws.close()
        print("Connection closed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
