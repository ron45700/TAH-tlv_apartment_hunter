import re

_PHONE_RE = re.compile(
    r"""
    (?<!\d)
    (?:
        \+972[-\s]?5\d(?:[-\s]?\d){7}
        |0\d{1,2}[-\s]?\d{3}[-\s]?\d{4}
        |0\d{8,9}
    )
    (?!\d)
    """,
    re.VERBOSE,
)


def extract_phones(text: str) -> list[str]:
    return [match.group(0) for match in _PHONE_RE.finditer(text)]


def canonical_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("972"):
        digits = "0" + digits[3:]
    return digits
