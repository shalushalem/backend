import os
import shutil
from fastapi import APIRouter, UploadFile, File
from services import audio_service

router = APIRouter()

@router.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_file = f"temp_{file.filename}"
    try:
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        text = audio_service.transcribe_audio_file(temp_file)
        os.remove(temp_file)
        return {"text": text}
    except Exception as e:
        if os.path.exists(temp_file): os.remove(temp_file)
        return {"text": "", "error": str(e)}