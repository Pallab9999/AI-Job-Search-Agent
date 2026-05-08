import logging
import os
from pathlib import Path

def setup_logger():
    """Set up the python logger."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File Handler
    fh = logging.FileHandler(log_dir / "agent.log")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger
