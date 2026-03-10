from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from worker import celery_app

# Import routers
from routers import chat, audio, vision, stylist, bg_remover, reddit

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

# 🚀 NEW ENDPOINT: Check the status of a Celery background task
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