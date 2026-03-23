import os
import io
import base64
import torch
import threading
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

print("🔥 CLEAN BG_REMOVER LOADED")

router = APIRouter()

# =========================
# REQUEST MODEL
# =========================
class BGRemoveRequest(BaseModel):
    image_base64: str

    @validator("image_base64")
    def validate_base64(cls, v):
        if not v or len(v) < 100:
            raise ValueError("Invalid image data")
        return v


# =========================
# GLOBALS
# =========================
model = None
model_lock = threading.Lock()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"⚙️ Using device: {device}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "RMBG_2_0")

transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])


# =========================
# LOAD MODEL (THREAD SAFE)
# =========================
def load_model():
    global model

    if model is not None:
        return model

    with model_lock:
        if model is not None:
            return model

        try:
            print("📁 Loading model from:", MODEL_PATH)

            if not os.path.exists(MODEL_PATH):
                raise Exception(f"Model folder not found: {MODEL_PATH}")

            model_local = AutoModelForImageSegmentation.from_pretrained(
                MODEL_PATH,
                trust_remote_code=True,
                local_files_only=True
            )

            model_local.to(device).eval()
            model = model_local

            print("✅ Model Ready!")

        except Exception as e:
            print("❌ Model load failed:", e)
            model = None

    return model


# =========================
# ASYNC SAFE ENDPOINT
# =========================
@router.post("/remove-bg")
async def remove_background(request: BGRemoveRequest):

    model_instance = load_model()

    if model_instance is None:
        raise HTTPException(status_code=500, detail="Model unavailable")

    try:
        # ✅ SAFE BASE64 PARSE
        try:
            base64_data = request.image_base64.split(",")[-1]
            image_data = base64.b64decode(base64_data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image")

        # ✅ LIMIT IMAGE SIZE (~5MB)
        if len(image_data) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image too large")

        # Load image
        orig_image = Image.open(io.BytesIO(image_data)).convert("RGB")
        w, h = orig_image.size

        input_tensor = transform_image(orig_image).unsqueeze(0).to(device)

        # 🚀 INFERENCE
        with torch.no_grad():
            preds = model_instance(input_tensor)[-1].sigmoid().cpu()

        mask = preds[0].squeeze().numpy()
        mask = (mask > 0.5).astype("uint8") * 255

        mask_pil = Image.fromarray(mask).resize((w, h), Image.LANCZOS)

        final_image = orig_image.copy()
        final_image.putalpha(mask_pil)

        buffer = io.BytesIO()
        final_image.save(buffer, format="PNG")

        result_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return {
            "success": True,
            "image_base64": result_base64
        }

    except HTTPException:
        raise
    except Exception as e:
        print("❌ BG Error:", e)
        raise HTTPException(status_code=500, detail="Processing failed")