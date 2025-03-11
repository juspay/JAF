import os
import logging

def init_logger(name: str):
    # Use the same settings as above for root logger
    logger = logging.getLogger(name)
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.setLevel(log_level)    

    if not logger.handlers:
        # Create a console handler and set its logging level
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # # Create a formatter and set it for the handler
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # # Add the handler to the logger
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger
