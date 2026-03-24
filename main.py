# backend/main.py

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from celery.result import AsyncResult
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# =========================
# SAFE CELERY IMPORT
# =========================
try:
    from worker import celery_app
except Exception:
    celery_app = None

# =========================
# ROUTERS (ONLY CLEAN ONES)
# =========================
from routers.chat import router as chat_router
from routers.stylist import router as stylist_router
from routers.reddit import router as reddit_router

# ❌ REMOVE THESE (WRONG LAYER)
# from brain.engines.styling.style_engine import router


# OPTIONAL ROUTERS
import importlib.util
import os


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


try:
    enable_bg_remover = os.getenv("ENABLE_BG_REMOVER", "false").lower() in ("1", "true", "yes")
    if enable_bg_remover and all(_has_module(m) for m in ["transformers", "torch", "torchvision", "PIL"]):
        from routers.bg_remover import router as bg_router
    else:
        raise ImportError("bg_remover disabled or missing deps")
except Exception as e:
    bg_router = None
    print(f"WARN: bg_remover router disabled: {e}")

try:
    enable_vision = os.getenv("ENABLE_VISION", "false").lower() in ("1", "true", "yes")
    if enable_vision and all(_has_module(m) for m in ["cv2", "sklearn", "numpy"]):
        from routers.vision import router as vision_router
    else:
        raise ImportError("vision disabled or missing deps")
except Exception as e:
    vision_router = None
    print(f"WARN: vision router disabled: {e}")

# =========================
# SENTRY INIT
# =========================
sentry_sdk.init(
    dsn="https://048fb4207a04a4a4208a1a97af611e1e@o4511020944392192.ingest.de.sentry.io/4511020965888080",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    integrations=[FastApiIntegration()],
)

# =========================
# APP INIT
# =========================
app = FastAPI(
    title="AHVI AI Master Brain API",
    version="2.0.0"
)

# =========================
# VALIDATION ERROR HANDLER
# =========================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request",
                "details": exc.errors(),
            },
        },
    )

# =========================
# GLOBAL ERROR HANDLER
# =========================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc)
            }
        },
    )

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROUTES
# =========================
app.include_router(chat_router, prefix="/api", tags=["Chat"])

app.include_router(stylist_router, prefix="/api/stylist", tags=["Styling"])
app.include_router(reddit_router, prefix="/api/reddit", tags=["Social"])

if vision_router:
    app.include_router(vision_router, prefix="/api/vision", tags=["Vision"])

if bg_router:
    app.include_router(bg_router, prefix="/api/background", tags=["Vision"])

# =========================
# HEALTH
# =========================
@app.get("/health")
def health_check():
    return {"status": "online"}

# =========================
# TASK STATUS
# =========================
@app.get("/api/tasks/{job_id}")
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
