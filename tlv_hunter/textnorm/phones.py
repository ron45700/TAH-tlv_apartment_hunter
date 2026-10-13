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
    """Distinct phones in canonical form, in order of first appearance."""
    phones = (canonical_phone(match.group(0)) for match in _PHONE_RE.finditer(text))
    return list(dict.fromkeys(phones))


def canonical_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("972"):
        digits = "0" + digits[3:]
    return digits


def whatsapp_number(phone: str) -> str | None:
    """The number for WhatsApp's click-to-chat link, or `None` when the phone is not a mobile.

    A mobile is a canonical phone of 10 digits starting `05` (DECISIONS.md #330 point 22). The link
    takes the full international number with no `+`, zeros, brackets or dashes (WhatsApp Help
    Center, "How to use click to chat", read in a browser 2026-10-13): `0541234567` becomes
    `972541234567`."""
    digits = canonical_phone(phone)
    if len(digits) != 10 or not digits.startswith("05"):
        return None
    return "972" + digits[1:]
