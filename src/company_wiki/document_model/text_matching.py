"""Transient script interpretation shared by predicates, never source output.

This does not normalize original units, locators, span hashes or page views.
The existing OpenCC conversion remains the only script converter. Its context
is bounded to one converter per process; document strings are not cached.
"""
from functools import lru_cache
import re

SCRIPT_MATCHING_VERSION = "source-script-match/1"


@lru_cache(maxsize=1)
def _converter():
    import opencc

    return opencc.OpenCC("t2s.json")


def matching_script_text(text: str) -> str:
    """Keep legacy conversion exactly: no whitespace or punctuation rewrite."""
    if not isinstance(text, str):
        raise TypeError("matching text must be a string")
    if not any("\u3400" <= character <= "\u9fff" for character in text):
        return text
    return str(_converter().convert(text))


def matching_reading_text(text: str) -> str:
    """Interpret native wrapping for classification while preserving source data."""
    script = matching_script_text(text)
    compact = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", script)
    return compact.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


__all__ = ["SCRIPT_MATCHING_VERSION", "matching_script_text", "matching_reading_text"]
