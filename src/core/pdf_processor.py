import io
import re
import logging
import threading
import time
import traceback
from pathlib import Path
from typing import Callable, Optional

import fitz  # PyMuPDF
from PIL import Image
from rapidfuzz import fuzz

from .ocr_engine import get_engine

class PDFProcessor:
    def __init__(self, input_path: str, output_folder: str, config: dict = None):
        self.input_path = Path(input_path)
        self.output_folder = Path(output_folder)
        self.config = config or {}
        # In multiprocessing, event is passed in
        self.stop_event = None 
        self.status_queue = None
        self._ocr = get_engine()

    def set_queue(self, queue):
        self.status_queue = queue

    def set_stop_event(self, event):
        self.stop_event = event

    def _emit(self, event_type, progress, message):
        if self.status_queue:
            self.status_queue.put((event_type, progress, message))
            


    def run(self):
        try:
            # Ensure OCR is initialized in this worker thread to avoid QBasicTimer/Thread affinity issues
            self._ocr.initialize()
            
            self._emit('info', 0, f"Starting processing for {self.input_path.name}")
            self._process_pdf()
            if not self.stop_event.is_set():
                self._emit('complete', 1.0, "Processing completed successfully.")
            else:
                self._emit('info', 1.0, "Processing cancelled.")
        except Exception as e:
            logging.error(f"Processing error: {e}\n{traceback.format_exc()}")
            self._emit('error', 0, str(e))

    def _process_pdf(self):
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        doc = fitz.open(str(self.input_path))
        total_pages = len(doc)
        current_index = 0
        
        carried_case = None
        carried_page = None
        
        # Track generated files for Excel summary
        # List of tuples: (filename, start_page, end_page)
        self.generated_files_data = []

        dpi = self.config.get('dpi', 200)
        bottom_fraction = self.config.get('bottom_fraction', 0.10)

        while current_index < total_pages:
            if self.stop_event.is_set():
                break

            msg = f"Scanning chunks starting from page {current_index + 1}..."
            self._emit('progress', current_index / total_pages, msg)
            logging.info(msg)

            scan_index = current_index
            pattern_found = False
            
            # Variables to determine the current chunk
            chunk_case_num = None
            chunk_start_page = 0
            chunk_end_page = 0

            while scan_index < total_pages:
                if self.stop_event.is_set():
                    break
                
                # Small sleep to yield GIL to Main Thread (UI) to prevent lag
                time.sleep(0.05)
                
                # Update granular progress
                self._emit('progress', scan_index / total_pages, f"Scanning page {scan_index + 1}...")

                # OCR
                left_img, right_img = self._get_footer_crops(doc, scan_index, bottom_fraction, dpi)
                
                # Logic from original script:
                # OCR left for case, right for page
                left_text_lines = self._ocr.extract_text(left_img, self.config)
                right_text_lines = self._ocr.extract_text(right_img, {**self.config, 'upscale': 1}) # original used upscale=1 for right

                detected_case = None if carried_case else self._detect_case_number(left_text_lines)
                detected_page = None if carried_page else self._detect_page_number(right_text_lines)

                current_case = carried_case or detected_case
                current_page_str = carried_page or detected_page
                
                logging.debug(f"P{scan_index+1}: Case={current_case}, Page={current_page_str}")

                # Update carry
                if detected_case and not detected_page:
                    carried_case = detected_case
                if detected_page and not detected_case:
                    carried_page = detected_page

                # Check pattern
                if current_case and current_page_str:
                    m = re.search(r"([0-9]+)\s*of\s*([0-9]+)", current_page_str)
                    if m:
                        chunk_start_page = int(m.group(1))
                        chunk_end_page = int(m.group(2))
                        chunk_case_num = current_case
                        pattern_found = True
                        break # Found the end of this current logical document definition? 
                        # Wait, original logic: it scans until it finds a "Page X of Y" and "Case Z". 
                        # If found, it assumes this page belongs to the document defined by "Page X of Y".
                        # The original logic loop:
                        # It scans *forward* until it finds a valid pattern (Case + Page X of Y).
                        # Once found, it calculates the *end* of the document based on the current page number X and total Y.
                        # Then it saves the chunk from start_idx to end_idx.
                        # Wait, if pattern is found at scan_index, and it says "Page 1 of 5", then the document is scan_index (page 1) to scan_index + 4.
                        # If pattern is found at scan_index, and it says "Page 3 of 5", then the document started 2 pages ago?
                        # Original logic:
                        # start_idx = current_index
                        # end_idx = scan_index + (end_page - start_page + 1) -> This assumes scan_index IS the page where we successfully read "Page start_page of end_page".
                        # If we are at scan_index, and we read "Page 1 of 5", start_page=1, end_page=5.
                        # end_idx (exclusive) = scan_index + (5 - 1 + 1) = scan_index + 5.
                        # Wait, if we are at scan_index=0 (absolute), and read Page 1 of 5.
                        # end_idx = 0 + 5 = 5. Pages 0,1,2,3,4. Corret.
                        # What if we read Page 3 of 5 at scan_index 2?
                        # start_idx (absolute) was current_index (0).
                        # end_idx = 2 + (5 - 3 + 1) = 2 + 3 = 5.
                        # Logic seems to assume the *current chunk being scanned* belongs to the detected document.
                
                scan_index += 1

            if not pattern_found:
                 # If no pattern found till end, maybe just save the rest as unknown or stop?
                 # Original script says "No valid patterns found. Stopping."
                 if not self.stop_event.is_set():
                     logging.warning("No valid pattern found in remaining pages.")
                 break
            
            # Reset carry
            carried_case = None
            carried_page = None

            # Determine range
            start_idx = current_index
            # Calculate end index based on the found pattern
            # Note: scan_index is where we found the match. 
            # If we found "Page S of E" at `scan_index`:
            # The document conceptually ends at `scan_index + (E - S)`. 
            # Total pages = E. Remaining pages = E - S.
            # So end_idx (exclusive) = scan_index + (E - S) + 1
            calculated_end = scan_index + (chunk_end_page - chunk_start_page) + 1
            
            # We must clamp to total_pages
            final_end_idx = min(calculated_end, total_pages)
            
            # Save
            # Save
            if chunk_case_num:
                # User requested format: [CaseNumber].pdf
                out_name = f"{chunk_case_num}.pdf"
            else:
                out_name = f"Unknown_pages_{start_idx + 1}-{final_end_idx}.pdf"

            # Add to summary data
            self.generated_files_data.append((out_name, start_idx + 1, final_end_idx))
                
            self._save_chunk(doc, start_idx, final_end_idx - 1, out_name)
            
            # Message
            self._emit('info', final_end_idx/total_pages, f"Saved {out_name}")
            
            # Advance
            current_index = final_end_idx

        doc.close()
        
        # Generate Excel Summary
        self._save_summary_excel()

    def _save_summary_excel(self):
        """Save processing summary to Excel"""
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Processing Summary"
            
            # Headers
            ws.append(["PDF File Generated Name", "PDF Start Location", "PDF End Location"])
            
            # Data
            for row in self.generated_files_data:
                ws.append(list(row))
                
            excel_path = self.output_folder / "summary.xlsx"
            wb.save(excel_path)
            logging.info(f"Summary Excel saved to: {excel_path}")
            self._emit('info', 1.0, f"Summary saved to summary.xlsx")
            
        except Exception as e:
            logging.error(f"Failed to save Excel summary: {e}")
            self._emit('error', 1.0, f"Failed to save Excel summary: {str(e)}")

    def _save_chunk(self, src_doc, start, end, filename):
        try:
            new_doc = fitz.open()
            new_doc.insert_pdf(src_doc, from_page=start, to_page=end)
            out_path = self.output_folder / filename
            new_doc.save(str(out_path))
            new_doc.close()
        except Exception as e:
            logging.error(f"Failed to save chunk {filename}: {e}")

    def _get_footer_crops(self, doc, page_idx, bottom_fraction, dpi):
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        
        w, h = img.size
        top = int(h * (1 - bottom_fraction))
        footer = img.crop((0, top, w, h))
        fw, fh = footer.size
        
        # Left crop (Case # area)
        lx1, lx2 = int(fw * 0.10), int(fw * 0.35)
        ly1, ly2 = int(fh * 0.20), int(fh * 0.60)
        left = footer.crop((lx1, ly1, lx2, ly2))
        
        # Right crop (Page # area)
        rx1, rx2 = int(fw * 0.80), int(fw * 0.95)
        ry1, ry2 = int(fh * 0.05), int(fh * 0.35)
        right = footer.crop((rx1, ry1, rx2, ry2))
        
        return left, right

    @staticmethod
    def _detect_case_number(text_list, threshold=70):
        # Adapted from original script
        best_score = 0
        best_match = None
        for text in text_list:
            score = fuzz.partial_ratio(text.lower(), "case number:")
            if score >= threshold and score > best_score:
                best_score = score
                best_match = text.strip()
        
        if best_match:
            return PDFProcessor._normalize_case_number(best_match)
        return None

    @staticmethod
    def _normalize_case_number(raw_text):
        # Adapted from original script
        pattern = ''.join(re.findall(r'[\dIl-]+', raw_text))
        pattern = pattern.replace('I', '1').replace('l', '1')
        pattern = pattern.lstrip('1-')
        segments = pattern.split('-')
        segments = [seg for seg in segments if seg]
        if not segments: return "I-"
        
        first = segments[0][-3:] if len(segments[0]) >= 3 else segments[0]
        middle = [seg[:3] for seg in segments[1:-1]]
        last = segments[-1] if len(segments) > 1 else ''
        
        final = [first] + middle
        if last: final.append(last)
        return 'I-' + '-'.join(final)

    @staticmethod
    def _detect_page_number(text_list, threshold=70):
        # Adapted from original script
        page_regex = re.compile(r"(page|pg)\s*[0-9I]+\s*of\s*[0-9I]+", re.IGNORECASE)
        best_score = 0
        best_match = None
        canonical = "page x of y"
        
        for text in text_list:
            if page_regex.search(text):
                score = fuzz.partial_ratio(text.lower(), canonical)
                if score >= threshold and score > best_score:
                    best_score = score
                    best_match = text.replace("I", "1").strip()
        return best_match

# Standalone worker function for multiprocessing (Must be outside class)
def run_processing_task(input_path, output_path, config, queue, stop_event):
    try:
        # Re-setup logging for this process if needed or relying on queue
        # We will rely on queue for specific updates
        
        processor = PDFProcessor(input_path, output_path, config)
        processor.set_queue(queue)
        processor.set_stop_event(stop_event)
        processor.run()
    except Exception as e:
        queue.put(('error', 0, str(e)))
