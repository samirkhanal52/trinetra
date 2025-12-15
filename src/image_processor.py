import logging
from PIL import Image
import pytesseract
from transformers import pipeline

import config

# Conditional import for HuggingFace to avoid hard dependency if not used
try:
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

class ImageProcessor:
    """Processes a single screenshot to extract text, caption, and insights."""

    def __init__(self):
        self.captioner = None
        if HF_AVAILABLE:
            try:
                # This will download the model on first run
                logging.info("Initializing HuggingFace image-to-text model...")
                self.captioner = pipeline("image-to-text", model="nlpconnect/vit-gpt2-image-captioning")
                logging.info("HuggingFace model loaded successfully.")
            except Exception as e:
                logging.warning(f"Could not load HuggingFace model. Captioning will be disabled. Error: {e}")
                self.captioner = None
        else:
            logging.warning("HuggingFace 'transformers' not installed. Captioning will be disabled.")

        if config.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

    def _get_caption(self, image_path: str) -> str:
        """Generates a caption for the image."""
        if not self.captioner:
            return "Image captioning model not available."
        try:
            caption = self.captioner(image_path)[0]['generated_text']
            return caption
        except Exception as e:
            logging.error(f"Failed to generate caption for {image_path}: {e}")
            return "Caption generation failed."

    def _get_text(self, image_path: str) -> str:
        """Extracts text from the image using OCR."""
        try:
            return pytesseract.image_to_string(Image.open(image_path), timeout=10)
        except pytesseract.TesseractNotFoundError:
            logging.error("Tesseract is not installed or not in your PATH. OCR functionality is disabled.")
            return ""
        except Exception as e:
            logging.error(f"OCR failed for {image_path}: {e}")
            return ""

    def _categorize_action(self, text: str, caption: str) -> str:
        """Assigns a category based on keywords in text and caption."""
        text_lower = text.lower()
        
        # Define keyword mappings for categories
        # Order matters: more specific checks should come first
        category_keywords = {
            "Coding": ["visual studio code", "vscode", "pycharm", "github", "gitlab", "docker", "terminal", "console", "def ", "import "],
            "Meeting": ["zoom", "microsoft teams", "google meet", "slack huddle", "webex"],
            "Email": ["outlook", "gmail", "compose", "subject:", "inbox"],
            "Browsing": ["http:", "https://", "chrome", "firefox", "edge", "safari", "search results"],
            "Productivity-App": ["excel", "powerpoint", "word", "jira", "asana", "trello", "notion"],
            "System": ["settings", "file explorer", "control panel", "task manager", "start menu"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return category

        if not text.strip():
            return "Idle"
            
        return "Other"

    def _generate_summary(self, text: str, caption: str) -> str:
        """Creates a one-sentence summary of the user's action."""
        first_line = text.split('\n')[0].strip()
        if len(first_line) > 100:
            first_line = first_line[:100] + "..."
        
        if first_line:
            return f"User is viewing a window with text: '{first_line}'."
        
        # Fallback to caption if OCR text is empty
        clean_caption = caption.replace("a screenshot of", "").strip()
        return f"User is viewing: {clean_caption}."

    def process(self, image_path: str) -> dict:
        """
        Processes a single image and returns a dictionary of insights.
        """
        logging.info(f"Processing image: {image_path}")
        caption = self._get_caption(image_path)
        text = self._get_text(image_path)
        
        summary = self._generate_summary(text, caption)
        category = self._categorize_action(text, caption)
        
        return {
            "caption": caption,
            "ocr_text": text,
            "summary": summary,
            "note_category": category
        }
