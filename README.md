# LCA Case Separator

A robust, modern desktop application designed to automatically separate consolidated PDF files into individual case files using OCR technology.

The application detects "Case Number" patterns and "Page X of Y" indicators on each page to intelligently split large documents, saving hours of manual work. Built with Python, PyQt6, and PaddleOCR.

## 🚀 Key Features

*   **Intelligent Separation**: Uses OCR (Optical Character Recognition) to read text on every page and detect case boundaries.
*   **Modern UI**: A clean, minimal, and responsive user interface built with PyQt6.
*   **Drag & Drop**: Simple drag-and-drop workflow for uploading files.
*   **Robust Logging**:
    *   **Global Logs**: Stored in `Documents/LCA_Logs/app.log` for application health.
    *   **Job Logs**: Detailed processing logs created in a `logs/` subfolder within your chosen output directory for every batch.
*   **Configurable**: Settings for OCR sensitivity and image preprocessing DPI/Contrast via `config.yaml`.
*   **Visual Feedback**: Real-time progress tracking, log viewing, and status updates during processing.

## 🛠️ Technology Stack

*   **Language**: Python 3.10+
*   **GUI Framework**: PyQt6 (Qt)
*   **OCR Engine**: PaddleOCR (High accuracy, supports angles and complex layouts)
*   **PDF Handling**: PyMuPDF (fitz) - Extremely fast PDF rendering and manipulation.
*   **Packaging**: PyInstaller (for creating standalone .exe)

## 📂 Project Structure

```
d:/PDF_Separator/ocr_app/
├── src/
│   ├── main.py              # Application entry point
│   ├── config/
│   │   └── app_config.py    # Configuration loader (Singleton)
│   ├── core/
│   │   ├── ocr_engine.py    # PaddleOCR wrapper and text extraction logic
│   │   ├── pdf_processor.py # PDF splitting and logic coordination
│   │   └── image_utils.py   # Image preprocessing (DPI, Contrast)
│   ├── ui/
│   │   └── main_window.py   # Main GUI window, layout, and event handling
│   └── utils/
│       └── logger.py        # Centralized logging configuration
├── assets/                  # Icons and static resources
├── config.yaml              # User configuration (generated on run)
├── requirements.txt         # Python dependencies
└── ocr_app.spec             # PyInstaller build specification
```

## ⚙️ Setup & Installation

### Prerequisites
*   **Python 3.10** or higher installed.
*   **Visual C++ Redistributable** (often required for PaddleOCR/OnnxRuntime on Windows).

### 1. Clone & Initialize
Navigate to the project directory:
```bash
cd d:\PDF_Separator\ocr_app
```

### 2. Create Virtual Environment
It is highly recommended to use a virtual environment to manage dependencies.
```bash
# Create venv
python -m venv venv

# Activate venv (Windows PowerShell)
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: This will install PyQt6, PaddleOCR, PyMuPDF, and other required libraries. This process may take a few minutes as it downloads OCR models.*

## ▶️ Usage

### Running from Source
To run the application in development mode:
```bash
python src/main.py
```

### Application Workflow
1.  **Select File**: Drag and drop a PDF file onto the upload zone.
2.  **Configure**: Choose the destination folder for the separated files.
3.  **Process**: Click "Start Processing". The app will analyze pages and split them automatically.
4.  **Review**: Check the logs window for details on detected case numbers.

## 🏎️ Architecture & Performance

The application is engineered for stability and high responsiveness using the following architecture:

1.  **Multiprocessing**: The heavy OCR lifting runs in a **separate system process** (`multiprocessing.Process`), completely isolated from the Main UI process. This ensures the application interface remains butter-smooth and responsive (drag/resize) even when the CPU is at 100% load.
2.  **Thread Limiting**: CPU affinity is strictly managed. Environment variables (`OMP_NUM_THREADS=1`, `PADDLE_NUM_THREADS=1`) are set to prevent the OCR engine from monopolizing all CPU cores, preventing system-wide freezes.
3.  **Excel Summary**: A `summary.xlsx` file is generated at the end of every job, listing every created PDF file and its source page range.

## 📝 Logging System

The application uses a dual-logging system ensures you never lose track of what happened.

1.  **Application Log**: 
    *   Location: `C:\Users\<User>\Documents\LCA_Logs\app.log`
    *   Purpose: Records startup errors, crashes, and global events.
2.  **Job Log**: 
    *   Location: `<OutputFolder>\logs\log_YYYY-MM-DD_HH-MM-SS.txt`
    *   Purpose: Specific details about that separation job (which pages went to which file).

## 📦 Building Executable

To package the application for distribution (Windows .exe), use **PyInstaller**.

1.  Ensure you have the development requirements installed:
    ```bash
    pip install pyinstaller
    ```
2.  Run the build command:
    ```bash
    pyinstaller ocr_app.spec
    ```
    *Alternatively, simple build command:*
    ```bash
    pyinstaller --noconsole --name "LCA_Case_Separator" --icon=assets/icon.ico --add-data "src;src" src/main.py
    ```
3.  The output executable will be in the `dist/` folder.

## 🔧 Configuration (config.yaml)

The `config.yaml` file allows you to tune the OCR engine:
```yaml
processing:
  dpi: 200          # Higher = better OCR but slower
  contrast: 1.2     # Increase contrast for faint text
  use_gpu: false    # Set to true if CUDA is available
```

## 🐛 Troubleshooting

*   **OCR Missing Text**: Try increasing `dpi` or `contrast` in config.
*   **PaddleOCR Error**: Ensure you have internet access on first run to download models (~20MB). If offline, manually place models in `~/.paddleocr`.
*   **Slow Processing**: OCR is CPU intensive. Reduce DPI to 150 for speed.

---
*Generated for internal developer documentation.*
