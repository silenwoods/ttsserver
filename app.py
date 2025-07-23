from flask import Flask, request, send_file
import pyttsx3
from gtts import gTTS
import tempfile
import os
import subprocess

def create_app():
    app = Flask(__name__)
    
    @app.route('/pyttsx3')
    def pyttsx3_route():
        text = request.args.get('text')
        if not text:
            return 'Missing text parameter', 400

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            engine = pyttsx3.init()
            engine.save_to_file(text, tmp.name)
            engine.runAndWait()
            return send_file(tmp.name, as_attachment=True, download_name='audio.wav')

    @app.route('/gtts')
    def gtts_route():
        text = request.args.get('text')
        if not text:
            return 'Missing text parameter', 400

        tts = gTTS(text=text, lang='en')
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tts.save(tmp.name)
            return send_file(tmp.name, as_attachment=True, download_name='audio.mp3')

    @app.route('/espeak')
    def espeak_route():
        text = request.args.get('text')
        if not text:
            return 'Missing text parameter', 400

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            cmd = ['espeak', '-w', tmp.name, text]
            subprocess.run(cmd)
            return send_file(tmp.name, as_attachment=True, download_name='audio.wav')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', debug=True)