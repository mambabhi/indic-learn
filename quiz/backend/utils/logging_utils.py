import logging
import os

# Ensure logs directory exists (optional)
os.makedirs("logs", exist_ok=True)

# Set up logging
logging.basicConfig(
    filename="logs/pipeline.log",  # Change path as needed
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

def log_and_print(message, to_console=False):
    """Logs the message to file and optionally prints to console."""
    logging.info(message)
    if to_console:
        print(message)
