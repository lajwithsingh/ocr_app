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
            # Do NOT initialize here to avoid MainThread affinity
            # cls._instance._initialize(lang, use_angle_cls)
            cls._instance.config = (lang, use_angle_cls)
        return cls._instance

    def initialize(self):
        """Explicit initialization, safe to call from worker thread"""
        if self._ocr is not None:
             return
             
        lang, use_angle_cls = self.config
        try:
            # Prevent OpenCV threading conflicts
            try:
                import cv2
                cv2.setNumThreads(0)
            except: pass
            
            logging.info(f"Initializing PaddleOCR (Lang: {lang})...")
            
            # Check for bundled models (offline support)
            # Priorities: 1. sys._MEIPASS/models (Frozen), 2. ./models (Local Dev)
            import sys
            from pathlib import Path
            
            model_args = {}
            base_model_dir = Path("models").absolute()
            if getattr(sys, 'frozen', False):
                base_model_dir = Path(sys._MEIPASS) / "models"
            
            if base_model_dir.exists():
                logging.info(f"Using bundled models at: {base_model_dir}")
                
                # Dynamic model finder (matches what bundle_models.py copied)
                def find_model_dir(keyword):
                    # Search for directory containing keyword
                    # Prefer exact matches if possible, but structure varies
                    for item in base_model_dir.rglob(f"*{keyword}*"):
                        if item.is_dir():
                            return str(item)
                    return None
                
                det_path = find_model_dir("det")
                rec_path = find_model_dir("rec")
                cls_path = find_model_dir("cls")
                
                if det_path: model_args['det_model_dir'] = det_path
                if rec_path: model_args['rec_model_dir'] = rec_path
                if cls_path: model_args['cls_model_dir'] = cls_path
                
                logging.info(f"Found models: Det={det_path}, Rec={rec_path}, Cls={cls_path}")

            # Initialize PaddleOCR with detected args
            self._ocr = PaddleOCR(use_textline_orientation=use_angle_cls, lang=lang, **model_args)
            
            # Silence internal logger
            logging.getLogger("ppocr").setLevel(logging.ERROR)
            
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
