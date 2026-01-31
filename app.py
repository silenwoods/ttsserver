from flask import Flask, request, send_file, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import pyttsx3
from gtts import gTTS
from dashscope.audio.tts_v2 import SpeechSynthesizer
import tempfile
import os
import subprocess
import re
from langdetect import detect, detect_langs

def create_app():
    app = Flask(__name__)
    
    # Enable CORS for all routes and origins
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Rate limiting setup
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["100 per hour"]
    )
    
    # Configuration
    MAX_TEXT_LENGTH = 1000  # Maximum characters per request
    MAX_FILE_SIZE_MB = 10   # Maximum audio file size in MB
    DEDUP_WINDOW = "1 per 10 seconds"
    
    def validate_text(text):
        if not text:
            return 'Missing text parameter', 400
        if len(text) > MAX_TEXT_LENGTH:
            return f'Text too long. Maximum {MAX_TEXT_LENGTH} characters allowed.', 400
        return None

    def detect_language(text:str, varlang:str):
        if varlang is None:
            return 'en'
        if varlang.lower() == 'auto':
            try:
                return detect(text)
            except:
                return 'en'
        return varlang

    def url_dedup_key():
        # Use the full URL (including query string) as the deduplication key.
        return request.url
        
    @app.route('/1')
    @limiter.limit(DEDUP_WINDOW, key_func=url_dedup_key)
    @limiter.limit("360 per hour")
    def gtts_route():
        text = request.args.get('text')
        varlang = request.args.get('lang')
        validation_error = validate_text(text)
        if validation_error:
            return validation_error

        try:
            tts = gTTS(text=text, lang=detect_language(text, varlang))
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tts.save(tmp.name)
                
                # Check file size
                file_size_mb = os.path.getsize(tmp.name) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.unlink(tmp.name)
                    return f'Generated audio too large. Maximum {MAX_FILE_SIZE_MB}MB allowed.', 400
                
                return send_file(tmp.name, mimetype='audio/mpeg', as_attachment=False, download_name='audio.mp3')
        except Exception as e:
            return f'Error generating audio: {str(e)}', 500

    @app.route('/2')
    @limiter.limit(DEDUP_WINDOW, key_func=url_dedup_key)
    @limiter.limit("360 per hour")
    def cosyvoice_route():
        """阿里百炼平台 CosyVoice TTS - 使用龙安欢声音"""
        text = request.args.get('text')
        validation_error = validate_text(text)
        if validation_error:
            return validation_error

        try:
            synthesizer = SpeechSynthesizer(
                model="cosyvoice-v3-plus",
                voice="longanhuan"
            )
            audio = synthesizer.call(text)

            if audio is None:
                return 'Error: Failed to generate audio from CosyVoice API', 500

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(audio)
                tmp.flush()

                file_size_mb = os.path.getsize(tmp.name) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.unlink(tmp.name)
                    return f'Generated audio too large. Maximum {MAX_FILE_SIZE_MB}MB allowed.', 400

                return send_file(tmp.name, mimetype='audio/mpeg', as_attachment=False, download_name='audio.mp3')
        except Exception as e:
            return f'Error generating audio: {str(e)}', 500

    return app

app = create_app()

if __name__ == '__main__':
    import ssl
    
    # HTTPS configuration
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=context)
