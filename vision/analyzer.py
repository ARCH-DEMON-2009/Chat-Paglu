import os
import re
from typing import Any, Dict, Optional

from vision.ocr import extract_text_from_image, normalize_question_text
from vision.question_answering import answer_question_text


class VisionService:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def analyze_image(self, image_path: str | None = None, raw_text: str | None = None) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "description": "Vision is disabled."}
        text = normalize_question_text(raw_text or extract_text_from_image(raw_text))
        answer = answer_question_text(text)
        description = "A user uploaded an image; OCR/vision analysis was attempted."
        if answer:
            return {"status": "ok", "description": description, "extracted_text": text, "answer": answer}
        return {"status": "ok", "description": description, "extracted_text": text}

    def extract_image_text(self, image_path: str | None = None, raw_text: str | None = None) -> str:
        return normalize_question_text(raw_text or "")

    def answer_image_question(self, text: str) -> str:
        result = answer_question_text(text)
        if result:
            return result
        if not text or not text.strip():
            return "I can’t read the image clearly yet. Please send a clearer photo."
        return "I can’t confidently read the text in this image. Please send a clearer version."

    def describe_image(self, image_path: str | None = None, raw_text: str | None = None) -> str:
        text = self.extract_image_text(image_path, raw_text)
        return f"I looked at the image and saw: {text[:180]}" if text else "The image is unclear or too difficult to read from the current upload."


service = VisionService(enabled=True)


def analyze_image(*args, **kwargs):
    return service.analyze_image(*args, **kwargs)


def extract_image_text(*args, **kwargs):
    return service.extract_image_text(*args, **kwargs)


def answer_image_question(*args, **kwargs):
    return service.answer_image_question(*args, **kwargs)


def describe_image(*args, **kwargs):
    return service.describe_image(*args, **kwargs)
