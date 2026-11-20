"""Offline lexical observations for consumers of the shared statement grammar."""
from dataclasses import dataclass
from functools import lru_cache

from company_wiki.implementation_identity import code_sha256
from company_wiki.wire_json import canonical_json_hash

from . import MAX_STATEMENT_CHARS, MAX_STATEMENT_TOKENS, __file__ as _GRAMMAR_FILE
from . import _chinese_tagger, resource_identity


@dataclass(frozen=True, slots=True)
class ChineseWord:
    start: int
    end: int
    tag: str


def chinese_words(text: str) -> tuple[ChineseWord, ...] | None:
    """Observe words and packaged POS labels in the matching text."""
    if len(text) > MAX_STATEMENT_CHARS:
        return None
    try:
        tokenizer, tags = _chinese_tagger()
        words = []
        offset = 0
        for word in tokenizer.cut(text, HMM=False):
            words.append(ChineseWord(offset, offset + len(word), tags.get(word, 'x')))
            offset += len(word)
            if len(words) > MAX_STATEMENT_TOKENS:
                return None
        return tuple(words)
    except (ImportError, OSError, LookupError, ValueError, KeyError, TypeError):
        return None


def chinese_word_boundaries(text: str) -> frozenset[int] | None:
    """Return word boundaries without claiming original source coordinates."""
    words = chinese_words(text)
    if words is None:
        return None
    return frozenset({0, *(word.end for word in words)})


@lru_cache(maxsize=2)
def lexical_identity(*, universal_newlines: bool = False) -> str:
    return canonical_json_hash({
        'word_boundaries': code_sha256(__file__, universal_newlines=universal_newlines),
        'tagger': code_sha256(_GRAMMAR_FILE, universal_newlines=universal_newlines),
        'resources': resource_identity(),
    })


__all__ = ['ChineseWord', 'chinese_word_boundaries', 'chinese_words', 'lexical_identity']
