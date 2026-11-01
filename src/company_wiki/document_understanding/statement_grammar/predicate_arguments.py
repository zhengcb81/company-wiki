"""Forward POS argument scopes; no industry vocabulary or factual inference."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PredicateArgumentScope:
    predicate: str
    argument_nominals: tuple[str, ...]
    attachment: str = 'complement'
    argument_quantifiers: tuple[str, ...] = ()
    argument_modifiers: tuple[str, ...] = ()


def predicate_argument_scopes(tagged: list[tuple[str, str]], start: int, *,
                             language: str) -> tuple[PredicateArgumentScope, ...]:
    """Keep each predicate's direct NP without borrowing beneficiary PPs.

    POS conjunctions coordinate either nominal arguments or verbal scopes.
    Infinitival/gerund complements and direct-object relatives retain their
    own arguments. A relative modifying a prepositional beneficiary remains
    background, including its coordinated predicates. This is a bounded
    linear observation of supplied tags, never a retag or source rewrite.
    """
    scopes: list[PredicateArgumentScope] = []
    predicate = ''
    arguments: list[str] = []
    quantifiers: list[str] = []
    modifiers: list[str] = []
    attachment = 'complement'
    background = False
    background_relative = False
    prep_waiting = False
    coordinated = False

    def flush() -> None:
        nonlocal arguments, quantifiers, modifiers
        if predicate and (arguments or quantifiers):
            scopes.append(PredicateArgumentScope(predicate, tuple(arguments), attachment,
                                                  tuple(quantifiers), tuple(modifiers)))
        arguments = []
        quantifiers = []
        modifiers = []

    for word, tag in tagged[start:]:
        if word in {'.', '。', '!', '！', '?', '？', ';', '；'}:
            flush()
            break
        nominal = (tag in {'NN', 'NNS', 'NNP', 'NNPS'} if language == 'en'
                   else tag.startswith('n') or tag == 'eng')
        verbal = tag.startswith('VB') if language == 'en' else tag in {'v', 'vn'}
        conjunction = tag == ('CC' if language == 'en' else 'c')
        preposition = tag in {'IN', 'TO'} if language == 'en' else tag == 'p'
        relative = language == 'en' and tag in {'WDT', 'WP', 'WP$'}
        quantified = tag == ('CD' if language == 'en' else 'm')
        modifier = tag in ({'JJ', 'JJR', 'JJS'} if language == 'en' else {'a', 'ad', 'an', 'b'})
        if relative:
            flush()
            background_relative = background
            attachment = 'background_relative' if background else 'direct_relative'
            continue
        if conjunction or word in {',', '，'}:
            coordinated = True
            continue
        if preposition:
            flush()
            background = True
            prep_waiting = True
            continue
        if verbal:
            if background_relative:
                continue
            if background:
                # A bare noun after a PP marks its background object. A verb
                # directly after the preposition instead introduces a verbal
                # complement (to treat / by treating). Chinese PP adjuncts
                # precede the predicate rather than containing finite VPs.
                if not (coordinated or prep_waiting or language == 'zh'):
                    continue
                background = False
            flush()
            predicate = word
            prep_waiting = False
            coordinated = False
            continue
        if nominal:
            if background or background_relative:
                prep_waiting = False
                coordinated = False
                continue
            arguments.append(word)
            coordinated = False
        elif quantified and not (background or background_relative):
            quantifiers.append(word)
        elif modifier and not (background or background_relative):
            modifiers.append(word)
    else:
        flush()
    return tuple(scopes)
