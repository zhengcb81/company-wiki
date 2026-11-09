"""Source statement syntax, independent of company or operating vocabularies.

This observer recognizes a readable clause, never its economic truth, issuer,
event, stage or measurement. It uses packaged linguistic resources offline.
Missing resources remain unknown; they cannot turn a fragment into support.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from hashlib import sha256
from importlib import metadata
import json
from pathlib import Path
import re
from typing import Any, TYPE_CHECKING

from company_wiki.document_understanding.operating_states.patterns import COMPOUND_HEAD
from .predicate_arguments import PredicateArgumentScope, predicate_argument_scopes

if TYPE_CHECKING:
    from company_wiki.resource_budget import WorkBudget


STATEMENT_GRAMMAR_VERSION = 'statement-grammar/4'
MAX_STATEMENT_CHARS = 4096
MAX_STATEMENT_TOKENS = 1024
STATEMENT_GRAMMAR_WORK_PER_CHAR = 32
_RESOURCES = Path(__file__).with_name('resources')
_ASSETS = ('averaged_perceptron_tagger_eng.weights.json',
           'averaged_perceptron_tagger_eng.tagdict.json',
           'averaged_perceptron_tagger_eng.classes.json', 'jieba.dict.txt')
_PACKAGES = ('nltk', 'jieba')
_EN_TOKEN = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|\d+(?:\.\d+)?|[^\w\s]", re.UNICODE)
_NOMINAL_HEAD = re.compile(r'(?:' + COMPOUND_HEAD + r'|业务|業務|活动|活動|项目|項目|计划|計劃|规划|規劃|报告|報告)')
_CN = re.compile(r'[\u3400-\u9fff]')
# Closed grammatical function words locate interrogative inversion; a wh word
# alone also introduces temporal/location subordination and is not a question.
_EN_AUXILIARY = r'(?:am|is|are|was|were|do|does|did|has|have|had|can|could|will|would|shall|should|may|might|must)'
_EN_INTERROGATIVE = re.compile(r'\s*(?:' + _EN_AUXILIARY + r'\b|'
    r'(?:what|when|where|why|how|who|whom|which|whose)\b'
    r'(?:\s+(?:many|much|long|often|soon|far))?\s+' + _EN_AUXILIARY + r'\b)', re.I)
_EN_WH_START = re.compile(r'\s*(?:what|when|where|why|how|who|whom|which|whose|whether)\b', re.I)
_ENUMERATOR = re.compile(r'^\s*(?:\([ivxlcdm]+\)|（[ivxlcdm]+）)\s*', re.I)
_EN_MEMBERSHIP = re.compile(r'(?:includ(?:e|es|ed|ing)|compris(?:e|es|ed|ing)|'
                            r'cover(?:s|ed|ing)?|consist(?:s|ed|ing)?)$', re.I)


@dataclass(frozen=True)
class StatementObservation:
    status: str
    reason: str
    argument_nominals: tuple[str, ...] = ()
    weak_relation: bool = False
    argument_scopes: tuple[PredicateArgumentScope, ...] = ()

    @property
    def independent(self) -> bool:
        return self.status == 'independent'


class _GrammarScopeExceeded(RuntimeError):
    pass


class _GrammarAmbiguous(RuntimeError):
    pass


def english_question_start(text: str) -> bool:
    """Observe explicit auxiliary inversion, without deciding factual meaning.

    Question punctuation and explicit dialogue roles remain caller-owned.
    Complex wh noun phrases are not classified from a word alone; the matrix
    observer separately withholds a leading subordinate phrase without a main
    clause. This cheap boundary does not load a linguistic model.
    """
    return _EN_INTERROGATIVE.match(text) is not None


def observe_english_statement_boundary(text: str, *,
        work_budget: WorkBudget | None = None,
        prepared: StatementObservation | None = None) -> StatementObservation | None:
    """Distinguish interrogatives/subordinates before a typed proof is reused.

    Auxiliary inversion is explicit. A wh prefix alone cannot decide between
    a question, a subordinate fragment, and a complete conditional statement.
    Those scopes use the same charged matrix observer as readable narration;
    resource/scope failure stays unknown, not a question or free support.
    """
    if english_question_start(text):
        return StatementObservation('fragment', 'interrogative_scope')
    if _EN_WH_START.match(text):
        return prepared if prepared is not None else observe_statement(text, work_budget=work_budget)
    return None


def resource_identity() -> str:
    """Actual data/package identity for the reading recipe, not an approval pin."""
    assets = {}
    for name in _ASSETS:
        try:
            assets[name] = sha256((_RESOURCES / name).read_bytes()).hexdigest()
        except OSError:
            assets[name] = 'unavailable'
    packages = {}
    for name in _PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = 'unavailable'
    payload = {'schema': STATEMENT_GRAMMAR_VERSION, 'assets': assets, 'packages': packages}
    return sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _verified_assets() -> None:
    manifest = json.loads((_RESOURCES / 'manifest.json').read_text(encoding='utf-8'))
    for name in _ASSETS:
        raw = (_RESOURCES / name).read_bytes()
        if sha256(raw).hexdigest() != manifest['assets'][name]['sha256']:
            raise ValueError('statement grammar resource differs from its packaged manifest')


@lru_cache(maxsize=1)
def _english_tagger() -> Any:
    _verified_assets()
    from nltk.tag.perceptron import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    tagger.load_from_json(lang='eng', loc=_RESOURCES)
    return tagger


@lru_cache(maxsize=1)
def _chinese_tagger() -> Any:
    _verified_assets()
    import jieba

    tokenizer = jieba.Tokenizer(dictionary=str(_RESOURCES / 'jieba.dict.txt'))
    # initialize() persists a machine-local dictionary cache. Build precisely
    # the same frequency dictionary in memory so reading never writes a cache.
    tokenizer.FREQ, tokenizer.total = tokenizer.gen_pfdict(tokenizer.get_dict_file())
    tokenizer.initialized = True
    with (_RESOURCES / 'jieba.dict.txt').open(encoding='utf-8') as stream:
        tags = {word: tag for line in stream if line.strip()
                for word, _frequency, tag in [line.rstrip().rsplit(' ', 2)]}
    # jieba.posseg imports global POS dictionaries and unused HMM weights.
    # HMM=False needs only these dictionary labels plus the public tokenizer;
    # keep this single packaged model instance instead of loading a second one.
    return tokenizer, tags


def _english_statement(text: str) -> tuple[bool, tuple[PredicateArgumentScope, ...], bool]:
    words = _EN_TOKEN.findall(text)
    if len(words) > MAX_STATEMENT_TOKENS:
        raise _GrammarScopeExceeded
    tagged = _english_tagger().tag(words)
    leading_wh = _EN_WH_START.match(text) is not None
    # Unknown proper names must not determine grammatical class of the next
    # word. Re-observe a leading proper-NP under a neutral noun phrase; this
    # transient view never replaces source text or assigns company identity.
    proper_end = 0
    while not leading_wh and proper_end < len(tagged) and tagged[proper_end][1] in {'NNP', 'NNPS'}:
        proper_end += 1
    if proper_end:
        tagged = _english_tagger().tag(['The', 'entity', *words[proper_end:]])
    # A prepositional reporting period has no matrix subject; a later comma
    # may introduce an independent statement. Likewise, all-title-case labels
    # cannot borrow a past-participle-looking legal/name suffix as a verb.
    intro = leading_wh or bool(tagged and tagged[0][1] in {'IN', 'TO', 'WRB', 'WDT', 'WP', 'WP$'})
    nominal = False
    for index, (word, tag) in enumerate(tagged):
        if word in {',', ';'}:
            intro = False
            nominal = False
            continue
        if intro:
            continue
        if tag in {'NN', 'NNS', 'NNP', 'NNPS', 'PRP'}:
            nominal = True
        elif tag in {'VBD', 'VBP', 'VBZ', 'MD', 'VB'} and nominal:
            if word[:1].isupper():
                continue
            # A relative phrase does not supply the matrix predicate.
            if any(previous in {'WDT', 'WP', 'WP$'} for _, previous in tagged[:index]):
                continue
            scopes = predicate_argument_scopes(tagged, index, language='en')
            membership = bool(scopes) and all(_EN_MEMBERSHIP.fullmatch(scope.predicate)
                                               for scope in scopes)
            # cover X with Y is a transitive application, not an enumeration.
            # Its unknown objects remain untouched; no crop/industry words
            # determine this grammatical distinction.
            if any(scope.predicate.casefold().startswith('cover') for scope in scopes):
                application = any(token.casefold() == 'with' and flag == 'IN'
                                  for token, flag in tagged[index + 1:])
                membership &= not application
                if application:
                    scopes = tuple(replace(scope, attachment='application')
                                   if scope.predicate.casefold().startswith('cover') else scope for scope in scopes)
            return True, scopes, membership
    return False, (), False


def _chinese_statement(text: str, *, lexical_boundaries: tuple[int, ...] = ()) -> tuple[
        bool, tuple[PredicateArgumentScope, ...], bool]:
    enumeration = _ENUMERATOR.match(text)
    removed = enumeration.end() if enumeration else 0
    text = text[removed:]
    boundaries = [0, *(point - removed for point in lexical_boundaries if removed < point < len(text) + removed), len(text)]
    tokenizer, tags = _chinese_tagger()
    tagged = []
    for left, right in zip(boundaries, boundaries[1:]):
        for word in tokenizer.cut(text[left:right], HMM=False):
            if word.strip():
                tag = tags.get(word, 'eng' if word.isascii() and word.isalpha()
                               else 'm' if word.isnumeric() else 'x')
                tagged.append((word, tag))
            if len(tagged) > MAX_STATEMENT_TOKENS:
                raise _GrammarScopeExceeded
    nominal = False
    aspect = False
    ambiguous = False
    ambiguous_nominals: tuple[str, ...] = ()
    nominalized_tail = False
    for index, (word, tag) in enumerate(tagged):
        if tag in {'uj', 'c'} or word in {'与', '與', '及', '和'}:
            nominal = False
            aspect = False
            continue
        if tag == 'x' and word in '，,；;。.!?！？':
            nominal = False
            aspect = False
            nominalized_tail = False
            continue
        if tag.startswith('n') or tag in {'r', 's', 'f', 'eng'}:
            nominal = True
            continue
        if tag == 'vd' and nominal:
            aspect = True
            continue
        if not nominal or not (tag in {'v', 'vn'} or tag == 'a' and aspect):
            continue
        tail = []
        for token, flag in tagged[index + 1:]:
            if flag == 'x' and token in '，,；;。.!?！？':
                break
            tail.append((token, flag))
        # 的 can nominalize a VP, or belong to an adjective/locative modifier
        # inside the verb's object NP. Do not let that local object modifier
        # consume a complete matrix predicate across its own scope.
        nominalizers = [offset for offset, (_, flag) in enumerate(tail)
                        if flag == 'uj' and (offset == 0 or tail[offset - 1][1] not in {'a', 'ad', 'an', 'f', 's'})]
        # A matrix copula/possession verb takes a nominal complement, whose
        # internal 的 does not nominalize that already observed matrix. An
        # immediate V+的 still lacks a matrix object (公司拥有的码头).
        nominal_complement = ((word in {'是', '有'} or word.endswith('于')) and nominalizers
                              and all(offset > 0 for offset in nominalizers)
                              and any(flag.startswith('n') or flag in {'v', 'vn'}
                                      for _, flag in tail[nominalizers[-1] + 1:]))
        if nominalizers and not nominal_complement:
            # An immediate V+的 is a clear relative nominal. With an intervening
            # noun the fixed POS dictionary cannot always distinguish a VP's
            # relative boundary from an object-internal possessive/modifier.
            # Do not guess that lexical ambiguity into either support or a
            # supposedly proven fragment; a later matrix clause can resolve it.
            ambiguous |= 0 not in nominalizers
            if 0 not in nominalizers:
                ambiguous_nominals = tuple(token for token, flag in tail if flag.startswith('n'))
            nominalized_tail = True
            continue
        if nominalized_tail and not nominal_complement:
            continue
        rest = ''.join(token for token, _ in tail).lstrip()
        if tail and (tail[0][1] == 'c' or tail[0][0] in {'与', '與', '及', '和'}):
            continue
        if tag == 'vn' and not rest:
            first_preposition = next((offset for offset, (_, flag) in enumerate(tagged[:index])
                                      if flag == 'p'), None)
            if (first_preposition is None or not any(flag.startswith('n') or flag in {'r', 'eng'}
                    for _, flag in tagged[:first_preposition])):
                continue
        if _NOMINAL_HEAD.match(rest):
            continue
        scopes = predicate_argument_scopes(tagged, index, language='zh')
        return True, scopes, word in {'包括', '包含', '涵盖', '覆盖'}
    if ambiguous:
        raise _GrammarAmbiguous(ambiguous_nominals)
    return False, (), False


def observe_statement(text: str, *, work_budget: WorkBudget | None = None,
                      lexical_boundaries: tuple[int, ...] = ()) -> StatementObservation:
    """Observe one bounded clause using general POS, with no runtime downloads.

    Prepared grammatical operators may supply ordered lexical cut positions.
    These are transient tokenizer boundaries, never source offsets/locators
    or POS overrides. Disjoint pieces retain one linear input/work envelope.
    """
    if not text.strip():
        return StatementObservation('fragment', 'empty_clause')
    if len(text) > MAX_STATEMENT_CHARS:
        return StatementObservation('unknown', 'statement_grammar_scope_limit')
    previous = 0
    if len(lexical_boundaries) > min(MAX_STATEMENT_TOKENS, len(text)):
        return StatementObservation('unknown', 'statement_grammar_scope_limit')
    for point in lexical_boundaries:
        if type(point) is not int or not previous <= point <= len(text):
            return StatementObservation('unknown', 'statement_grammar_scope_limit')
        previous = point
    if ':' in text or '：' in text:
        return StatementObservation('fragment', 'enumeration_scope')
    if text.rstrip().endswith(('?', '？')) or english_question_start(text):
        return StatementObservation('fragment', 'interrogative_scope')
    # This is a conservative logical work coefficient, not a claim of CPU
    # instruction equivalence. It is charged only when fallback is requested;
    # cold immutable model loading remains bounded by the worker deadline.
    if work_budget is not None:
        work_budget.charge(STATEMENT_GRAMMAR_WORK_PER_CHAR * len(text) + 1)
    try:
        independent, scopes, weak = (_chinese_statement(text, lexical_boundaries=lexical_boundaries)
                                     if _CN.search(text) else _english_statement(text))
    except _GrammarScopeExceeded:
        return StatementObservation('unknown', 'statement_grammar_scope_limit')
    except _GrammarAmbiguous as exc:
        return StatementObservation('unknown', 'statement_grammar_ambiguous',
                                    exc.args[0] if exc.args else ())
    except (ImportError, OSError, LookupError, ValueError, KeyError, TypeError):
        return StatementObservation('unknown', 'statement_grammar_unavailable')
    return StatementObservation('independent' if independent else 'fragment',
                                'subject_predicate' if independent else 'no_matrix_predicate',
                                tuple(word for scope in scopes for word in scope.argument_nominals), weak, scopes)

__all__ = [
    'StatementObservation',
    'observe_english_statement_boundary',
    'observe_statement',
    'resource_identity',
]
