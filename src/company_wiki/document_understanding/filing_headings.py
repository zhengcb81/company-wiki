"""Shared lexical evidence for numbered filing headings."""

import re


def part_heading_level(text: str) -> int | None:
    value = " ".join(text.strip().split())
    match = re.fullmatch(
        r"PART\s+(II|I)\b(?:\s*[.—–:−-]\s*|\s+)?(.*)", value, re.IGNORECASE
    )
    if not match or len(value) > 100:
        return None
    title = match.group(2).strip()
    if not title:
        return 1
    if title.casefold() in {"financial information", "other information"}:
        return 1
    if (
        title == title.upper()
        and title.isascii()
        and re.fullmatch(r"[A-Z][A-Z /&-]*", title)
        and not title.startswith(("OF ", "IS ", "WAS ", "AND "))
    ):
        return 1
    return None


def is_item_label(text: str) -> bool:
    return re.fullmatch(r"Item\s+\d{1,2}[A-Za-z]?\.?", text.strip(), re.IGNORECASE) is not None


def is_item_heading(text: str) -> bool:
    return re.match(r"^Item\s+\d{1,2}[A-Za-z]?\b(?:\.|\s|$)", text.strip(), re.IGNORECASE) is not None


__all__ = ["is_item_heading", "is_item_label", "part_heading_level"]
