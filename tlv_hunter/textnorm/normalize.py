import hashlib
import re
import unicodedata

from tlv_hunter.textnorm.blank import is_blank

_NIQUD_RE = re.compile("[\u0591-\u05c7]")
_QUOTES_RE = re.compile("[\u05f3\u05f4\u2018\u2019\u201c\u201d\"']")
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\u2600-\u27bf\U0001f1e6-\U0001f1ff\u2190-\u21ff\u2b00-\u2bff\ufe0f]+"
)
_FINAL_LETTERS = str.maketrans(
    {
        "\u05da": "\u05db",
        "\u05dd": "\u05de",
        "\u05df": "\u05e0",
        "\u05e3": "\u05e4",
        "\u05e5": "\u05e6",
    }
)
_WHITESPACE_RE = re.compile(r"\s+")


class UnhashableTextError(ValueError):
    """Text is not blank but normalizes to nothing (e.g. emoji only). Handling is undecided."""


def compute_text_hash(text: str) -> str | None:
    if is_blank(text):
        return None
    normalized = _normalize_for_hash(text)
    if not normalized:
        raise UnhashableTextError("text is not blank but normalizes to an empty string")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_for_hash(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _NIQUD_RE.sub("", text)
    text = _QUOTES_RE.sub("", text)
    text = _EMOJI_RE.sub("", text)
    text = text.translate(_FINAL_LETTERS)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip().lower()
