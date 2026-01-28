import os
# Disable OneDNN to avoid compatibility issues
os.environ['PADDLE_USE_MKLDNN'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

import logging
import traceback
from paddleocr import PaddleOCR
from .image_utils import pil_to_bgr_np, preprocess_image

class OCREngine:
    _instance = None
    _ocr = None

    def __new__(cls, lang='en', use_angle_cls=False):
        if cls._instance is None:
            cls._instance = super(OCREngine, cls).__new__(cls)
            cls._instance._initialize(lang, use_angle_cls)
        return cls._instance

    def _initialize(self, lang, use_angle_cls):
        try:
            logging.info("Initializing PaddleOCR...")
            # Initialize PaddleOCR (downloads models if needed)
            self._ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
            logging.info("PaddleOCR initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize PaddleOCR: {e}")
            raise RuntimeError(f"OCR Initialization Failed: {e}")

    def extract_text(self, pil_image, config=None) -> list:
        """
        Runs OCR on a PIL image and returns a list of detected text lines.
        """
        if self._ocr is None:
            raise RuntimeError("OCR Engine not initialized.")

        # Default config
        cfg = config or {}
        
        try:
            # Preprocess
            preprocessed = preprocess_image(
                pil_image,
                upscale=cfg.get('upscale', 1.5),
                sharpen=cfg.get('sharpen', 1.5),
                contrast=cfg.get('contrast', 1.2),
                denoise=cfg.get('denoise', True)
            )
            
            # Convert to BGR for Paddle
            arr = pil_to_bgr_np(preprocessed)
            
            # Predict
            # Predict
            result = self._ocr.predict(arr)
            
            texts = []
            if result:
                # Case 1: Result is a list of dicts (user script format)
                # Script logic: for block in raw: for element in block: texts.extend(block['rec_texts'])
                # We will be smarter: just get rec_texts if available
                # But to match script exactly in case structure is complex list-of-lists-of-dicts?
                
                # Check if result is directly a list of dicts
                if isinstance(result, list):
                    for block in result:
                        if isinstance(block, dict) and 'rec_texts' in block:
                             texts.extend(block['rec_texts'])
                        elif isinstance(block, list):
                            # Standard PaddleOCR output: [[[[coords], [text, conf]], ...]]
                             for line in block:
                                 if isinstance(line, list) and len(line) >= 2 and len(line[1]) >= 1:
                                     # line[1][0] is text
                                     texts.append(line[1][0])
                                 elif isinstance(line, dict) and 'rec_texts' in line:
                                      # Nested dict?
                                      texts.extend(line['rec_texts'])
                
            return texts

        except Exception as e:
            # Fallback (raw image)
            logging.warning(f"OCR preprocessing failed, trying raw image: {e}")
            try:
                arr = pil_to_bgr_np(pil_image)
                result = self._ocr.predict(arr)
                texts = []
                if result:
                    for block in result:
                        if block:
                            for line in block:
                                if len(line) >= 2 and len(line[1]) >= 1:
                                     texts.append(line[1][0])
                return texts
            except Exception as e2:
                logging.error(f"OCR Fatal Error: {e2}")
                return []

# Global instance accessor
def get_engine():
    return OCREngine()
