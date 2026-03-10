import os
import torch
import tempfile
import base64
import whisper

# Coqui XTTS Fixes
os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["SCARF_NO_ANALYTICS"] = "True"
os.environ["DO_NOT_TRACK"] = "True"

from TTS.api import TTS

USE_GPU = torch.cuda.is_available()
print(f"Hardware Check: CUDA GPU Available? {USE_GPU}")

print("Loading Whisper AI Model...")
try:
    whisper_model = whisper.load_model("base")
    print("✅ Whisper Model Loaded!")
except Exception as e:
    print(f"⚠️ Failed to load Whisper: {e}")
    whisper_model = None

print("Loading XTTS Voice Cloning Model...")
try:
    tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=USE_GPU)
    print("✅ Voice Clone Model Loaded!")
except Exception as e:
    print(f"⚠️ Failed to load XTTS: {e}")
    tts_model = None

def transcribe_audio_file(file_path: str) -> str:
    if not whisper_model: return ""
    result = whisper_model.transcribe(file_path)
    return result["text"].strip()

def generate_cloned_audio(text: str, target_lang: str) -> str:
    if not tts_model: return ""
    
    reference_audio_path = "my_voice.wav"
    if not os.path.exists(reference_audio_path):
        print(f"⚠️ Reference audio '{reference_audio_path}' not found!")
        return ""

    xtts_lang = "hi" if target_lang in ["hi", "te"] else "en"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_path = temp_audio.name

    try:
        tts_model.tts_to_file(
            text=text,
            file_path=temp_path,
            speaker_wav=reference_audio_path,
            language=xtts_lang
        )
        with open(temp_path, "rb") as audio_file:
            return base64.b64encode(audio_file.read()).decode('utf-8')
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)