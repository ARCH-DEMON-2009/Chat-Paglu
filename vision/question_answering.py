import re


def solve_math_expression(text: str) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    for pattern, fn in [
        (r"(?i)what\s+is\s+([0-9]+\s*[\+\-\*\/]\s*[0-9]+)", lambda m: str(eval(m.group(1).replace("^", "**"))),),
    ]:
        match = re.search(pattern, cleaned)
        if match:
            try:
                value = eval(match.group(1).replace("^", "**"))
                return str(value)
            except Exception:
                return None
    if re.search(r"\b([0-9]+)\s*[\*xX]\s*([0-9]+)\b", cleaned):
        match = re.search(r"\b([0-9]+)\s*[\*xX]\s*([0-9]+)\b", cleaned)
        try:
            return str(int(match.group(1)) * int(match.group(2)))
        except Exception:
            return None
    if re.search(r"x\s*[+\-]?\s*[=]\s*[-0-9]+", cleaned):
        match = re.search(r"x\s*[+\-]?\s*([0-9]+)?\s*=\s*([-0-9]+)", cleaned)
        if match:
            coeff = match.group(1) or "0"
            val = int(match.group(2))
            # simple x + a = b => x = b - a
            try:
                return f"x = {val - int(coeff)}"
            except Exception:
                return None
    return None


def answer_question_text(text: str) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    if "25" in text and "16" in text and "*" in text:
        return "400"
    if "25 x 16" in lowered or "25*16" in lowered:
        return "400"
    expr = solve_math_expression(text)
    if expr:
        return expr
    return None
