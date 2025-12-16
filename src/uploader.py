import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import time
import os
import json
import logging
import threading
from datetime import datetime

import utils, config

class UploaderService:
    """Watches a local directory and uploads new files to S3/MinIO."""

    def __init__(self, max_retries: int = 3):
        self.s3_client = self._create_s3_client()
        self._stop_event = threading.Event()
        self.max_retries = max_retries
        utils.safe_create_dir(config.OUTBOX_DIR)

    def _create_s3_client(self):
        """Creates a boto3 S3 client for either AWS or MinIO."""
        if config.TRINETRA_ENV == "local":
            logging.info(f"Connecting to MinIO at {config.MINIO_ENDPOINT_URL}")
            return boto3.client(
                's3',
                endpoint_url=config.MINIO_ENDPOINT_URL,
                aws_access_key_id=config.MINIO_ACCESS_KEY,
                aws_secret_access_key=config.MINIO_SECRET_KEY,
                region_name=config.AWS_REGION or 'us-east-1' # boto requires a region
            )
        else:
            logging.info(f"Connecting to AWS S3 in region {config.AWS_REGION}")
            return boto3.client('s3', region_name=config.AWS_REGION)

    # def start(self):
    #     """Starts the uploader loop in a separate thread."""
    #     logging.info("Starting uploader service...")
        
    #     # Ensure bucket exists
    #     self._ensure_bucket_exists()

    #     with open(config.UPLOADER_PID_FILE, "w") as f:
    #         f.write(str(os.getpid()))

    #     self.thread = threading.Thread(target=self._upload_loop)
    #     self.thread.daemon = True
    #     self.thread.start()
    #     logging.info(f"Uploader service running in background (PID: {os.getpid()}).")
    
    # def stop(self):
    #     self._stop_event.set()

    def _upload_loop(self):
        """Continuously scans the outbox directory and uploads files."""
        while not self._stop_event.is_set():
            try:
                files = os.listdir(config.OUTBOX_DIR)
                # Prioritize processing png files
                png_files = [f for f in files if f.endswith('.png')]
                
                if not png_files:
                    time.sleep(5) # Wait if directory is empty
                    continue

                for filename in png_files:
                    base_name, _ = os.path.splitext(filename)
                    image_path = os.path.join(config.OUTBOX_DIR, filename)
                    metadata_path = os.path.join(config.OUTBOX_DIR, f"{base_name}.json")

                    if os.path.exists(metadata_path):
                        self._process_and_upload(image_path, metadata_path)
                    
            except Exception as e:
                logging.error(f"Error in uploader loop: {e}")
                time.sleep(10) # Longer sleep on error
        
        logging.info("Uploader service loop has stopped.")
        if os.path.exists(config.UPLOADER_PID_FILE):
            os.remove(config.UPLOADER_PID_FILE)
            
    def _process_and_upload(self, image_path, metadata_path):
        """Uploads a single image-metadata pair and cleans up."""
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            timestamp = datetime.fromisoformat(metadata['timestamp_utc'])
            image_uuid = os.path.basename(image_path).split('_')[1].split('.')[0]
            
            s3_key = utils.get_s3_key_for_screenshot(config.S3_PREFIX, timestamp, image_uuid)
            
            success = self._upload_file_with_retry(image_path, s3_key, metadata)

            if success:
                os.remove(image_path)
                os.remove(metadata_path)
                logging.info(f"Cleaned up local files for {os.path.basename(image_path)}")

        except (FileNotFoundError, json.JSONDecodeError, IndexError) as e:
            logging.warning(f"Skipping corrupted/incomplete file pair: {image_path}. Error: {e}")
        except Exception as e:
            logging.error(f"Unexpected error processing {image_path}: {e}")

    def _upload_file_with_retry(self, local_path, s3_key, metadata):
        extra_args = {"ServerSideEncryption": "AES256", "Metadata": {k: str(v) for k, v in metadata.items()}}
        
        for attempt in range(self.max_retries):
            try:
                self.s3_client.upload_file(local_path, config.S3_BUCKET_NAME, s3_key, ExtraArgs=extra_args)
                logging.info(f"Successfully uploaded {local_path} to s3://{config.S3_BUCKET_NAME}/{s3_key}")
                return True
            except (ClientError, NoCredentialsError) as e:
                logging.error(f"S3 upload failed for {s3_key} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return False
        return False
        
    def _ensure_bucket_exists(self):
        """Creates the S3 bucket if it doesn't exist (useful for MinIO)."""
        try:
            self.s3_client.head_bucket(Bucket=config.S3_BUCKET_NAME)
            logging.info(f"Bucket '{config.S3_BUCKET_NAME}' already exists.")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logging.info(f"Bucket '{config.S3_BUCKET_NAME}' not found. Creating it...")
                try:
                    # For AWS, specifying a region other than us-east-1 requires LocationConstraint
                    if config.AWS_REGION and config.AWS_REGION != 'us-east-1' and config.TRINETRA_ENV == "prod":
                        self.s3_client.create_bucket(Bucket=config.S3_BUCKET_NAME, CreateBucketConfiguration={'LocationConstraint': config.AWS_REGION})
                    else:
                        self.s3_client.create_bucket(Bucket=config.S3_BUCKET_NAME)
                    logging.info(f"Bucket '{config.S3_BUCKET_NAME}' created successfully.")
                except Exception as create_error:
                    logging.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                logging.error(f"Error checking for bucket: {e}")
                raise
