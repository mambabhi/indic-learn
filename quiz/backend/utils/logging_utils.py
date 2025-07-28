import logging
import os

# Resolve to project root
# ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # <--- ADDED ONE MORE os.path.dirname
LOG_DIR = os.path.join(ROOT_DIR, "logs")

# Ensure logs directory exists (optional)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")

# ... (your existing code) ...
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")
print(f"DEBUG_LOGGING: Log file path resolved to: {LOG_FILE}") # <--- ADD THIS LINE

logger = logging.getLogger("quiz_logger")  # use a unique name
logger.setLevel(logging.DEBUG)

# Set up logging
file_handler = logging.FileHandler(LOG_FILE, mode="w")  # overwrite every run
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

if logger.hasHandlers():
    logger.handlers.clear()  # prevent duplicate logs

logger.addHandler(file_handler)

def log_and_print(message, to_console=False):
    """Logs the message to file and optionally prints to console."""
    logger.info(message)  # ✅ use your custom logger, not the root one
    if to_console:
        print(message)