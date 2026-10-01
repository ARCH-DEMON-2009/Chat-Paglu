import os
import re
import mimetypes
from typing import Any, Dict, Optional

from vision.ocr import extract_text_from_image, normalize_question_text
from vision.question_answering import answer_question_text
from ai_chat import call_gemini_with_fallback

try:
    from google.genai import types
except Exception:  # pragma: no cover - optional dependency fallback
    types = None


class VisionService:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def analyze_image(self, image_path: str | None = None, raw_text: str | None = None, image_bytes: bytes | None = None, mime_type: str = 'image/jpeg') -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "description": "Vision is disabled."}
        if image_bytes is None and image_path:
            try:
                with open(image_path, 'rb') as image_file:
                    image_bytes = image_file.read()
            except OSError:
                return {"status": "error", "description": "The image could not be read."}
        text = normalize_question_text(raw_text or extract_text_from_image(raw_text))
        answer = self.answer_image_question(text or 'Describe this image and read any visible text.', image_bytes, mime_type)
        description = "Image analysis completed."
        if answer:
            return {"status": "ok", "description": description, "extracted_text": text, "answer": answer}
        return {"status": "ok", "description": description, "extracted_text": text}

    def extract_image_text(self, image_path: str | None = None, raw_text: str | None = None) -> str:
        if raw_text:
            return normalize_question_text(raw_text)
        if not self.enabled or not image_path or types is None:
            return ""
        try:
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
        except OSError:
            return ""
        mime_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
        response = call_gemini_with_fallback(
            ['Extract all clearly visible text from this image. Return only the text; do not describe the image. Make no guesses about unclear text.', types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
            'Transcribe visible text exactly. If no readable text is present, return an empty response.',
            temperature=0.1,
            model=os.getenv('VISION_MODEL', os.getenv('AI_MODEL', 'gemini-2.5-flash')),
        )
        result = getattr(response, 'text', None) if response is not None else None
        return normalize_question_text(result)

    def answer_image_question(self, text: str, image_bytes: bytes | None = None, mime_type: str = 'image/jpeg') -> str:
        if not self.enabled:
            return "Image analysis is currently disabled."
        result = answer_question_text(text)
        if result:
            return result
        if image_bytes and types is not None:
            response = call_gemini_with_fallback(
                [text, types.Part.from_bytes(data=image_bytes, mime_type=mime_type)],
                'Answer the user’s question about the attached image. Describe only visible details, read visible text when possible, and say when something is unclear. Keep the answer concise.',
                temperature=0.2,
                model=os.getenv('VISION_MODEL', os.getenv('AI_MODEL', 'gemini-2.5-flash')),
            )
            answer = getattr(response, 'text', None) if response is not None else None
            if isinstance(answer, str) and answer.strip():
                return answer.strip()
        if not text or not text.strip():
            return "I can’t read the image clearly yet. Please send a clearer photo."
        if image_bytes:
            return "I couldn’t analyze that image right now. Please try again in a moment."
        return "I can’t confidently read the text in this image. Please send a clearer version."

    def describe_image(self, image_path: str | None = None, raw_text: str | None = None) -> str:
        if raw_text:
            return f"I looked at the image and saw: {normalize_question_text(raw_text)[:180]}"
        if not self.enabled or not image_path:
            return "The image is unclear or too difficult to read from the current upload."
        try:
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
        except OSError:
            return "The image could not be read."
        mime_type = mimetypes.guess_type(image_path)[0] or 'image/jpeg'
        return self.answer_image_question('Describe the visible contents of this image.', image_bytes, mime_type)


service = VisionService(enabled=True)


def analyze_image(*args, **kwargs):
    return service.analyze_image(*args, **kwargs)


def extract_image_text(*args, **kwargs):
    return service.extract_image_text(*args, **kwargs)


def answer_image_question(*args, **kwargs):
    return service.answer_image_question(*args, **kwargs)


def describe_image(*args, **kwargs):
    return service.describe_image(*args, **kwargs)
