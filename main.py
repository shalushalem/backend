from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from worker import celery_app

# Import routers
from routers import chat, audio, vision, stylist, bg_remover, reddit, style_engine

# 🚀 INITIALIZE SENTRY FOR FASTAPI
sentry_sdk.init(
    dsn="https://048fb4207a04a4a4208a1a97af611e1e@o4511020944392192.ingest.de.sentry.io/4511020965888080", # <--- Replace with your Sentry DSN!
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    integrations=[
        FastApiIntegration(),
        RedisIntegration(), # Tracks if Redis goes down!
    ],
)

app = FastAPI(title="Ahvi AI Fashion Assistant Backend")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(chat.router)
app.include_router(audio.router)
app.include_router(vision.router)
app.include_router(stylist.router)
app.include_router(bg_remover.router)
app.include_router(reddit.router)
app.include_router(style_engine.router)

# 🚀 ENDPOINT: Check the status of a Celery background task
@app.get("/api/tasks/{job_id}")
def get_task_status(job_id: str):
    # Ask Celery/Redis what the status of this specific job is
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)