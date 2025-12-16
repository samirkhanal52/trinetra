import time
import os
import logging
import signal
import tempfile
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from . import config
from .processor import ImageProcessor
from .uploader_service import UploaderService

class IndexingService:
    """
    A service that polls S3 for new screenshots, processes them into Action Logs,
    and indexes them into a vector database.
    """
    def __init__(self):
        self.s3_client = UploaderService()._create_s3_client()
        self.processor = ImageProcessor()
        self.embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = Chroma(
            persist_directory=config.CHROMA_DB_PATH,
            embedding_function=self.embedding_model
        )
        self._shutdown = False
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down indexing service.")
        self._shutdown = True

    def run_forever(self):
        logging.info(f"Indexing service running with PID: {os.getpid()}")
        with open(config.INDEXING_PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        while not self._shutdown:
            try:
                logging.info("Indexing service starting polling cycle...")
                screenshots_prefix = f"{config.S3_PREFIX}/screenshots/"
                
                new_screenshots = self._find_new_screenshots(screenshots_prefix)

                if new_screenshots:
                    logging.info(f"Found {len(new_screenshots)} new screenshots to index.")
                    self._process_and_index(new_screenshots)
                else:
                    logging.info("No new screenshots found.")

                logging.info("Indexing cycle complete. Sleeping for 60 seconds.")
                time.sleep(60)
            except Exception as e:
                logging.error(f"An error occurred in the indexing loop: {e}", exc_info=True)
                time.sleep(60)
        
        logging.info("Indexing service loop has stopped.")
        if os.path.exists(config.INDEXING_PID_FILE):
            os.remove(config.INDEXING_PID_FILE)
            
    def _find_new_screenshots(self, prefix: str) -> list:
        # Get all S3 screenshot keys
        paginator = self.s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=config.S_BUCKET_NAME, Prefix=prefix)
        all_s3_keys = {obj['Key'] for page in pages for obj in page.get('Contents', []) if obj['Key'].endswith('.png')}
        
        # Get all documents already in the vector store
        existing_docs = self.vector_store.get()
        indexed_keys = {meta['source_s3_key'] for meta in existing_docs['metadatas']}

        return list(all_s3_keys - indexed_keys)

    def _process_and_index(self, keys: list):
        with tempfile.TemporaryDirectory() as temp_dir:
            for key in keys:
                if self._shutdown: break
                
                try:
                    local_path = os.path.join(temp_dir, os.path.basename(key))
                    self.s3_client.download_file(config.S3_BUCKET_NAME, key, local_path)
                    
                    action_log = self.processor.process(local_path)
                    if not action_log: continue

                    doc_text = (
                        f"Activity: {action_log['activity_summary']}\n"
                        f"Application: {action_log['primary_application']}\n"
                        f"Category: {action_log['task_category']}\n"
                        f"Keywords: {', '.join(action_log['keywords'])}"
                    )
                    timestamp_str = os.path.basename(key).split('_')[0]
                    metadata = {
                        "source_s3_key": key,
                        "timestamp_utc": datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S").isoformat(),
                        "category": action_log['task_category'],
                        "application": action_log['primary_application']
                    }
                    
                    self.vector_store.add_texts(texts=[doc_text], metadatas=[metadata])
                    logging.info(f"Successfully indexed document for {key}")

                except Exception as e:
                    logging.error(f"Failed to index key {key}: {e}")
                finally:
                    if os.path.exists(local_path): os.remove(local_path)
