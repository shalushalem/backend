import sys
import os

# 🚀 FIX: Force Python to add the current directory to its path so it can find 'services'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# 🚀 INITIALIZE SENTRY FOR CELERY
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN", "https://048fb4207a04a4a4208a1a97af611e1e@o4511020944392192.ingest.de.sentry.io/4511020965888080"), # <--- Replace with your Sentry DSN!
    traces_sample_rate=1.0,
    integrations=[
        CeleryIntegration(), # Catches failing background tasks
        RedisIntegration(),
    ],
)

# Connect Celery to your local Redis server
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery_app = Celery('ahvi_tasks', broker=redis_url, backend=redis_url)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task(name="generate_audio")
def run_heavy_audio_task(text_to_clone, lang):
    """This runs entirely separate from your FastAPI server."""
    # We import inside the function so it only loads when the worker starts
    from services import audio_service 
    try:
        audio_base64 = audio_service.generate_cloned_audio(text_to_clone, lang)
        return {"status": "success", "audio_base64": audio_base64}
    except Exception as e:
        # If it fails, Sentry will automatically record the crash,
        # but we also return an error status so your frontend knows it failed.
        return {"status": "error", "message": str(e)}