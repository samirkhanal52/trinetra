import base64
import json
import logging
from PIL import Image
import pytesseract
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from . import config

# --- PDO Prompt Template ---
PDO_PROMPT = """
**Persona:** You are an expert productivity analyst AI. Your task is to meticulously analyze a user's screen capture to understand their activity.

**Objective:** Examine the provided screenshot and its corresponding OCR text. From this data, determine the user's primary activity, the main application in use, and classify the task into a predefined category. Your analysis must be concise, accurate, and structured.

**Desired Output:** Provide your analysis in a single, clean JSON object. Do not include any explanatory text, markdown formatting, or apologies. The JSON object must have the following keys and data types:
- `primary_application`: string (e.g., "Visual Studio Code", "Google Chrome", "Microsoft Outlook")
- `activity_summary`: string (A brief, one-sentence summary of what the user is doing. e.g., "Debugging a Python function in the recorder_service.py file.")
- `task_category`: string (Must be one of the following enums: "Coding", "Email", "Browsing", "Meeting", "System", "Productivity-App", "Idle", "Other")
- `keywords`: array of strings (List of 3-5 important keywords or entities from the screen, like filenames, function names, or website titles.)
"""

class ImageProcessor:
    """
    Processes screenshots using a multi-modal LLM to generate structured "Action Logs".
    """
    def __init__(self):
        # Using a powerful multi-modal model is key.
        self.llm = ChatOpenAI(model="gpt-4o", max_tokens=512)
        if config.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

    def _get_text_from_image(self, image_path: str) -> str:
        try:
            return pytesseract.image_to_string(Image.open(image_path), timeout=15)
        except Exception as e:
            logging.error(f"OCR failed for {image_path}: {e}")
            return ""

    @staticmethod
    def _encode_image(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def process(self, image_path: str) -> dict | None:
        """
        Processes a single image and returns a structured dictionary (Action Log).
        """
        logging.info(f"Processing image with GenAI: {image_path}")
        ocr_text = self._get_text_from_image(image_path)
        base64_image = self._encode_image(image_path)

        message = HumanMessage(
            content=[
                {"type": "text", "text": PDO_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
                {"type": "text", "text": f"Here is the supplementary OCR text to aid your analysis:\n\n---\n{ocr_text[:2000]}\n---"},
            ]
        )
        
        try:
            response = self.llm.invoke([message])
            action_log = json.loads(response.content)
            logging.info(f"Successfully generated Action Log for {image_path}")
            return action_log
        except json.JSONDecodeError:
            logging.error("Failed to parse JSON response from LLM.")
            return None
        except Exception as e:
            logging.error(f"LLM invocation failed: {e}")
            return None
