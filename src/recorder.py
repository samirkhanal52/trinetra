import json
import logging
import os
import signal
import time
import uuid
from datetime import datetime

import mss
import mss.tools

import src.config as config
import src.utils as utils
from src.uploader import UploaderService


class RecorderService:
    """Captures the screen and saves screenshots and metadata locally."""

    def __init__(self):
        self._shutdown = False
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle termination signals gracefully."""
        logging.info(f"Received signal {signum}, shutting down recorder.")
        self._shutdown = True

    def run_forever(self):
        """The main blocking loop that captures and saves screenshots."""
        utils.safe_create_dir(config.OUTBOX_DIR)

        # Write PID to file for the 'stop' command to find
        with open(config.RECORDER_PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        logging.info(f"Recorder service running with PID: {os.getpid()}")

        with mss.mss() as sct:
            while not self._shutdown:
                try:
                    start_time = time.time()

                    image_uuid = str(uuid.uuid4())
                    timestamp = datetime.utcnow()
                    base_filename = (
                        f"{timestamp.strftime('%Y%m%dT%H%M%S')}_{image_uuid}"
                    )

                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)

                    local_image_path = os.path.join(
                        config.OUTBOX_DIR, f"{base_filename}.png"
                    )
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=local_image_path)

                    metadata = utils.create_metadata(
                        (monitor["width"], monitor["height"])
                    )
                    local_metadata_path = os.path.join(
                        config.OUTBOX_DIR, f"{base_filename}.json"
                    )
                    with open(local_metadata_path, "w") as f:
                        json.dump(metadata, f)

                    uploader_service = UploaderService()
                    uploader_service._process_and_upload(
                        local_image_path, local_metadata_path
                    )

                    logging.info(f"Captured screenshot: {base_filename}.png")

                    elapsed = time.time() - start_time
                    time.sleep(max(0, 1.0 - elapsed))

                except Exception as e:
                    logging.error(f"Error in recorder loop: {e}")
                    time.sleep(5)

        logging.info("Recorder service loop has stopped.")
        if os.path.exists(config.RECORDER_PID_FILE):
            os.remove(config.RECORDER_PID_FILE)
