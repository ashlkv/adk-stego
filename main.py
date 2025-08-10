# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import base64
import warnings
import tempfile
import wave

from pathlib import Path
from dotenv import load_dotenv
from watermark import add_watermark, encode_message, get_watermark

from google.genai.types import (
    Part,
    Content,
    Blob,
)

from google.adk.runners import InMemoryRunner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from google_search_agent.agent import root_agent

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

#
# ADK Streaming
#

# Load Gemini API Key
load_dotenv()

APP_NAME = "ADK Streaming example"


def apply_audio_watermark(pcm_data):
    """Apply watermark to PCM audio data with default "disobey" message."""
    watermark_message = "6469736f626579000000000000000000"  # "disobey" in hex
    return apply_audio_watermark_with_message(pcm_data, watermark_message)

def apply_audio_watermark_with_message(pcm_data, watermark_message):
    """Apply watermark to PCM audio data by converting to WAV, watermarking, and converting back."""
    try:
        # Create temporary files in current directory so Docker can access them
        temp_input_path = f"temp_input_{os.getpid()}.wav"
        temp_output_path = f"temp_output_{os.getpid()}.wav"
        
        # Convert PCM to WAV
        with wave.open(temp_input_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(24000)  # 24kHz sample rate (common for speech)
            wav_file.writeframes(pcm_data)
        
        if add_watermark(temp_input_path, temp_output_path, watermark_message):
            # Read watermarked WAV and extract PCM data
            with wave.open(temp_output_path, 'rb') as wav_file:
                watermarked_pcm = wav_file.readframes(wav_file.getnframes())
            
            # Clean up temp files
            os.unlink(temp_input_path)
            os.unlink(temp_output_path)
            
            return watermarked_pcm
        else:
            # Clean up temp files on failure
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
            if os.path.exists(temp_output_path):
                os.unlink(temp_output_path)
            return None
                
    except Exception as e:
        print(f"Error applying watermark: {e}")
        return None


async def start_agent_session(user_id, is_audio=False):
    """Starts an agent session"""

    # Create a Runner
    runner = InMemoryRunner(
        app_name=APP_NAME,
        agent=root_agent,
    )

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,  # Replace with actual user ID
    )

    # Set response modality
    modality = "AUDIO" if is_audio else "TEXT"
    run_config = RunConfig(response_modalities=[modality])

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Start agent session
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue


async def agent_to_client_sse(live_events):
    """Agent to client communication via SSE"""
    session_id = id(live_events)  # Use live_events object id as session identifier
    audio_buffers[session_id] = []
    
    async for event in live_events:
        # If the turn is complete or interrupted, process buffered audio and send completion
        if event.turn_complete or event.interrupted:
            # Process any buffered audio chunks
            if audio_buffers[session_id]:
                # Combine all audio chunks
                combined_audio = b''.join(audio_buffers[session_id])
                
                # Apply watermark to combined audio
                watermarked_data = apply_audio_watermark(combined_audio)
                
                # Verify watermark
                temp_verify_path = f"temp_verify_{os.getpid()}.wav"
                with wave.open(temp_verify_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(24000)
                    wav_file.writeframes(watermarked_data)
                detected = get_watermark(temp_verify_path)
                print(f"watermark read: {detected}")
                os.unlink(temp_verify_path)
                
                # Split watermarked audio into chunks and send
                chunk_size = 11520  # Approximate chunk size from original stream
                for i in range(0, len(watermarked_data), chunk_size):
                    chunk = watermarked_data[i:i+chunk_size]
                    message = {
                        "mime_type": "audio/pcm",
                        "data": base64.b64encode(chunk).decode("ascii")
                    }
                    yield f"data: {json.dumps(message)}\n\n"
                    print(f"[AGENT TO CLIENT]: audio/pcm: {len(chunk)} bytes (watermarked chunk)")
                
                # Clear buffer
                audio_buffers[session_id] = []
            
            message = {
                "turn_complete": event.turn_complete,
                "interrupted": event.interrupted,
            }
            yield f"data: {json.dumps(message)}\n\n"
            print(f"[AGENT TO CLIENT]: {message}")
            continue

        # Read the Content and its first Part
        part: Part = (
            event.content and event.content.parts and event.content.parts[0]
        )
        if not part:
            continue

        # If it's audio, buffer it for watermarking at turn completion
        is_audio = part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")
        if is_audio:
            audio_data = part.inline_data and part.inline_data.data
            if audio_data:
                # Buffer audio chunk
                audio_buffers[session_id].append(audio_data)
                print(f"[BUFFERING]: audio/pcm: {len(audio_data)} bytes")
                continue

        # If it's text and a parial text, send it
        if part.text and event.partial:
            message = {
                "mime_type": "text/plain",
                "data": part.text
            }
            yield f"data: {json.dumps(message)}\n\n"
            print(f"[AGENT TO CLIENT]: text/plain: {message}")


#
# FastAPI web app
#

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Store active sessions and audio buffers
active_sessions = {}
audio_buffers = {}
user_audio_buffers = {}
user_silence_counters = {}
import asyncio
import struct


@app.get("/")
async def root():
    """Serves the index.html"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/events/{user_id}")
async def sse_endpoint(user_id: int, is_audio: str = "false"):
    """SSE endpoint for agent to client communication"""

    # Start agent session
    user_id_str = str(user_id)
    live_events, live_request_queue = await start_agent_session(user_id_str, is_audio == "true")

    # Store the request queue for this user
    active_sessions[user_id_str] = live_request_queue

    print(f"Client #{user_id} connected via SSE, audio mode: {is_audio}")

    def cleanup():
        live_request_queue.close()
        if user_id_str in active_sessions:
            del active_sessions[user_id_str]
        print(f"Client #{user_id} disconnected from SSE")

    async def event_generator():
        try:
            async for data in agent_to_client_sse(live_events):
                yield data
        except Exception as e:
            print(f"Error in SSE stream: {e}")
        finally:
            cleanup()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@app.post("/send/{user_id}")
async def send_message_endpoint(user_id: int, request: Request):
    """HTTP endpoint for client to agent communication"""

    user_id_str = str(user_id)

    # Get the live request queue for this user
    live_request_queue = active_sessions.get(user_id_str)
    if not live_request_queue:
        return {"error": "Session not found"}

    # Parse the message
    message = await request.json()
    mime_type = message["mime_type"]
    data = message["data"]

    # Send the message to the agent
    if mime_type == "text/plain":
        content = Content(role="user", parts=[Part.from_text(text=data)])
        live_request_queue.send_content(content=content)
        print(f"[CLIENT TO AGENT]: {data}")
    elif mime_type == "audio/pcm":
        decoded_data = base64.b64decode(data)
        
        # Initialize user audio buffer if not exists
        if user_id_str not in user_audio_buffers:
            user_audio_buffers[user_id_str] = []
            user_silence_counters[user_id_str] = 0
        
        # Calculate RMS volume for silence detection
        samples = struct.unpack(f'<{len(decoded_data)//2}h', decoded_data)
        rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
        volume_threshold = 800  # Higher than 800 and some of the speech might be cut off.
        
        # Buffer user audio chunk
        user_audio_buffers[user_id_str].append(decoded_data)
        
        if rms < volume_threshold:
            user_silence_counters[user_id_str] += 1
            print(f"[SILENCE]: chunk {user_silence_counters[user_id_str]} (RMS: {rms:.1f})")
        else:
            user_silence_counters[user_id_str] = 0
            print(f"[SPEECH]: audio/pcm: {len(decoded_data)} bytes (RMS: {rms:.1f})")
        
        # Process when we detect end of speech (3 consecutive silent chunks)
        if user_silence_counters[user_id_str] >= 3 and len(user_audio_buffers[user_id_str]) > 3:
            # Remove the silent chunks from the end
            audio_chunks = user_audio_buffers[user_id_str][:-3]
            
            if audio_chunks:
                # Combine all speech audio chunks
                combined_user_audio = b''.join(audio_chunks)
                
                # Only save and send if we have substantial audio (minimum 30KB)
                if len(combined_user_audio) >= 30000:
                    # Save combined audio to WAV file with timestamp
                    import time
                    timestamp = int(time.time() * 1000)  # millisecond timestamp
                    user_wav_path = f"user_speech_{timestamp}.wav"
                    with wave.open(user_wav_path, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(16000)  # Match client sample rate
                        wav_file.writeframes(combined_user_audio)
                    print(f"Saved user speech: {user_wav_path}")
                    
                    # Try to read watermark from the saved WAV file
                    try:
                        detected_watermark = get_watermark(user_wav_path)
                        if detected_watermark:
                            from watermark import decode_message
                            decoded_message = decode_message(detected_watermark)
                            print(f"Found watermark: {detected_watermark} - '{decoded_message}'")
                        else:
                            print("No watermark found in user speech")
                    except Exception as e:
                        print(f"Watermark detection failed: {e}")
                    
                    # Send combined audio to LLM
                    live_request_queue.send_realtime(Blob(data=combined_user_audio, mime_type=mime_type))
                    print(f"[CLIENT TO AGENT]: audio/pcm: {len(combined_user_audio)} bytes (combined)")
                    
                    # Send a silence chunk to signal end of speech to the model
                    silence_chunk = b'\x00' * 6400  # 6400 bytes of silence (16-bit)
                    live_request_queue.send_realtime(Blob(data=silence_chunk, mime_type=mime_type))
                    print(f"[CLIENT TO AGENT]: silence chunk sent to signal end of speech")
                else:
                    print(f"[SKIPPING]: Audio too small ({len(combined_user_audio)} bytes), not saving")
            
            # Clear user audio buffer and reset counter
            user_audio_buffers[user_id_str] = []
            user_silence_counters[user_id_str] = 0
    else:
        return {"error": f"Mime type not supported: {mime_type}"}

    return {"status": "sent"}
