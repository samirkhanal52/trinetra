import os
from dotenv import load_dotenv
import logging

load_dotenv()

# --- Service Configuration ---
RECORDER_PID_FILE = "screenrec_recorder.pid"
UPLOADER_PID_FILE = "screenrec_uploader.pid"
AGENT_PID_FILE = "trinetra_agent.pid"
STOP_FILE = ".STOP_RECORDING" # Can be used as a global kill switch
DATA_DIR = "data"
OUTBOX_DIR = os.path.join(DATA_DIR, "outbox") # Shared directory for services

# --- S3/MinIO Configuration ---
USE_MINIO = os.getenv("USE_MINIO", "False").lower() in ('true', '1', 't')
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_PREFIX", "screen-recordings")

# AWS specific
AWS_REGION = os.getenv("AWS_REGION")

# MinIO specific
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

# Tesseract Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD")

def validate_config():
    """Validates that essential configuration is set."""
    if USE_MINIO:
        required_vars = ["MINIO_ENDPOINT_URL", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "S3_BUCKET_NAME"]
        logging.info("Using MinIO configuration.")
    else:
        required_vars = ["AWS_REGION", "S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
        logging.info("Using AWS S3 configuration.")
        
    missing_vars = [var for var in required_vars if not globals().get(var)]
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True
