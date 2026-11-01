"""Explicit source turn markers shared by structure and physical continuity.

No speaker identity or answer truth is inferred from these formatting markers.
This leaf module deliberately does not depend on the structure package.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SOURCE_TURN_MARKER_VERSION = 'source-turn-marker/1'
SOURCE_TURN_MARKER_PREFIX_CHARS = 64
ROLE_INVESTOR = 'investor_question'
ROLE_MANAGEMENT = 'management'
_QUESTION_MARK = re.compile(r'^\s*(?:\d{1,3}\s*[、.．]\s*)?(?:问|問題|问题|Q|Question)\s*[:：]', re.I)
_ANSWER_MARK = re.compile(r'^\s*(?:答复|答覆|回答|答|回复|回覆|A|Answer)\s*[:：]', re.I)


def observed_source_turn(hints: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Use source speaker/turn evidence in either native or projected form."""
    native = hints.get('native_speaker_turn')
    native = native if isinstance(native, Mapping) else {}
    speaker = native.get('speaker', hints.get('speaker'))
    turn = native.get('turn_id', hints.get('turn_id'))
    return (speaker if isinstance(speaker, str) and speaker.strip() else None,
            turn if isinstance(turn, str) and turn.strip() else None)


def explicit_qa_marker(text: str) -> str | None:
    # Formatting lives in a bounded prefix. No full paragraph scan is needed
    # merely to observe Q:/A:, including in the physical source work account.
    prefix = text[:SOURCE_TURN_MARKER_PREFIX_CHARS]
    if _QUESTION_MARK.match(prefix):
        return ROLE_INVESTOR
    if _ANSWER_MARK.match(prefix):
        return ROLE_MANAGEMENT
    return None
