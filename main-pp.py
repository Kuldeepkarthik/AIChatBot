from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import base64
import json
import os
from openai import OpenAI
import uvicorn
from dotenv import load_dotenv
import io
import tempfile
import speech_recognition as sr
from pydub import AudioSegment

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
You are a helpful PayPay assistant named ALICE. Respond conversationally and briefly.
You can access the API to get details like rewards, offers, limits, transactions, etc. for the paypal issued debit card.

Example 1:
User: What is my reward points?
ALICE: You have 1000 reward points.

Example 2:
User: What is my spending limit for debit card?
ALICE: Your spending purchase limit for PayPal issued debit card is $1000, please let me know if you want to increase the limit for today. Also, you can ask for cash withdrawal limit.

Example 3:
User: What is my transaction history for debit card?
ALICE: Your transaction history for PayPal issued debit card is as follows: You paid 100$ to John Doe and you paid 200$ to Jane Doe today. Let me know if you want to know more about the transaction for specific date.
Note: add some random transaction when asked for by the user.

Example 4:
User: What is my cash withdrawal limit for debit card?
ALICE: Your cash withdrawal limit for PayPal issued debit card is $1000, please let me know if you want to increase the limit for today.

"""

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send welcome message using TTS after a small delay
        import asyncio
        await asyncio.sleep(0.5)  # Give client time to set up message handlers
        await self.send_welcome_message(websocket)
    
    async def send_welcome_message(self, websocket: WebSocket):
        try:
            welcome_text = "Hi! I am Alice, A paypal assistant. how can I help you"
            print(f"Generating TTS for: {welcome_text}")
            
            # Generate speech using OpenAI TTS
            # response = client.audio.speech.create(
            #     model="tts-1",
            #     voice="nova",
            #     input=welcome_text,
            #     response_format="wav"
            # )
            
            # Convert WAV audio to base64
            # audio_data = response.content
            # audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            # save audio_base64 in welcomeblob file and everytime read that file and attach the data
            # exec("open('welcome_blob.txt', 'w').write(audio_base64); print(open('welcome_blob.txt', 'r').read())")
            audio_d = open('welcome_blob.txt', 'r').read()
            print("audio_d", audio_d)
            # Send back the base64 encoded audio
            welcome_message = {
                "type": "audio_response",
                "data": audio_d,
                "format": "wav"
            }
            
            await self.send_personal_message(
                json.dumps(welcome_message), 
                websocket
            )
            print("Welcome message sent successfully")
            
        except Exception as e:
            print(f"Error sending welcome message: {e}")
            # Only log the error, don't try to send error messages on connection failure

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio_blob":
                # Get the base64 encoded audio data
                audio_base64 = message.get("data")
                
                # Decode the base64 audio data
                audio_data = base64.b64decode(audio_base64)
                
                # Transcribe audio using SpeechRecognition
                try:
                    # Create a temporary file for the audio
                    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                        temp_file.write(audio_data)
                        temp_file_path = temp_file.name
                    
                    # Convert webm to wav for speech recognition
                    audio = AudioSegment.from_file(temp_file_path)
                    wav_path = temp_file_path.replace('.webm', '.wav')
                    audio.export(wav_path, format="wav")
                    
                    # Initialize speech recognizer
                    recognizer = sr.Recognizer()
                    
                    # Transcribe the audio
                    with sr.AudioFile(wav_path) as source:
                        audio_data_sr = recognizer.record(source)
                        transcribed_text = recognizer.recognize_google(audio_data_sr)
                    
                    # Clean up the temporary files
                    os.unlink(temp_file_path)
                    os.unlink(wav_path)
                    
                    print(f"Transcribed text: {transcribed_text}")
                    
                    # Generate a response using OpenAI Chat Completion
                    chat_response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": transcribed_text}
                        ],
                        max_tokens=150
                    )
                    
                    text_to_speak = chat_response.choices[0].message.content
                    print(f"AI response: {text_to_speak}")
                    
                except Exception as transcription_error:
                    print(f"Transcription error: {transcription_error}")
                    text_to_speak = "I'm sorry, I couldn't understand what you said. Could you please try again?"
                
                # Generate speech using OpenAI TTS
                try:
                    response = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=text_to_speak,
                        response_format="wav"
                    )
                    
                    # Convert WAV audio to base64
                    audio_data = response.content
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    # Send back the base64 encoded audio
                    response_message = {
                        "type": "audio_response",
                        "data": audio_base64,
                        "format": "wav"
                    }
                    
                    await manager.send_personal_message(
                        json.dumps(response_message), 
                        websocket
                    )
                    
                except Exception as e:
                    error_message = {
                        "type": "error",
                        "message": f"TTS generation failed: {str(e)}"
                    }
                    await manager.send_personal_message(
                        json.dumps(error_message), 
                        websocket
                    )
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"message": "FastAPI WebSocket Audio Server"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)