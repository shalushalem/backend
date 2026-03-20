# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from worker import celery_app

# IMPORT ROUTERS
from routers import (
    chat, 
    audio, 
    stylist, 
    bg_remover, 
    reddit, 
    style_engine, 
    packing_engine, 
    vision
)

# 🚀 INITIALIZE SENTRY FOR FASTAPI
sentry_sdk.init(
    dsn="https://048fb4207a04a4a4208a1a97af611e1e@o4511020944392192.ingest.de.sentry.io/4511020965888080", 
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    integrations=[
        FastApiIntegration(),
        RedisIntegration(), 
    ],
)

app = FastAPI(
    title="AHVI AI Master Brain API",
    description="The core backend powering the AHVI Flutter Application.",
    version="2.0.0"
)

# Setup CORS (Allows your Flutter app to communicate securely)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧠 ROUTERS: The AI & Brain Endpoints
app.include_router(chat.router, prefix="/api/chat", tags=["Chat & NLU"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio Processing"])
app.include_router(stylist.router, prefix="/api/stylist", tags=["Styling"])            
app.include_router(style_engine.router, prefix="/api/style-engine", tags=["Style Rules"])         
app.include_router(packing_engine.router, prefix="/api/packing", tags=["Lifestyle"])        

# 👁️ ROUTERS: Vision & Image Processing
app.include_router(vision.router, prefix="/api/vision", tags=["Vision AI"]) 
app.include_router(bg_remover.router, prefix="/api/background", tags=["Vision AI"])

# 🌐 ROUTERS: External Services
app.include_router(reddit.router, prefix="/api/reddit", tags=["Social"])


# 🩺 ENDPOINT: Server Health Check (Good for production)
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "online", "message": "AHVI Master Brain is running."}


# 🚀 ENDPOINT: Check the status of a Celery background task
@app.get("/api/tasks/{job_id}", tags=["System"])
def get_task_status(job_id: str):
    task_result = AsyncResult(job_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        return {"status": "processing"}
    elif task_result.state == 'SUCCESS':
        return {"status": "completed", "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"status": "failed", "error": str(task_result.info)}
    else:
        return {"status": task_result.state}

if __name__ == "__main__":
    import uvicorn
    # Ready for production!
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)