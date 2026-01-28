import logging
import queue
from logging import handlers

# Global log queue for UI consumer
log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    """
    This handler sends events to a queue which will be populated in the UI.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

def setup_logging(log_file="app.log", log_level=logging.INFO):
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Formatters
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')

    # Determine log path in Documents folder
    from pathlib import Path
    from datetime import datetime
    
    log_dir = Path.home() / "Documents" / "LCA_Logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_file
    
    # File Handler
    file_handler = handlers.RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console Handler (for dev debug)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # UI Queue Handler
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(file_formatter)
    root_logger.addHandler(queue_handler)

    logging.info(f"Logging initialized. Logs stored at: {log_path}")

def add_output_logging(output_dir):
    """Add a file handler to the output directory logs folder with timestamp"""
    from pathlib import Path
    from datetime import datetime
    try:
        log_dir = Path(output_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        # Timestamp based filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = log_dir / f"log_{timestamp}.txt"
        
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        handler = logging.FileHandler(log_file) # No rotation for unique files
        handler.setFormatter(file_formatter)
        logging.getLogger().addHandler(handler)
        logging.info(f"Additional logging started in: {log_file}")
        return handler
    except Exception as e:
        logging.error(f"Failed to setup output logging: {e}")
        return None

def remove_handler(handler):
    """Remove and close a log handler"""
    if handler:
        try:
            logging.getLogger().removeHandler(handler)
            handler.close()
        except Exception as e:
            print(f"Error removing handler: {e}")
