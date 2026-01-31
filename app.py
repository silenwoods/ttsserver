from flask import Flask, request, send_file, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from flask_cors import CORS
from limits import parse_many
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
    app.config["RATELIMIT_HEADERS_ENABLED"] = True
    app.config["LOG_RATE_LIMITS"] = False
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["3600 per hour"]
    )
    
    # Configuration
    MAX_TEXT_LENGTH = 1000  # Maximum characters per request
    MAX_FILE_SIZE_MB = 10   # Maximum audio file size in MB
    DEDUP_WINDOW = "1 per 10 seconds"
    HOURLY_LIMIT = "3600 per hour"
    DEDUP_LIMIT_ITEM = parse_many(DEDUP_WINDOW)[0]
    HOURLY_LIMIT_ITEM = parse_many(HOURLY_LIMIT)[0]
    
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

    def format_limit(limit_obj):
        if limit_obj is None:
            return "unknown"
        for attr in ("limit", "limit_string", "limit_str"):
            value = getattr(limit_obj, attr, None)
            if value:
                return str(value)
        return str(limit_obj)

    def classify_limit(limit_obj):
        if limit_obj is None:
            return "unknown", "unknown"
        if limit_obj.limit == DEDUP_LIMIT_ITEM and limit_obj.key_func is url_dedup_key:
            return "route:dedup_window", "decorated"
        if limit_obj.limit == HOURLY_LIMIT_ITEM:
            source = "decorated" if getattr(limit_obj, "override_defaults", False) else "default"
            rule_id = "route:hourly" if source == "decorated" else "default:hourly"
            return rule_id, source
        source = "decorated" if getattr(limit_obj, "override_defaults", False) else "default"
        return f"{source}:unknown", source

    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit(e):
        limit_obj = getattr(e, "limit", None)
        limit_str = format_limit(limit_obj)
        rule_id, rule_source = classify_limit(limit_obj)
        limit_key = None
        limit_scope = None
        limit_bucket = None
        if limit_obj is not None:
            try:
                limit_key = limit_obj.key_func()
                limit_scope = limit_obj.scope_for(request.endpoint or "", request.method)
                key_prefix = getattr(limiter, "_key_prefix", None)
                args = [limit_key, limit_scope]
                if key_prefix:
                    args = [key_prefix, *args]
                limit_bucket = limit_obj.limit.key_for(*args)
            except Exception:
                pass
        remote = request.headers.get("X-Forwarded-For", request.remote_addr)
        log_payload = {
            "event": "rate_limit_exceeded",
            "rule_id": rule_id,
            "rule_source": rule_source,
            "limit": limit_str,
            "limit_key": limit_key,
            "limit_scope": limit_scope,
            "limit_bucket": limit_bucket,
            "path": request.path,
            "method": request.method,
            "remote": remote,
            "full_url": request.url,
            "dedup_key": url_dedup_key(),
        }
        if app.config.get("LOG_RATE_LIMITS", True):
            app.logger.warning("Rate limit exceeded: %s", log_payload)
        return Response(f"Rate limit exceeded: {limit_str}", status=429, mimetype="text/plain")
        
    @app.route('/1')
    @limiter.limit(DEDUP_WINDOW, key_func=url_dedup_key)
    @limiter.limit(HOURLY_LIMIT)
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
    @limiter.limit(HOURLY_LIMIT)
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
