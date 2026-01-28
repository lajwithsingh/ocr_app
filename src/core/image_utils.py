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

    # Simple global Otsu-like threshold (numpy)
    try:
        # compute Otsu threshold (manual)
        hist, bin_edges = np.histogram(arr.flatten(), bins=256, range=(0, 256))
        total = arr.size
        sum_total = np.dot(np.arange(256), hist)
        sumB = 0.0
        wB = 0.0
        max_var = 0.0
        threshold = 128
        for i in range(256):
            wB += hist[i]
            if wB == 0:
                continue
            wF = total - wB
            if wF == 0:
                break
            sumB += i * hist[i]
            mB = sumB / wB
            mF = (sum_total - sumB) / wF
            var_between = wB * wF * (mB - mF) ** 2
            if var_between > max_var:
                max_var = var_between
                threshold = i
        # apply threshold with a small offset to avoid very light text being lost
        th_val = max(0, min(255, int(threshold * 0.98)))
        bin_img = (arr > th_val).astype(np.uint8) * 255
        result = Image.fromarray(bin_img)
        return result.convert("RGB")
    except Exception:
        # last fallback: return grayscale as RGB
        return gray.convert("RGB")
