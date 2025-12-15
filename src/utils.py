import logging
import os
import uuid
from datetime import datetime
import json
import socket

def setup_logging():
    """Configures basic logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def get_s3_key_for_screenshot(prefix: str, timestamp: datetime, image_uuid: str) -> str:
    """Generates the S3 key for a screenshot based on date and time."""
    return (
        f"{prefix}/screenshots/{timestamp.strftime('%Y/%m/%d/%H')}/"
        f"{timestamp.strftime('%Y%m%dT%H%M%S')}_{image_uuid}.png"
    )

def get_s3_key_for_metadata(s3_image_key: str) -> str:
    """Generates the S3 key for a metadata file corresponding to a screenshot."""
    return s3_image_key.replace(".png", ".json")

def create_metadata(resolution: tuple) -> dict:
    """Creates a metadata dictionary for a screenshot."""
    now = datetime.utcnow()
    return {
        "timestamp_utc": now.isoformat(),
        "hostname": socket.gethostname(),
        "resolution": f"{resolution[0]}x{resolution[1]}",
        "recorder_id": str(uuid.uuid4()) # A unique ID for this recording session or instance
    }

def safe_create_dir(dir_path: str):
    """Safely creates a directory if it doesn't exist."""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def get_pid_from_file(pid_file: str) -> int | None:
    """Reads a PID from a file."""
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                return int(f.read().strip())
        except (IOError, ValueError):
            return None
    return None
