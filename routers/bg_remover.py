import os
import io
import base64
import torch
import numpy as np
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from huggingface_hub import snapshot_download, login
from transformers import AutoModelForImageSegmentation
from torchvision import transforms
import cv2  # for optional smoothing

router = APIRouter()

# =========================
# Request Model
# =========================
class BGRemoveRequest(BaseModel):
    image_base64: str

# =========================
# MODEL SETUP
# =========================
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if hf_token:
    login(token=hf_token)

print("Downloading RMBG-2.0...")
model_path = snapshot_download(
    repo_id="briaai/RMBG-2.0",
    local_dir="RMBG_2_0"
)

print("Loading model...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = AutoModelForImageSegmentation.from_pretrained(
    "RMBG_2_0",
    trust_remote_code=True
)
model.to(device).eval()

transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

print("✅ Model Ready!")

# =========================
# API ENDPOINT
# =========================
@router.post("/api/remove-bg")
def remove_background(request: BGRemoveRequest):
    try:
        # =========================
        # 1. Decode Base64 Image
        # =========================
        base64_data = request.image_base64
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        image_data = base64.b64decode(base64_data)
        orig_image = Image.open(io.BytesIO(image_data)).convert("RGB")
        w, h = orig_image.size

        # =========================
        # 2. Model Inference
        # =========================
        input_tensor = transform_image(orig_image).unsqueeze(0).to(device)

        with torch.no_grad():
            preds = model(input_tensor)[-1].sigmoid().cpu()

        # =========================
        # 3. CLEAN MASK (IMPORTANT FIX)
        # =========================
        mask = preds[0].squeeze().numpy()

        # OPTION A: Hard threshold (sharp edges)
        threshold = 0.5
        mask = (mask > threshold).astype("uint8") * 255

        # OPTION B (better): smooth edges slightly
        # Uncomment this block if you want softer edges
        """
        mask = (mask * 255).astype("uint8")
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        """

        # =========================
        # 4. Resize mask to original size
        # =========================
        mask_pil = Image.fromarray(mask).resize((w, h), Image.LANCZOS)

        # =========================
        # 5. Apply alpha channel
        # =========================
        final_image = orig_image.copy()
        final_image.putalpha(mask_pil)

        # =========================
        # 6. DEBUG (IMPORTANT)
        # =========================
        print("Image mode:", final_image.mode)

        alpha = final_image.split()[-1]
        alpha_min, alpha_max = min(alpha.getdata()), max(alpha.getdata())
        print("Alpha range:", alpha_min, alpha_max)

        # =========================
        # 7. Convert to Base64 PNG
        # =========================
        buffered = io.BytesIO()
        final_image.save(buffered, format="PNG")

        result_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {
            "success": True,
            "image_base64": result_base64,
            "message": "Background removed successfully (clean alpha)"
        }

    except Exception as e:
        print(f"BG Removal Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))