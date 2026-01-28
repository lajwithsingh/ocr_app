import os
# Disable OneDNN/MKL-DNN to avoid PaddlePaddle compatibility issues
os.environ['PADDLE_USE_MKLDNN'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'

import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logging

def main():
    """Application entry point"""
    # Initialize logging with file and UI support
    setup_logging()
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("PDF Automatic Splitter")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
