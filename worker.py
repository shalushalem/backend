import os
from celery import Celery

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
        return {"status": "error", "message": str(e)}