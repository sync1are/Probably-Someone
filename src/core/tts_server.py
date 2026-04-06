"""TTS Server - Runs Kokoro TTS as a separate service."""

from flask import Flask, request, jsonify
from kokoro import KPipeline
import numpy as np

app = Flask(__name__)

# Initialize TTS pipeline on server startup
print("🔊 Loading Kokoro TTS pipeline...")
pipeline = KPipeline(lang_code='a')
print("✓ TTS pipeline ready")


@app.route('/generate', methods=['POST'])
def generate_speech():
    """Generate speech from text."""
    try:
        data = request.json
        text = data.get('text', '')
        voice = data.get('voice', 'af_sky')
        speed = data.get('speed', 1.0)

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Generate audio
        audio_chunks = []
        for _, _, audio in pipeline(text, voice=voice, speed=speed):
            audio_chunks.append(audio)

        # Concatenate all audio chunks
        if audio_chunks:
            full_audio = np.concatenate(audio_chunks)
            # Convert to bytes (float32)
            audio_bytes = full_audio.tobytes()
            return audio_bytes, 200, {'Content-Type': 'application/octet-stream'}
        else:
            return jsonify({'error': 'No audio generated'}), 500

    except Exception as e:
        print(f"Error generating speech: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    print("🎙️ Starting TTS server on http://127.0.0.1:8889")
    app.run(host='127.0.0.1', port=8889, threaded=True)
