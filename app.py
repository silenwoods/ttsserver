from flask import Flask, request, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import pyttsx3
from gtts import gTTS
import tempfile
import os
import subprocess
import re

def create_app():
    app = Flask(__name__)
    
    # Rate limiting setup
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["100 per hour"]
    )
    
    # Configuration
    MAX_TEXT_LENGTH = 1000  # Maximum characters per request
    MAX_FILE_SIZE_MB = 10   # Maximum audio file size in MB
    
    def validate_text(text):
        if not text:
            return 'Missing text parameter', 400
        if len(text) > MAX_TEXT_LENGTH:
            return f'Text too long. Maximum {MAX_TEXT_LENGTH} characters allowed.', 400
        if not re.match(r'^[\w\s\.,!?;:\-"\'\(\)\[\]\{\}]+$', text):
            return 'Invalid characters in text. Only alphanumerics and common punctuation allowed.', 400
        return None

    @app.route('/2')
    @limiter.limit("360 per hour")
    def pyttsx3_route():
        text = request.args.get('text')
        validation_error = validate_text(text)
        if validation_error:
            return validation_error

        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                engine = pyttsx3.init()
                engine.save_to_file(text, tmp.name)
                engine.runAndWait()
                
                # Check file size
                file_size_mb = os.path.getsize(tmp.name) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.unlink(tmp.name)
                    return f'Generated audio too large. Maximum {MAX_FILE_SIZE_MB}MB allowed.', 400
                
                return send_file(tmp.name, mimetype='audio/wav', as_attachment=False, download_name='audio.wav')
        except Exception as e:
            return f'Error generating audio: {str(e)}', 500

    @app.route('/1')
    @limiter.limit("360 per hour")
    def gtts_route():
        text = request.args.get('text')
        validation_error = validate_text(text)
        if validation_error:
            return validation_error

        try:
            tts = gTTS(text=text, lang='en')
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

    @app.route('/3')
    @limiter.limit("360 per hour")
    def espeak_route():
        text = request.args.get('text')
        validation_error = validate_text(text)
        if validation_error:
            return validation_error

        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                cmd = ['espeak', '-w', tmp.name, text]
                subprocess.run(cmd, check=True, timeout=30)
                
                # Check file size
                file_size_mb = os.path.getsize(tmp.name) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    os.unlink(tmp.name)
                    return f'Generated audio too large. Maximum {MAX_FILE_SIZE_MB}MB allowed.', 400
                
                return send_file(tmp.name, mimetype='audio/wav', as_attachment=False, download_name='audio.wav')
        except subprocess.TimeoutExpired:
            return 'Audio generation timed out. Please try with shorter text.', 408
        except subprocess.CalledProcessError as e:
            return f'Error generating audio: {str(e)}', 500
        except Exception as e:
            return f'Error generating audio: {str(e)}', 500

    return app

if __name__ == '__main__':
    import ssl
    app = create_app()
    
    # HTTPS configuration
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=context)