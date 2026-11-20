"""Offline word boundaries for consumers of the shared statement grammar."""
from functools import lru_cache

from company_wiki.implementation_identity import code_sha256
from company_wiki.wire_json import canonical_json_hash

from . import MAX_STATEMENT_CHARS, MAX_STATEMENT_TOKENS, __file__ as _GRAMMAR_FILE
from . import _chinese_tagger, resource_identity


def chinese_word_boundaries(text: str) -> frozenset[int] | None:
    """Return offsets in the matching text. Ambiguous or unavailable input can abstain."""
    if len(text) > MAX_STATEMENT_CHARS:
        return None
    try:
        tokenizer, _ = _chinese_tagger()
        boundaries = {0}
        offset = 0
        for word in tokenizer.cut(text, HMM=False):
            offset += len(word)
            boundaries.add(offset)
            if len(boundaries) > MAX_STATEMENT_TOKENS + 1:
                return None
        return frozenset(boundaries)
    except (ImportError, OSError, LookupError, ValueError, KeyError, TypeError):
        return None


@lru_cache(maxsize=2)
def lexical_identity(*, universal_newlines: bool = False) -> str:
    return canonical_json_hash({
        'word_boundaries': code_sha256(__file__, universal_newlines=universal_newlines),
        'tagger': code_sha256(_GRAMMAR_FILE, universal_newlines=universal_newlines),
        'resources': resource_identity(),
    })


__all__ = ['chinese_word_boundaries', 'lexical_identity']
