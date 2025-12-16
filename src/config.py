import os
from dotenv import load_dotenv
import logging

load_dotenv()

# --- Service Configuration ---
RECORDER_PID_FILE = "screenrec_recorder.pid"
UPLOADER_PID_FILE = "screenrec_uploader.pid"
INDEXING_PID_FILE = "trinetra_indexing.pid"
STOP_FILE = ".STOP_RECORDING" # Can be used as a global kill switch
DATA_DIR = "data"
OUTBOX_DIR = os.path.join(DATA_DIR, "outbox") # Shared directory for services

# --- S3/MinIO Configuration ---
TRINETRA_ENV = os.getenv("TRINETRA_ENV", "local").lower()
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_PREFIX", "screen-recordings")

# AWS specific
AWS_REGION = os.getenv("AWS_REGION")

# MinIO specific
MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

# --- Vector Database Path ---
CHROMA_DB_PATH = "chroma_db"

# --- Generative AI Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def validate_config():
    """Validates that essential configuration is set."""
    if TRINETRA_ENV == "local":
        required_vars = ["MINIO_ENDPOINT_URL", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "S3_BUCKET_NAME"]
        logging.info("Using MinIO configuration.")
    else:
        required_vars = ["AWS_REGION", "S3_BUCKET_NAME", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
        logging.info("Using AWS S3 configuration.")
        
    missing_vars = [var for var in required_vars if not globals().get(var)]
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    if not OPENAI_API_KEY:
        logging.warning("OPENAI_API_KEY is not set. AI processing features will fail.")

    return True
