# backend/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# ✅ SAFE CELERY IMPORT
try:
    from worker import celery_app
except Exception:
    celery_app = None

# ✅ SAFE ROUTER IMPORTS (NO MORE CRASHES)
from routers.chat import router as chat_router
from routers.stylist import router as stylist_router
from routers.bg_remover import router as bg_router
from routers.reddit import router as reddit_router
from routers.style_engine import router as style_engine_router
from routers.packing_engine import router as packing_router
from routers.vision import router as vision_router

# 🚀 SENTRY (safe init)
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

# 🌐 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧠 ROUTERS
app.include_router(chat_router, tags=["Chat & NLU"])
app.include_router(stylist_router, prefix="/api/stylist", tags=["Styling"])
app.include_router(style_engine_router, prefix="/api/style-engine", tags=["Style Rules"])
app.include_router(packing_router, prefix="/api/packing", tags=["Lifestyle"])

# 👁️ VISION
app.include_router(vision_router, prefix="/api/vision", tags=["Vision AI"])
app.include_router(bg_router, prefix="/api/background", tags=["Vision AI"])

# 🌐 EXTERNAL
app.include_router(reddit_router, prefix="/api/reddit", tags=["Social"])

# 🩺 HEALTH CHECK
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "online", "message": "AHVI Master Brain is running."}

# 🚀 TASK STATUS
@app.get("/api/tasks/{job_id}", tags=["System"])
def get_task_status(job_id: str):
    if not celery_app:
        return {"status": "celery not configured"}

    task_result = AsyncResult(job_id, app=celery_app)

    if task_result.state == 'PENDING':
        return {"status": "processing"}
    elif task_result.state == 'SUCCESS':
        return {"status": "completed", "result": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"status": "failed", "error": str(task_result.info)}
    else:
        return {"status": task_result.state}

# 🛑 GLOBAL ERROR HANDLER
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )

# 🚀 ENTRY POINT
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)