import re

blocked_keywords = ["hack", "fraud", "illegal", "scam"]

blocked_patterns = [
    r"\b(fuck|shit|bitch|asshole|abuse|sex|porn)\b",
    r"ignore previous instructions",
    r"system prompt",
    r"act as",
    r"jailbreak",
]

def is_blocked(text):
    lower = text.lower()

    if any(word in lower for word in blocked_keywords):
        return True

    for pattern in blocked_patterns:
        if re.search(pattern, lower):
            return True

    return False
