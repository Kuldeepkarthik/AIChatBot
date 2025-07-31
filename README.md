# Audio-Video AI Project

Real-time audio recording and AI-powered text-to-speech response system using FastAPI WebSocket backend and vanilla JavaScript frontend.

## Features

- Real-time audio recording with energy detection
- WebSocket communication between frontend and backend
- OpenAI TTS integration for generating speech responses
- Base64 encoded PCM audio playback
- Auto-start/stop recording based on voice activity

## Setup
1. Unwrap all 3 .rar files before procedding with other steps.
### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your OpenAI API key:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

4. Run the FastAPI server:
   ```bash
   python main.py
   ```

   The server will start on `http://localhost:8000`

### Frontend Setup

1. Open `frontend/index.html` in a web browser
2. Click "Start Listening" to begin recording
3. Speak into the microphone - recording will auto-start when voice is detected
4. The backend will process the audio and return a TTS response

## API Endpoints

- `GET /` - Health check endpoint
- `WebSocket /ws` - WebSocket endpoint for real-time audio communication

## WebSocket Message Format

### Frontend to Backend:
```json
{
  "type": "audio_blob",
  "data": "base64_encoded_audio_data"
}
```

### Backend to Frontend:
```json
{
  "type": "audio_response",
  "data": "base64_encoded_pcm_audio",
  "format": "pcm"
}
```

## Requirements

- Python 3.7+
- OpenAI API key
- Modern web browser with WebRTC support
- Microphone access
