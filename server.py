from flask import Flask, request, jsonify, send_from_directory
from agent import extract_proposal
from google import genai
from google.genai import types
import json
import os

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB upload limit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_NAME = "gemini-3.5-flash-lite"
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/mp4", "audio/m4a", "audio/aac", "audio/ogg",
    "audio/webm", "audio/flac"
}


@app.route("/")
def home():
    return send_from_directory(app.root_path, "assistant.html")


@app.route("/generator")
def generator():
    return send_from_directory(app.root_path, "challenge-generator.html")


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True)
    notes = data.get("notes", "") if data else ""

    if not isinstance(notes, str) or not notes.strip():
        return jsonify({"error": "Please provide adviser notes."}), 400

    try:
        result = extract_proposal(notes)
        return jsonify(json.loads(result))
    except Exception as error:
        app.logger.exception("Proposal extraction failed")
        return jsonify({"error": str(error)}), 500


@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio = request.files.get("audio")
    if audio is None or not audio.filename:
        return jsonify({"error": "Choose an audio recording first."}), 400

    extension = os.path.splitext(audio.filename)[1].lower()
    extension_mime_types = {
        ".mp3": "audio/mpeg", ".wav": "audio/wav",
        ".m4a": "audio/mp4", ".aac": "audio/aac",
        ".ogg": "audio/ogg", ".webm": "audio/webm",
        ".flac": "audio/flac"
    }
    mime_type = extension_mime_types.get(extension, (audio.mimetype or "").lower())
    if mime_type not in ALLOWED_AUDIO_TYPES:
        return jsonify({"error": "Unsupported audio format."}), 415

    audio_bytes = audio.read()
    if not audio_bytes:
        return jsonify({"error": "The selected audio file is empty."}), 400
    if len(audio_bytes) > 20 * 1024 * 1024:
        return jsonify({"error": "Audio file exceeds the 20 MB limit."}), 413

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY is missing from .env"}), 500

    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            "Transcribe this adviser-client voice note accurately and as close to verbatim as possible. "
            "Preserve names, numbers, currencies, dates, investment amounts, fees, time horizons, "
            "risk preferences, and uncertainty. Do not summarise, infer missing details, or create "
            "financial advice. Mark genuinely unclear words as [unclear]. Return only the transcript."
        )
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, audio_part]
        )
        transcript = (response.text or "").strip()
        if not transcript:
            return jsonify({"error": "Gemini did not return a transcript. Try another audio file."}), 502
        return jsonify({"transcript": transcript})
    except Exception as error:
        app.logger.exception("Audio transcription failed")
        return jsonify({"error": str(error)}), 500


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Audio file exceeds the 20 MB limit."}), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)

