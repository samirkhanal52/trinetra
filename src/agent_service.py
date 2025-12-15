import boto3
from botocore.exceptions import ClientError
import time
import os
import json
import logging
import signal
import tempfile
from datetime import datetime

import config
from uploader import UploaderService
from image_processor import ImageProcessor

class AgentService:
    """
    A service that polls S3 for new screenshots, processes them to generate
    insights, and saves the results back to S3.
    """

    def __init__(self, poll_interval: int = 60):
        # We can reuse the UploaderService's S3 client creation logic
        self.s3_client = UploaderService()._create_s3_client()
        self.processor = ImageProcessor()
        self.poll_interval = poll_interval
        self._shutdown = False
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down agent.")
        self._shutdown = True

    def run_forever(self):
        """The main blocking loop that orchestrates the processing."""
        logging.info(f"Agent service running with PID: {os.getpid()}")
        with open(config.AGENT_PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        while not self._shutdown:
            try:
                logging.info("Agent starting polling cycle...")
                
                # Define S3 prefixes
                screenshots_prefix = f"{config.S3_PREFIX}/screenshots/"
                notes_prefix = f"{config.S3_PREFIX}/notes/"

                logging.info(f"Reading objects from S3...{screenshots_prefix}")

                # 1. Get lists of existing screenshots and notes
                screenshot_keys = self._list_s3_objects(screenshots_prefix)
                note_keys = self._list_s3_objects(notes_prefix)

                # 2. Determine which screenshots are new
                processed_bases = {os.path.basename(key).split('.')[0] for key in note_keys}
                new_screenshots = [
                    key for key in screenshot_keys 
                    if os.path.basename(key).split('.')[0] not in processed_bases
                ]

                if new_screenshots:
                    logging.info(f"Found {len(new_screenshots)} new screenshots to process.")
                    self._process_screenshots(new_screenshots, notes_prefix)
                else:
                    logging.info("No new screenshots found.")

                logging.info(f"Agent cycle complete. Sleeping for {self.poll_interval} seconds.")
                time.sleep(self.poll_interval)

            except Exception as e:
                logging.error(f"An error occurred in the agent loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)
        
        logging.info("Agent service loop has stopped.")
        if os.path.exists(config.AGENT_PID_FILE):
            os.remove(config.AGENT_PID_FILE)
            
    def _list_s3_objects(self, prefix: str) -> set:
        """Lists all object keys within a given S3 prefix."""
        keys = set()
        paginator = self.s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=config.S3_BUCKET_NAME, Prefix=prefix)
        for page in pages:
            for obj in page.get('Contents', []):
                # Ensure we only consider files, not "folders"
                if not obj['Key'].endswith('/'):
                    keys.add(obj['Key'])
        return keys

    def _process_screenshots(self, keys: list, notes_prefix: str):
        """Downloads, processes, and uploads notes for a list of screenshot keys."""
        with tempfile.TemporaryDirectory() as temp_dir:
            for key in keys:
                if self._shutdown:
                    logging.info("Shutdown signal received, stopping processing.")
                    break
                
                try:
                    filename = os.path.basename(key)
                    local_path = os.path.join(temp_dir, filename)

                    # TO:DO --> Read from S3 directly without saving locally
                    logging.info(f"Downloading {key}...")
                    self.s3_client.download_file(config.S3_BUCKET_NAME, key, local_path)

                    # Process using the existing ImageProcessor
                    result = self.processor.process(local_path)

                    # Prepare the output JSON
                    timestamp_str = filename.split('_')[0]
                    result['timestamp_utc'] = datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S").isoformat()
                    result['source_screenshot_key'] = key
                    
                    # Upload the resulting note as a JSON file
                    note_basename = filename.split('.')[0] + ".json"
                    # Recreate the same time-based folder structure for notes
                    time_path = key.replace(f"{config.S3_PREFIX}/screenshots/", "").replace(filename, "")
                    note_key = os.path.join(notes_prefix, time_path, note_basename).replace("\\", "/")
                    
                    self._upload_note(result, note_key)

                except Exception as e:
                    logging.error(f"Failed to process screenshot {key}: {e}")
                finally:
                    # Clean up the local download
                    if os.path.exists(local_path):
                        os.remove(local_path)
    
    def _upload_note(self, note_data: dict, s3_key: str):
        """Uploads a dictionary as a JSON file to S3."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as tmp:
                json.dump(note_data, tmp)
                tmp_path = tmp.name
            
            self.s3_client.upload_file(tmp_path, config.S3_BUCKET_NAME, s3_key)
            logging.info(f"Successfully uploaded note to {s3_key}")
        except Exception as e:
            logging.error(f"Failed to upload note {s3_key}: {e}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
