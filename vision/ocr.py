import re


def extract_text_from_image(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    sanitized = raw_text.replace("\r", "\n")
    return sanitized.strip()


def normalize_question_text(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", raw_text)
    return text.strip()
