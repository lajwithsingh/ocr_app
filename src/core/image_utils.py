import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

try:
    import cv2
    _HAS_CV2 = True
except Exception:
    _HAS_CV2 = False

def pil_to_bgr_np(img_pil: Image.Image) -> np.ndarray:
    """Convert PIL RGB to numpy BGR (uint8)."""
    arr = np.array(img_pil.convert("RGB"))
    return arr[:, :, ::-1]

def preprocess_image(img: Image.Image,
                    upscale: float = 2.0,
                    sharpen: float = 1.0,
                    contrast: float = 1.3,
                    denoise: bool = True,
                    use_adaptive_thresh: bool = True) -> Image.Image:
    """
    Preprocess PIL image for better OCR.
    """
    # 1) Upscale (bicubic)
    if upscale and upscale != 1.0:
        w, h = img.size
        img = img.resize((int(w * upscale), int(h * upscale)), resample=Image.BICUBIC)

    # 2) Convert to L (grayscale)
    gray = img.convert("L")

    # 3) Enhance contrast
    if contrast != 1.0:
        enh = ImageEnhance.Contrast(gray)
        gray = enh.enhance(contrast)

    # 4) Sharpen
    if sharpen and sharpen != 1.0:
        percent = int(max(0, (sharpen - 1.0) * 150))
        if percent <= 0:
            gray = gray.filter(ImageFilter.SHARPEN)
        else:
            gray = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=percent, threshold=2))

    # 5) Denoise & Threshold
    if _HAS_CV2 and use_adaptive_thresh:
        try:
            arr = np.array(gray)
            if denoise:
                arr = cv2.medianBlur(arr, 3)
            # adaptive threshold
            th = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 31, 10)
            result = Image.fromarray(th)
            return result.convert("RGB")
        except Exception:
            pass

    # Fallback threshold
    arr = np.array(gray).astype(np.uint8)
    if denoise and _HAS_CV2:
        try:
            arr = cv2.medianBlur(arr, 3)
        except Exception:
            pass
            
    # Simple Otsu-like fallback not strictly needed if we just return high contrast gray, 
    # but keeping original logic if needed or just returning gray which works well for OCR usually.
    return gray.convert("RGB")
