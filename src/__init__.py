"""
Trinetra - A CLI tool to record screen activity, upload to S3, and generate summaries.
"""

__version__ = "1.0.0"
__author__ = "Samir Khanal"
__email__ = "samir.khanal458@gmail.com"

# Import main components for easier access
from src.cli import cli
from src.indexing_service import IndexingService
from src.processor import ImageProcessor
from src.recorder import RecorderService
from src.uploader import UploaderService

__all__ = [
    "cli",
    "RecorderService",
    "UploaderService",
    "ImageProcessor",
    "IndexingService",
]
