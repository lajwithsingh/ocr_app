import os
# Disable OneDNN/MKL-DNN to avoid PaddlePaddle compatibility issues
os.environ['PADDLE_USE_MKLDNN'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'
# Limit CPU threads to prevent system freeze (95-99% usage issue)
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['PADDLE_NUM_THREADS'] = '1'

import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
from utils.logger import setup_logging

def main():
    """Application entry point"""
    import multiprocessing
    multiprocessing.freeze_support()
    
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
