import io
import base64
import torch
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from huggingface_hub import snapshot_download, login
from transformers import AutoModelForImageSegmentation
from torchvision import transforms

router = APIRouter()

# Request model to receive base64 images from the frontend
class BGRemoveRequest(BaseModel):
    image_base64: str

# ==========================================
# 🧠 GLOBAL MODEL SETUP (Runs once on startup)
# ==========================================
# ⚠️ SECURITY WARNING: It is highly recommended to use an environment variable 
# (.env file) for your HuggingFace token instead of hardcoding it!
hf_token = os.getenv("HUGGINGFACE_TOKEN")
login(HF_TOKEN)

print("Downloading/Checking RMBG-2.0 model locally...")
model_path = snapshot_download(
    repo_id="briaai/RMBG-2.0",
    local_dir="RMBG_2_0"
)

print("Loading RMBG-2.0 (The Edge-Precision Model)...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = AutoModelForImageSegmentation.from_pretrained(
    "RMBG_2_0",
    trust_remote_code=True,
    low_cpu_mem_usage=False
)
model.to(device).eval()

transform_image = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])
print("✅ BG Remover Model Loaded & Ready!")

# ==========================================
# 🚀 API ENDPOINT
# ==========================================
@router.post("/api/remove-bg")
def remove_background(request: BGRemoveRequest):
    try:
        # 1. Decode the Base64 string from the frontend into a PIL Image
        # (Strip the "data:image/jpeg;base64," prefix if it exists)
        base64_data = request.image_base64
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        image_data = base64.b64decode(base64_data)
        orig_image = Image.open(io.BytesIO(image_data)).convert("RGB")
        w, h = orig_image.size

        # 2. Process via RMBG-2.0
        input_tensor = transform_image(orig_image).unsqueeze(0).to(device)

        with torch.no_grad():
            # Get the alpha matte (transparency map)
            preds = model(input_tensor)[-1].sigmoid().cpu()
            mask = preds[0].squeeze()

        # 3. Convert mask to image and resize back to original quality
        # Using Image.Resampling.LANCZOS to avoid deprecation warnings in newer Pillow versions
        mask_pil = transforms.ToPILImage()(mask).resize((w, h), getattr(Image, 'LANCZOS', Image.Resampling.LANCZOS))

        # 4. Apply mask to create the transparent PNG
        final_image = orig_image.copy()
        final_image.putalpha(mask_pil)

        # 5. Convert the transparent PIL Image back to a Base64 string
        buffered = io.BytesIO()
        final_image.save(buffered, format="PNG")
        result_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        # Return the transparent image back to the frontend
        return {
            "success": True,
            "image_base64": result_base64,
            "message": "Background removed successfully"
        }

    except Exception as e:
        print(f"BG Removal Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))