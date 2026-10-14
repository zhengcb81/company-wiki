"""Signal extraction from an observation.

The router must decide a family from *disclosure metadata plus cover/TOC/layered body
signals*, and ``design.md`` section 4 says the cover and section evidence outranks the
title while a conflict is reported rather than hidden. This module therefore produces an
explicit, inspectable bag of signals, each carrying the unit ids that produced it, so a
route can always cite its input.

Two design rules are enforced here:

* matching is on normalized text (case, width and whitespace folded), never on a company
  name or a security code;
* a signal is only raised from units that were actually probed, and the probe set is
  stratified across the document span, so a heading deep in a 400-page file still counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from typing import Final, Iterable, Sequence

from .observation import Observation, UnitRef

# --- text normalization ---------------------------------------------------------------

_WS = re.compile(r"[\s\u00a0\u3000]+")


def normalize(text: str) -> str:
    """Fold case, full-width forms and whitespace so aliases match reliably."""
    if not text:
        return ""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _WS.sub(" ", folded).strip()


def matches_any(normalized_text: str, aliases: Iterable[str]) -> str | None:
    """Return the first alias present in the text, or ``None``."""
    for alias in aliases:
        if normalize(alias) in normalized_text:
            return alias
    return None


def count_matches(normalized_text: str, aliases: Iterable[str]) -> int:
    return sum(1 for alias in aliases if normalize(alias) in normalized_text)


def is_speaker_turn(text: str) -> bool:
    """True when a unit opens with a real ``Speaker:`` turn, not a footnote label.

    ``SPEAKER_TURN`` alone is too permissive on real filings: statement-footnote labels
    such as ``Notes:`` and address lines match the same ``Word:`` shape. This gate drops
    the closed set of non-speaker labels in ``NON_SPEAKER_LABELS`` before a unit may count
    as a transcript turn.
    """
    if not SPEAKER_TURN.match(text or ""):
        return False
    label = normalize((text or "").split(":", 1)[0])
    return label not in NON_SPEAKER_LABELS


#: Cross-reference cues. A form or document name mentioned next to one of these is a
#: pointer to another document, not evidence about this one. ``design.md`` section 5
#: names this explicitly: "把目录/交叉引用当正文" is a must-avoid error.
_CROSS_REFERENCE_CUES = (
    "详见",
    "参见",
    "见本",
    "根据",
    "引用",
    "提到",
    "see ",
    "refer to",
    "referred to",
    "as described in",
    "for details",
    "disclosed in",
    "详见本公司",
    "详见公司",
)


def looks_like_cross_reference(text: str) -> bool:
    """True when a unit mentions another document rather than being one.

    The test is deliberately conservative and evidence-based: the unit must both name a
    document/form and contain an explicit pointing cue. Narrative prose that happens to
    contain ``年度报告`` is not enough on its own; it must also be *pointing* somewhere.
    """
    folded = normalize(text)
    if not folded:
        return False
    return any(normalize(cue) in folded for cue in _CROSS_REFERENCE_CUES)


def is_title_evidence(unit: UnitRef) -> bool:
    """True when a unit can serve as this document's *own* title/cover line.

    Only heading-like or short standalone lines qualify, and a line that points at
    another document never does. A long prose sentence that happens to embed a document
    name is prose *about* a document, not a self-identification.
    """
    if not (unit.text or "").strip():
        return False
    if looks_like_cross_reference(unit.text):
        return False
    if unit.kind in {"heading", "title"} or unit.heading_level is not None:
        return True
    if unit.text_clipped:
        return False
    # A bare short line (a cover/letterhead fragment) also counts, but only when it does
    # not read as a sentence -- prose that merely mentions a document name is excluded by
    # the punctuation and length test below.
    stripped = unit.text.strip()
    if len(stripped) > 80:
        return False
    return not re.search(r"[。；;]\s*$", stripped) and "，" not in stripped


def self_identification_units(units: Sequence[UnitRef]) -> list[UnitRef]:
    """Units that may act as this document's own title/cover evidence."""
    return [unit for unit in units if is_title_evidence(unit)]


#: A bracketed document title, e.g. ``《募集资金管理办法》``. In A-share filings this is how
#: one document *cites* another; it is a pointer, not a self-identification.
_BRACKETED_TITLE = re.compile(r"《[^》]{2,80}》")

#: Wording that makes a bracketed-title line *this* document's own purpose rather than a
#: citation of the quoted document. The real 鼎龙 confirmation letter is titled
#: ``关于《…招股说明书》的确认意见``: it quotes the prospectus but names itself a 确认意见. A bare
#: ``《募集资金管理办法》`` heading inside an IPO prospectus has no such trailing purpose word,
#: so it stays a pointer.
_SELF_PURPOSE_TAIL = (
    "确认意见",
    "确认函",
    "管理制度",
    "管理办法",
    "管理细则",
    "述职报告",
    "会议通知",
    "审核意见",
    "核查意见",
    "承诺函",
    "声明",
)


def _cites_another_document_title(text: str, *, allow_self_purpose: bool = False) -> bool:
    """True when a heading-like line is really a bracketed citation of another document.

    ``is_title_evidence`` accepts short heading lines, and a prospectus body legitimately
    carries a heading such as ``《…募集资金管理办法》`` for the policy it cites. That line is
    the *cited* document's title, not the prospectus naming itself, so it must not be read
    as this document's administrative purpose.

    ``allow_self_purpose`` separates the two channels the caller uses. For a supplied
    ``observation.title`` the line *is* how the document names itself, so a title that
    quotes another document but ends in its own purpose word (``关于《…招股说明书》的确认意见``,
    the real 鼎龙 confirmation letter) is self-identifying and not a citation. For a heading
    found *inside* the document a bracketed title is always a citation -- a body heading
    reading ``《募集资金管理办法》`` never becomes the containing prospectus's own purpose.
    """
    stripped = (text or "").strip()
    if not _BRACKETED_TITLE.search(stripped):
        return False
    if allow_self_purpose and any(tail in stripped for tail in _SELF_PURPOSE_TAIL):
        return False
    # The bracket must dominate the line for it to read as a citation: a bare
    # ``《募集资金管理办法》`` heading, or one with only list numbering around it.
    without = _BRACKETED_TITLE.sub("", stripped).strip(" ,，、:：-—0123456789.（）()")
    return len(without) <= 8


#: A-share section numbering: ``第一节`` .. ``第十节`` and the common suffix forms.
CN_SECTION_HEADING = re.compile(
    r"第\s*[一二三四五六七八九十百]+\s*节|第\s*[一二三四五六七八九十百]+\s*章"
)

#: A-share business narrative sections worth citing when they appear in the structure.
CN_BUSINESS_SECTION_ALIASES = (
    "管理层讨论与分析",
    "经营情况讨论与分析",
    "业务与技术",
    "主营业务",
    "公司业务",
    "行业情况",
    "未来发展",
    "风险因素",
)


def _cn_section_units(
    probes: Sequence[UnitRef], cover_ids: Sequence[str]
) -> list[UnitRef]:
    """Units carrying A-share section numbering or business-section vocabulary.

    A real annual report lists its sections either as one dot-leader TOC page or as
    separate ``第N节`` heading units; both must count as structure.

    A section name only counts when the unit *is* a heading-like line. A meeting minute
    that happens to discuss another company's ``第三节 管理层讨论与分析`` is prose about a
    report, not this document's structure -- the same cross-reference rule applied to
    titles. Units already counted as the cover are excluded for the same reason.
    """
    excluded = set(cover_ids)
    found: list[UnitRef] = []
    for unit in probes:
        if unit.unit_id in excluded:
            continue
        text = normalize(unit.text)
        if not text:
            continue
        numbered = bool(CN_SECTION_HEADING.search(text))
        named = bool(matches_any(text, CN_BUSINESS_SECTION_ALIASES))
        if not (numbered or named):
            continue
        if not _is_structural_line(unit):
            continue
        found.append(unit)
    return found


def _is_structural_line(unit: UnitRef) -> bool:
    """True when a unit reads as a heading/TOC line rather than a sentence of prose."""
    if unit.kind in {"heading", "title"} or unit.heading_level is not None:
        return True
    if unit.text_clipped:
        return False
    stripped = (unit.text or "").strip()
    if not stripped or len(stripped) > 60:
        return False
    # A prose sentence ends with sentence punctuation or contains an internal clause
    # separator; a section heading does neither.
    if re.search(r"[。；;！？!?]\s*$", stripped):
        return False
    return "，" not in stripped


def _hk_body_evidence(toc_text: str) -> bool:
    """True when the probed structure carries HK periodic-report vocabulary.

    Used to stop a wrong ``form_type`` from forcing an HK report into the SEC family:
    ``design.md`` section 4 puts cover/section evidence above file metadata.
    """
    return count_matches(toc_text, HK_STRUCTURAL_VOCAB) >= 1


#: Section vocabulary that identifies an HK periodic report. Kept beside the detector so
#: the structural scan and the metadata-override guard cannot drift apart.
HK_STRUCTURAL_VOCAB = (
    "業務回顧及展望",
    "管理層討論與分析",
    "財務表現摘要",
    "董事會報告",
    "企業管治報告",
    "獨立核數師報告",
    "年報",
    "年度報告",
    "中期報告",
    "全球發售",
    "行業概覽",
    "歷史及公司架構",
    "所得款項用途",
)


def _has_alternating_qa(
    probes: Sequence[UnitRef],
    question_units: Sequence[UnitRef],
    answer_units: Sequence[UnitRef],
) -> bool:
    """True when question and answer markers alternate in reading order.

    One question followed by one answer is already a Q&A exchange. Requiring at least one
    question->answer adjacency keeps a document that merely *quotes* a question, or that
    contains a stray ``答：`` in prose, from being classified as a record.
    """
    if not question_units or not answer_units:
        return False
    order = {unit.unit_id: position for position, unit in enumerate(probes)}
    question_positions = sorted(order[unit.unit_id] for unit in question_units)
    answer_positions = sorted(order[unit.unit_id] for unit in answer_units)
    for question_position in question_positions:
        if any(answer_position > question_position for answer_position in answer_positions):
            return True
    return False


# --- signal vocabulary ----------------------------------------------------------------

#: Cover/self-identification vocabulary, per regime. These are *form* words, not titles.
CN_PERIODIC_WORDS = ("年度报告", "半年度报告", "第一季度报告", "第三季度报告", "季度报告")
CN_ANNUAL_WORDS = ("年度报告",)
CN_INTERIM_WORDS = ("半年度报告", "中期报告")
CN_QUARTERLY_WORDS = ("季度报告",)
CN_OFFERING_WORDS = (
    "向特定对象发行a股股票",
    "向特定对象发行股票",
    "非公开发行股票",
    "发行a股股票",
    "募集说明书",
    "配股说明书",
)
CN_CONVERTIBLE_WORDS = ("可转换公司债券", "可转债")
CN_IPO_WORDS = (
    "首次公开发行股票",
    "招股说明书",
    "招股意向书",
    "科创板上市",
    "创业板上市",
    "主板上市",
)

CN_ADMIN_WORDS = (
    "确认意见",
    "述职报告",
    "管理制度",
    "管理办法",
    "会议通知",
    "关于召开",
    "承诺函",
)
CN_REVISION_WORDS = ("修订稿", "修订版", "更新稿", "更正", "补充公告", "注册稿", "上会稿")
CN_SUMMARY_WORDS = ("摘要",)

HK_OFFERING_WORDS = ("全球發售", "全球发售", "發售股份", "发售股份", "上市文件")
HK_PROSPECTUS_WORDS = ("招股章程", "招股说明书")
HK_ANNUAL_WORDS = ("annual report", "年報", "年报")
#: Traditional and Simplified forms are distinct codepoints, so both must be listed.
#: NFKC folding does *not* convert Traditional to Simplified; a Han-variant-aware
#: reading would be a new dependency and is deliberately avoided here.
HK_INTERIM_WORDS = (
    "interim report",
    "中期報告",
    "中期报告",
    "半年報",
    "半年报",
)
HK_RELEASE_WORDS = ("for immediate release", "announces", "announcement of", "業績公佈", "业绩公布")
HK_DECK_WORDS = ("results presentation", "presentation", "業績演示", "业绩演示", "investor presentation")

SEC_FORMS = {
    "10-k": ("form 10-k", "10-k"),
    "10-q": ("form 10-q", "10-q"),
    "20-f": ("form 20-f", "20-f"),
    "s-1": ("form s-1", "s-1"),
    "f-1": ("form f-1", "f-1"),
    "8-k": ("form 8-k", "8-k"),
    "6-k": ("form 6-k", "6-k"),
}
SEC_ANNUAL_FORM_WORDS = ("annual report pursuant to section 13", "for the fiscal year ended")
SEC_QUARTERLY_FORM_WORDS = ("quarterly report pursuant to section 13", "for the quarterly period ended")

SEC_10K_VOCAB = (
    "item 1. business",
    "item 1a. risk factors",
    "item 7. management's discussion and analysis",
    "item 8. financial statements",
)
SEC_10Q_VOCAB = (
    "item 2. management's discussion and analysis",
    "part i — financial information",
    "part i - financial information",
    "condensed consolidated financial statements",
)
SEC_20F_VOCAB = (
    "item 4. information on the company",
    "item 5. operating and financial review",
    "item 3. key information",
    "item 18. financial statements",
)

QA_QUESTION_MARKERS = ("问：", "问:", "q:", "question:", "提问：")
QA_ANSWER_MARKERS = ("答：", "答:", "a:", "answer:", "答复：", "回复：")
QA_SECTION_MARKERS = ("问答记录", "交流内容及具体问答记录", "questions and answers", "question-and-answer", "q&a")
IR_RECORD_MARKERS = ("投资者关系活动记录表", "投资者关系活动记录", "投资者网上集体接待日", "业绩说明会")
IR_POLICY_MARKERS = ("投资者关系管理制度", "投资者关系管理办法", "投资者关系管理细则", "investor relations policy")
TRANSCRIPT_MARKERS = (
    "call participants",
    "operator:",
    "prepared remarks",
    "earnings conference call",
    "earnings call",
    "conference call",
)
SPEAKER_TURN = re.compile(r"^\s*[A-Z][A-Za-z.\-']{1,40}(?:\s+[A-Z][A-Za-z.\-']{0,40}){0,3}\s*:")

#: ``Name:`` shapes that are *not* a speaker turn. A financial-statement footnote label
#: (``Notes:``, ``Note:``), an address line or a legend matches the speaker-turn pattern
#: but carries no speaker, so counting it as a turn misreads a real periodic report as an
#: earnings-call transcript.
#:
#: This is not hypothetical: on the plan's own 246-page HK annual report sample the label
#: ``Notes:``/``Note:`` appears 33 times as a statement-footnote lead-in, which fired the
#: transcript signal and routed a genuine annual report to ``earnings_call``. The gate is
#: intentionally a small closed set of unambiguous non-speaker labels -- it is a negative
#: label list, not a company-name or vocabulary special case.
NON_SPEAKER_LABELS: Final[frozenset[str]] = frozenset(
    {
        "note",
        "notes",
        "source",
        "sources",
        "basis",
        "legend",
        "key",
        "definition",
        "definitions",
        "abbreviation",
        "abbreviations",
        "disclaimer",
        "important",
        "attention",
        "remark",
        "remarks",
        "example",
        "examples",
        "total",
        "subtotal",
        "others",
        "miscellaneous",
        "email",
        "address",
        "tel",
        "telephone",
        "fax",
        "website",
        "www",
    }
)

SLIDE_MARKERS = ("results presentation", "presentation", "slide", "investor day", "業績演示")

ATTACHMENT_KINDS = ("attachment", "link", "external_link", "reference")
URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


@dataclass(frozen=True)
class Signal:
    """One piece of evidence with the units that produced it."""

    code: str
    unit_ids: tuple[str, ...]
    detail: str
    form_type: str | None = None


@dataclass
class SignalBag:
    """Collected signals plus the probe coverage that produced them."""

    signals: list[Signal] = field(default_factory=list)
    cover_signals: list[Signal] = field(default_factory=list)
    toc_signals: list[Signal] = field(default_factory=list)
    body_signals: list[Signal] = field(default_factory=list)
    probe_limit_hit: bool = False
    char_limit_hit: bool = False

    def add(self, bucket: list[Signal], code: str, unit_ids: Sequence[str], detail: str,
            *, form_type: str | None = None) -> None:
        """Record a signal. Title-only evidence is valid and cites no unit.

        A real document can be unreadable end to end (the ``cn-ipo-confirmation`` sample
        is a single opaque page with an empty native scan). Its title is still genuine
        input evidence, so a signal is allowed to carry an empty ``unit_ids`` list rather
        than being dropped -- dropping it would turn a decidable case into ``generic``.
        """
        bucket.append(
            Signal(code=code, unit_ids=tuple(dict.fromkeys(unit_ids)), detail=detail, form_type=form_type)
        )

    @property
    def all(self) -> list[Signal]:
        return [*self.cover_signals, *self.toc_signals, *self.body_signals, *self.signals]

    def codes(self) -> set[str]:
        return {signal.code for signal in self.all}

    def unit_ids_for(self, code: str) -> tuple[str, ...]:
        ids: list[str] = []
        for signal in self.all:
            if signal.code == code:
                ids.extend(signal.unit_ids)
        return tuple(dict.fromkeys(ids))


def _first_page(units: Sequence[UnitRef]) -> int | None:
    pages = [unit.page for unit in units if unit.page is not None]
    return min(pages) if pages else None


#: How many leading units count as "the cover" for a pageless carrier (HTML/TXT).
#: Deliberately small: a long body must never be mistaken for a cover, and a short
#: document must still expose body evidence outside the cover window.
COVER_WINDOW_UNITS = 3

#: How far into the document an administrative marker may sit and still count as the
#: document naming itself. Wider than the cover window because a real policy or
#: confirmation letter may carry a code/number line before its title.
BODY_SELF_ID_WINDOW = 6

#: A cover window may not consume the whole document. Below this many probed units the
#: third positional split carries no real evidence separation, so the router treats the
#: front of the document as cover *and* as body and relies on title/structural evidence
#: instead of a positional guess. This is what keeps a three-unit cross-reference from
#: being read as a cover page.
MIN_UNITS_FOR_POSITIONAL_COVER = 4


def _cover_units(observation: Observation) -> list[UnitRef]:
    """The cover: physical first page, or the front units for pageless carriers.

    Physical pagination is authoritative when present. Without it -- HTML and TXT
    carriers, and synthetic fixtures -- a positional cover is only meaningful if there is
    enough document left afterwards to be a body; otherwise the document is too short for
    the cover/body distinction to carry any weight, and the caller should decide on
    structure rather than position.
    """
    first_page = _first_page(observation.probes)
    if first_page is not None:
        on_first = [unit for unit in observation.probes if unit.page == first_page]
        if on_first:
            return on_first
    if len(observation.probes) < MIN_UNITS_FOR_POSITIONAL_COVER:
        return []
    return list(observation.probes[:COVER_WINDOW_UNITS])


def _toc_units(observation: Observation) -> list[UnitRef]:
    """Units that look like a table of contents or an index page."""
    return [unit for unit in observation.probes if _is_toc_unit(unit)]


def _is_toc_unit(unit: UnitRef) -> bool:
    text = normalize(unit.text)
    if text in {"目录", "contents", "目錄", "index", "table of contents"}:
        return True
    # Bilingual TOC headers pair the English and Traditional Chinese words in one line.
    if re.fullmatch(r"(?:contents|table of contents)\s*[·•\-—]?\s*(?:目錄|目录)", text):
        return True
    if re.fullmatch(r"(?:目錄|目录)\s*[·•\-—]?\s*(?:contents|table of contents)", text):
        return True
    if unit.kind == "toc":
        return True
    return ("...." in unit.text or "……" in unit.text) and len(unit.text) > 40


def detect_signals(observation: Observation) -> SignalBag:
    """Extract an inspectable signal bag from the probed units."""
    bag = SignalBag(
        probe_limit_hit=observation.probe_limited,
        char_limit_hit=observation.char_limited,
    )
    cover = _cover_units(observation)
    cover_ids = {unit.unit_id for unit in cover}
    toc = _toc_units(observation)
    toc_units = [unit for unit in toc if unit.unit_id not in cover_ids]
    toc_ids = {unit.unit_id for unit in toc_units}
    body = [unit for unit in observation.probes if unit.unit_id not in cover_ids | toc_ids]

    title_text = normalize(observation.title or "")
    cover_text = normalize(" ".join(unit.text for unit in cover))
    toc_text = normalize(" ".join(unit.text for unit in toc_units))
    body_text = normalize(" ".join(unit.text for unit in body))
    #: Units whose text may act as this document's own self-identification. A document
    #: name appearing only inside a cross-reference is excluded, so "see our Form 10-K"
    #: cannot make a newsletter look like a 10-K.
    self_id_units = self_identification_units(observation.probes)
    self_id_text = normalize(" ".join(unit.text for unit in self_id_units))

    _detect_carrier(bag, observation)
    _detect_administrative(
        bag, observation, title_text, cover_text, body_text, body, self_id_units
    )
    _detect_identity(bag, observation, title_text, cover_text)
    _detect_periodic(
        bag, observation, title_text, cover_text, toc_text, cover, toc_units, self_id_units
    )
    _detect_offering(
        bag,
        observation,
        title_text,
        cover_text,
        toc_text,
        cover,
        toc_units,
        body,
        self_id_units,
    )
    _detect_sec(
        bag, observation, title_text, cover_text, toc_text, cover, toc_units, body, self_id_text
    )
    _detect_hk(bag, observation, title_text, cover_text, cover, self_id_units)
    _detect_qa_and_call(bag, observation, title_text, cover_text, body_text, body)
    _detect_release_and_deck(bag, observation, title_text, cover_text, body_text, body)
    _detect_attachments(bag, observation)
    return bag


def _detect_carrier(bag: SignalBag, observation: Observation) -> None:
    mime = (observation.mime_type or "").casefold()
    units = tuple(unit.unit_id for unit in observation.probes[:3])
    if "html" in mime:
        bag.add(bag.signals, "HTML_CARRIER", units, f"mime={observation.mime_type}")
    elif "plain" in mime or mime.endswith("/txt"):
        bag.add(bag.signals, "TXT_CARRIER", units, f"mime={observation.mime_type}")


def _detect_administrative(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    body_text: str,
    body: Sequence[UnitRef],
    self_id_units: Sequence[UnitRef],
) -> None:
    """Administrative purpose is decided first, per the card.

    A confirmation letter can carry ``招股说明书`` in its title, so this must run before
    any prospectus logic and must be able to win on title evidence alone when the body is
    unreadable (the real ``cn-ipo-confirmation`` sample has an opaque single page).

    The marker must be part of how *this* document names itself, not a mention of some
    other document. This distinction is what the real sample set demands:

    * ``鼎龙`` confirmation letter -- the whole confirmation sentence is the title, so the
      marker is self-identification;
    * ``中微`` IPO prospectus -- the body cites ``《募集资金管理办法》`` as a pointer to a
      separate policy, so the same word must **not** make the prospectus administrative.

    The two channels are therefore treated differently, because they carry different
    evidence:

    * ``observation.title`` is supplied metadata. When the caller supplies a title whose own
      purpose word is administrative (``…的确认意见``), that is a self-identification the
      router may trust even with an unreadable body -- which is exactly the real
      ``cn-ipo-confirmation`` sample (one opaque page, zero native characters). The title is
      never a file path, so this does not violate the no-path-inference rule.
    * ``cover_text`` is assembled from *units inside this document*. A bracketed citation of
      another document's title must not stand in for this document's purpose, so cover
      evidence additionally requires a genuine, non-cited heading line.
    """
    matched: list[str] = []
    matched_ids: list[str] = []

    for word in CN_ADMIN_WORDS:
        folded = normalize(word)
        if not folded:
            continue
        if folded not in normalize(title_text):
            continue
        if _cites_another_document_title(title_text, allow_self_purpose=True):
            continue
        matched.append(word)
        matched_ids.extend(
            unit.unit_id
            for unit in observation.probes
            if folded in normalize(unit.text) and is_title_evidence(unit)
        )
    if matched:
        ids = tuple(dict.fromkeys(matched_ids)) or tuple(
            unit.unit_id for unit in observation.probes[:1]
        ) or tuple(unit.unit_id for unit in observation.units[:1])
        bag.add(
            bag.cover_signals,
            "ADMINISTRATIVE_PURPOSE",
            ids,
            "行政用途措辞: " + "、".join(sorted(set(matched))[:4]),
        )
        return

    for word in CN_ADMIN_WORDS:
        folded = normalize(word)
        if not folded:
            continue
        if folded not in normalize(cover_text):
            continue
        # The marker must sit on a line that can serve as *this* document's own name. A
        # bracketed title such as ``《募集资金管理办法》`` inside a 429-page IPO prospectus
        # is a citation of a separate policy, not the prospectus naming itself, so the same
        # word must not make the prospectus administrative. Only units that pass
        # ``is_title_evidence`` and are not a cited document title count.
        units_for_word = [
            unit
            for unit in observation.probes
            if folded in normalize(unit.text)
            and is_title_evidence(unit)
            and not _cites_another_document_title(unit.text)
        ]
        if not units_for_word:
            continue
        matched.append(word)
        matched_ids.extend(unit.unit_id for unit in units_for_word)
    if matched:
        ids = tuple(dict.fromkeys(matched_ids)) or tuple(
            unit.unit_id for unit in observation.probes[:1]
        ) or tuple(unit.unit_id for unit in observation.units[:1])
        bag.add(
            bag.cover_signals,
            "ADMINISTRATIVE_PURPOSE",
            ids,
            "行政用途措辞: " + "、".join(sorted(set(matched))[:4]),
        )
        return

    # Body-only evidence. A real administrative original states its own purpose as the
    # document's title line, so the marker must sit on the *earliest* heading-like line of
    # the document -- not on any heading anywhere. A 259-page annual report contains
    # headings like ``声明`` and ``募集资金管理办法`` deep inside; those describe the
    # report's contents, not the report's purpose.
    body_candidates = [
        unit
        for unit in self_id_units
        if (
            matches_any(normalize(unit.text), CN_ADMIN_WORDS)
            or matches_any(normalize(unit.text), IR_POLICY_MARKERS)
        )
        and not _cites_another_document_title(unit.text)
    ]
    if body_candidates and _is_leading_self_identification(observation, body_candidates):
        bag.add(
            bag.cover_signals,
            "ADMINISTRATIVE_PURPOSE",
            tuple(unit.unit_id for unit in body_candidates),
            "行政用途措辞: " + body_candidates[0].text.strip()[:40],
        )
        return

    # IR policy markers may also appear as a document's own title without the word 制度.
    for marker in IR_POLICY_MARKERS:
        folded = normalize(marker)
        if folded and folded in (title_text + " " + cover_text):
            ids = tuple(unit.unit_id for unit in body[:2]) or tuple(
                unit.unit_id for unit in observation.probes[:1]
            ) or tuple(unit.unit_id for unit in observation.units[:1])
            bag.add(
                bag.cover_signals,
                "ADMINISTRATIVE_PURPOSE",
                ids,
                f"制度类材料: {marker}",
            )
            return


def _is_leading_self_identification(
    observation: Observation, candidates: Sequence[UnitRef]
) -> bool:
    """True when an administrative marker appears at the document's own title position.

    "Leading" means within the first few probed units. A real confirmation letter, policy
    or director's report opens with its own name; a long filing that happens to contain a
    ``声明`` heading somewhere in its body does not become administrative.
    """
    leading_positions = {
        unit.unit_id for unit in observation.probes[:BODY_SELF_ID_WINDOW]
    }
    return any(unit.unit_id in leading_positions for unit in candidates)


def _detect_identity(
    bag: SignalBag, observation: Observation, title_text: str, cover_text: str
) -> None:
    """Report the metadata the router was handed, as citable evidence."""
    if observation.declared_kind and observation.declared_kind != "unknown":
        bag.add(
            bag.signals,
            "DECLARED_KIND_MATCH",
            tuple(unit.unit_id for unit in observation.probes[:1]),
            f"declared_kind={observation.declared_kind}",
        )
    if observation.title:
        bag.add(
            bag.signals,
            "FILENAME_MATCH",
            tuple(unit.unit_id for unit in observation.probes[:1]),
            "标题提供类型提示",
        )
    if observation.form_type:
        bag.add(
            bag.signals,
            "METADATA_MATCH",
            tuple(unit.unit_id for unit in observation.probes[:1]),
            f"form_type={observation.form_type}",
        )


def _detect_periodic(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    toc_text: str,
    cover: Sequence[UnitRef],
    toc_units: Sequence[UnitRef],
    self_id_units: Sequence[UnitRef],
) -> None:
    cover_ids = tuple(unit.unit_id for unit in cover)
    toc_ids = tuple(unit.unit_id for unit in toc_units)
    self_id_text = normalize(" ".join(unit.text for unit in self_id_units))
    self_id_ids = tuple(unit.unit_id for unit in self_id_units)
    # Self-identification is where a period word counts: a report saying "2025 年年度报告"
    # on its cover, or naming itself in a heading. A period word buried in prose about
    # another company's report is not this document's identity.
    haystack = title_text + " " + cover_text + " " + self_id_text

    if matches_any(haystack, CN_ANNUAL_WORDS):
        bag.add(
            bag.cover_signals,
            "COVER_HEADING",
            cover_ids or self_id_ids,
            "封面/标题含年度报告",
        )
    if matches_any(haystack, CN_INTERIM_WORDS):
        bag.add(
            bag.cover_signals,
            "COVER_HEADING",
            cover_ids or self_id_ids,
            "封面/标题含半年度报告",
        )
    if matches_any(haystack, CN_QUARTERLY_WORDS):
        bag.add(
            bag.cover_signals,
            "COVER_HEADING",
            cover_ids or self_id_ids,
            "封面/标题含季度报告",
        )

    if matches_any(toc_text, ("第一节", "第二节", "第三节", "第五节", "第十节")):
        bag.add(bag.toc_signals, "TOC_STRUCTURE", toc_ids, "A股第N节章节编号")
    else:
        # The section list often arrives as separate heading units (one per ``第N节``)
        # rather than one dot-leader page, so the structural scan spans all probed units.
        section_hits = _cn_section_units(observation.probes, cover_ids)
        if section_hits:
            bag.add(
                bag.toc_signals,
                "TOC_STRUCTURE",
                tuple(unit.unit_id for unit in section_hits),
                "A股第N节章节标题",
            )
        business_hits = [
            unit
            for unit in section_hits
            if matches_any(normalize(unit.text), CN_BUSINESS_SECTION_ALIASES)
        ]
        if business_hits:
            bag.add(
                bag.body_signals,
                "SECTION_VOCABULARY",
                tuple(unit.unit_id for unit in business_hits),
                "A股业务与管理层讨论章节",
            )


def _detect_offering(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    toc_text: str,
    cover: Sequence[UnitRef],
    toc_units: Sequence[UnitRef],
    body: Sequence[UnitRef],
    self_id_units: Sequence[UnitRef],
) -> None:
    cover_ids = tuple(unit.unit_id for unit in cover)
    toc_ids = tuple(unit.unit_id for unit in toc_units)
    # Keep the actual evidence channel and matching IDs. A historical body
    # heading cannot borrow an unrelated annual-report cover as its provenance.
    def add_named_signal(aliases: Sequence[str], detail: str) -> bool:
        cover_hits = [unit.unit_id for unit in cover
                      if is_title_evidence(unit) and matches_any(normalize(unit.text), aliases)]
        body_hits = [unit.unit_id for unit in (*self_id_units, *toc_units)
                     if unit.unit_id not in cover_ids and matches_any(normalize(unit.text), aliases)]
        if cover_hits:
            bag.add(bag.cover_signals, "COVER_HEADING", cover_hits, detail)
        elif matches_any(title_text, aliases):
            bag.add(bag.body_signals, "SECTION_VOCABULARY", body_hits, detail)
        elif body_hits:
            bag.add(bag.body_signals, "SECTION_VOCABULARY", body_hits, detail)
        return bool(cover_hits or body_hits or matches_any(title_text, aliases))

    for aliases, detail in ((CN_CONVERTIBLE_WORDS, "可转换公司债券募集材料"),
                            (CN_OFFERING_WORDS, "再融资募集说明书措辞"),
                            (CN_IPO_WORDS, "首次公开发行/招股措辞")):
        if add_named_signal(aliases, detail):
            break
    for aliases, detail in ((HK_OFFERING_WORDS, "港股全球发售措辞"),
                            (HK_PROSPECTUS_WORDS, "港股招股章程措辞")):
        if add_named_signal(aliases, detail):
            break

    fundraising = (
        "募集资金运用",
        "募集资金投资项目",
        "募集资金使用金额",
        "所得款项用途",
        "use of proceeds",
        "項目投資計劃",
        "项目投资计划",
        "项目建设周期",
        "募投项目",
    )
    hits = [unit for unit in (*toc_units, *body) if matches_any(normalize(unit.text), fundraising)]
    if hits:
        bag.add(
            bag.toc_signals if hits[0] in toc_units else bag.body_signals,
            "SECTION_VOCABULARY",
            tuple(unit.unit_id for unit in hits),
            "募投/所得款项章节",
        )

    if matches_any(toc_text, CN_IPO_WORDS) and matches_any(toc_text, ("业务与技术", "财务会计信息")):
        bag.add(bag.toc_signals, "TOC_STRUCTURE", toc_ids, "招股书目录结构")
    if matches_any(toc_text, ("行業概覽", "行业概览")) or matches_any(
        toc_text, ("歷史及公司架構", "历史及公司架构")
    ):
        bag.add(bag.toc_signals, "TOC_STRUCTURE", toc_ids, "港股招股书目录结构")


def _detect_sec(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    toc_text: str,
    cover: Sequence[UnitRef],
    toc_units: Sequence[UnitRef],
    body: Sequence[UnitRef],
    self_id_text: str,
) -> None:
    """SEC form vocabulary. Only a form *label* identifies the document.

    A bare ``10-K`` substring is not evidence: a 10-Q says "our annual report on Form
    10-K" as a matter of course. What identifies a filing is the form label on its own
    cover (``FORM 10-Q``) or an explicit period-report header. This is why the match is
    anchored on the ``form <name>`` pattern or on a self-identifying form line, and why
    body prose is not searched for form names at all.
    """
    cover_ids = tuple(unit.unit_id for unit in cover)
    toc_ids = tuple(unit.unit_id for unit in toc_units)
    body_ids = tuple(unit.unit_id for unit in body)
    self_id_units = self_identification_units(observation.probes)
    self_id_ids = tuple(unit.unit_id for unit in self_id_units)
    evidence_ids = cover_ids or self_id_ids

    # ``FORM 10-K`` printed on a cover is a label, not a reference: a filing cannot refer to
    # another filing *as its own cover label*. This is what makes a reconstructed
    # observation usable, where a whole SEC cover arrives as one large paragraph unit and
    # would fail a "short heading line" test.
    #
    # The exceptions are an explicit pointer ("See our Form 10-K ...") and running prose
    # that merely names a form while discussing something else ("...the risk factor section
    # of our Form 10-K", as said on a real earnings call). Both name another document even
    # though they carry the label. ``is_title_evidence`` already encodes exactly the
    # prose-versus-cover-line distinction, so a form label only counts when the unit could
    # serve as this document's own cover line -- unless the unit also carries real SEC item
    # structure, which is what a reconstructed one-paragraph cover looks like.
    labelled_units = [
        unit
        for unit in observation.probes
        if _has_sec_form_label(normalize(unit.text))
        and not _is_pointer_to_another_document(unit.text)
        and (is_title_evidence(unit) or _has_sec_structure_evidence(normalize(unit.text)))
    ]
    # Bare form names (``10-K`` without the ``form`` prefix) are only trusted from the
    # cover/short title lines, so the "our annual report on Form 10-K" sentence in a 10-Q
    # body cannot decide the form.
    own_lines = [unit for unit in (*cover, *self_id_units) if _is_structural_line(unit)]

    # The first printed own form identifies the containing filing. Registry
    # order must not let an attached 10-K replace an earlier outer 8-K.
    form = None
    chosen_label_ids: tuple[str, ...] = ()
    for unit in labelled_units:
        match = _SEC_FORM_LABEL.search(normalize(unit.text))
        if match:
            form = match.group(1)
            chosen_label_ids = (unit.unit_id,)
            break
    if form is None:
        for candidate, aliases in SEC_FORMS.items():
            if matches_any(title_text, aliases):
                form = candidate
                break
    if form is None:
        short_haystack = title_text + " " + " ".join(
            normalize(unit.text) for unit in own_lines
        )
        for candidate, aliases in SEC_FORMS.items():
            if matches_any(short_haystack, aliases):
                form = candidate
                break
    if form is None and observation.form_type and not _hk_body_evidence(toc_text):
        # Metadata may supply a form only when the body does not contradict it. An HK
        # bilingual report whose metadata claims 10-K is a metadata error, not a 10-K;
        # ``design.md`` section 4 puts cover/section evidence above the file metadata.
        declared = normalize(observation.form_type).removeprefix("form ").removesuffix("/a")
        for candidate in SEC_FORMS:
            if declared == candidate:
                form = candidate
                break

    labelled = bool(labelled_units)
    # Period-report header wording ("annual report pursuant to section 13") is trusted from
    # the cover and the document's own short title lines.
    haystack = title_text + " " + " ".join(normalize(unit.text) for unit in own_lines)
    # A 10-Q refers to its own 10-K, so a stray unlabelled form name in prose must never
    # decide the form. When the document reports an interim period and no printed label was
    # found, the interim-period path decides instead.
    if form in {"10-k", "10-q", "20-f"} and not labelled:
        if _looks_like_interim_period_report(
            toc_text + " " + " ".join(normalize(unit.text) for unit in body)
        ):
            form = None

    if form:
        label_ids = chosen_label_ids or evidence_ids
        bag.add(bag.cover_signals, "COVER_HEADING", label_ids, f"SEC 表单: {form.upper()}", form_type=form.upper())

    if matches_any(haystack, SEC_ANNUAL_FORM_WORDS) and form is None:
        bag.add(bag.cover_signals, "COVER_HEADING", evidence_ids, "年报式 SEC 封面语")
    if matches_any(haystack, SEC_QUARTERLY_FORM_WORDS) and form is None:
        bag.add(bag.cover_signals, "COVER_HEADING", evidence_ids, "季报式 SEC 封面语")

    # Item-number structure is body evidence rather than cover evidence; it is read from
    # the probed units (which include TOC pages when the document has one).
    combined = toc_text + " " + " ".join(normalize(unit.text) for unit in body)
    structure_ids = toc_ids or body_ids
    if count_matches(combined, SEC_10K_VOCAB) >= 2:
        bag.add(
            bag.toc_signals if toc_ids else bag.body_signals,
            "TOC_STRUCTURE",
            structure_ids,
            "10-K Item 编号",
        )
    if matches_any(combined, ("item 2. management's discussion and analysis",)) and matches_any(
        combined, ("part i", "condensed consolidated")
    ):
        bag.add(
            bag.toc_signals if toc_ids else bag.body_signals,
            "TOC_STRUCTURE",
            structure_ids,
            "10-Q Part I Item 2 结构",
        )
    if count_matches(combined, SEC_20F_VOCAB) >= 2:
        bag.add(
            bag.toc_signals if toc_ids else bag.body_signals,
            "TOC_STRUCTURE",
            structure_ids,
            "20-F Item 编号",
        )

    # A 10-Q may be probed only in part, so its item header never appears in the observed
    # window. The document still says what it is: it reports a *quarter*, refers back to
    # its own annual report, and carries interim-period vocabulary. Those are structural
    # facts, not keyword guesses, and they are checked only when no form label was found.
    # This scan reads every probed unit, because the period wording lives in narrative
    # text rather than in a heading.
    if form is None:
        every_unit_text = normalize(
            " ".join(
                [toc_text]
                + [normalize(unit.text) for unit in observation.probes]
            )
        )
        if _looks_like_interim_period_report(every_unit_text):
            bag.add(
                bag.body_signals,
                "SECTION_VOCABULARY",
                body_ids or evidence_ids,
                "SEC 中期期间报告措辞",
            )


#: A form *label*: the form name preceded by "form", as printed on a filing cover.
_SEC_FORM_LABEL = re.compile(r"\bform\s+(10-k|10-q|20-f|s-1|f-1|8-k|6-k)\b")

#: Wording that turns a form label into a pointer at someone else's filing.
_SEC_POINTER_CUES = (
    "see ",
    "refer to",
    "referred to",
    "described in",
    "disclosed in",
    "filed with the securities and exchange commission",
    "our annual report on form",
    "our quarterly report on form",
)


def _is_pointer_to_another_document(text: str) -> bool:
    """True when a form label is being cited rather than claimed as this document's own."""
    folded = normalize(text)
    return any(normalize(cue) in folded for cue in _SEC_POINTER_CUES)


def _has_sec_form_label(haystack: str) -> bool:
    """True when the text carries a printed form label such as ``FORM 10-Q``."""
    return bool(_SEC_FORM_LABEL.search(haystack))


def _has_sec_structure_evidence(combined: str) -> bool:
    """True when the observed text already carries explicit SEC item structure."""
    return bool(
        count_matches(combined, SEC_10K_VOCAB) >= 2
        or count_matches(combined, SEC_20F_VOCAB) >= 2
        or matches_any(combined, ("item 2. management's discussion and analysis",))
        or matches_any(combined, ("item 1. business", "item 4. information on the company"))
    )


#: Wording that identifies an interim SEC period report when the item header is outside
#: the observed window. Both a quarterly marker and a reference to the registrant's own
#: annual report must be present, so a 10-K excerpt cannot satisfy it.
_SEC_INTERIM_PERIOD_MARKERS = (
    "for the three months ended",
    "for the quarterly period ended",
    "three months ended",
)
_SEC_OWN_ANNUAL_REFERENCE = (
    "our annual report on form 10-k",
    "annual report on form 10-k",
    "in our annual report on form 10-k",
)


def _looks_like_interim_period_report(combined: str) -> bool:
    """True when the text reports a quarter and points back at its own annual report."""
    return bool(
        matches_any(combined, _SEC_INTERIM_PERIOD_MARKERS)
        and matches_any(combined, _SEC_OWN_ANNUAL_REFERENCE)
    )


def _detect_hk(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    cover: Sequence[UnitRef],
    self_id_units: Sequence[UnitRef],
) -> None:
    """HK periodic-report signals.

    Two things keep this from firing on a US filing:

    * the English ``annual report`` phrase alone is not HK evidence -- a 10-Q says "our
      annual report on Form 10-K" -- so a period word only counts together with HK
      vocabulary or a bilingual heading;
    * the structural scan requires HK section vocabulary (Traditional Chinese headings or
      ``全球發售``), which an SEC filing never carries.
    """
    cover_ids = tuple(unit.unit_id for unit in cover)
    self_id_text = normalize(" ".join(unit.text for unit in self_id_units))
    self_id_ids = tuple(unit.unit_id for unit in self_id_units)
    haystack = title_text + " " + cover_text + " " + self_id_text
    evidence_ids = cover_ids or self_id_ids

    hk_vocabulary_present = any(
        matches_any(normalize(unit.text), HK_STRUCTURAL_VOCAB)
        for unit in observation.probes
    )
    if hk_vocabulary_present and matches_any(haystack, HK_ANNUAL_WORDS):
        bag.add(bag.cover_signals, "COVER_HEADING", evidence_ids, "港股年报措辞")
    if hk_vocabulary_present and matches_any(haystack, HK_INTERIM_WORDS):
        bag.add(bag.cover_signals, "COVER_HEADING", evidence_ids, "港股中期报告措辞")

    # A HK bilingual report's section vocabulary may arrive as separate heading units
    # rather than as one dot-leader TOC page, so the structural scan covers every probed
    # unit. This is also what lets the body overrule a wrong ``form_type``.
    hits = [
        unit
        for unit in observation.probes
        if matches_any(normalize(unit.text), HK_STRUCTURAL_VOCAB)
        and unit.unit_id not in set(cover_ids)
    ]
    if hits:
        bag.add(
            bag.toc_signals,
            "TOC_STRUCTURE",
            tuple(unit.unit_id for unit in hits),
            "港股双语/定期报告章节",
        )


def _detect_qa_and_call(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    body_text: str,
    body: Sequence[UnitRef],
) -> None:
    """IR Q&A records and earnings-call transcripts.

    A question/answer pair is structural evidence: it is the alternating marker pattern
    that proves the document *is* a Q&A record, not a mention of one. The real record
    types keep the markers in one unit each (``1、问：`` ... ``答：`` ...), so the test
    counts units carrying a marker rather than units merely containing the word.
    """
    evidence_ids = tuple(unit.unit_id for unit in body[:2]) or tuple(
        unit.unit_id for unit in observation.probes[:1]
    )
    # A Q&A record alternates question and answer markers. In a paginated PDF the two
    # markers land in separate units, so adjacency within reading order is the real
    # structural evidence, not co-occurrence inside one unit.
    question_units = [
        unit for unit in observation.probes if matches_any(normalize(unit.text), QA_QUESTION_MARKERS)
    ]
    answer_units = [
        unit for unit in observation.probes if matches_any(normalize(unit.text), QA_ANSWER_MARKERS)
    ]
    qa_section_units = [
        unit
        for unit in observation.probes
        if matches_any(normalize(unit.text), QA_SECTION_MARKERS)
    ]
    ir_record = matches_any(title_text + " " + cover_text, IR_RECORD_MARKERS) or matches_any(
        body_text, IR_RECORD_MARKERS
    )
    alternating = _has_alternating_qa(observation.probes, question_units, answer_units)
    if alternating or (ir_record and (question_units or qa_section_units)):
        ids = tuple(
            dict.fromkeys(
                [unit.unit_id for unit in question_units]
                + [unit.unit_id for unit in answer_units]
                + [unit.unit_id for unit in qa_section_units]
            )
        )
        bag.add(
            bag.cover_signals if ir_record else bag.body_signals,
            "QA_STRUCTURE",
            ids or evidence_ids,
            "投资者关系问答记录",
        )

    transcript_hits = [
        unit for unit in observation.probes if matches_any(normalize(unit.text), TRANSCRIPT_MARKERS)
    ]
    speaker_units = [unit for unit in observation.probes if is_speaker_turn(unit.text or "")]
    if transcript_hits or (
        len(speaker_units) >= 2 and matches_any(body_text, ("earnings", "call", "quarter"))
    ):
        ids = tuple(
            dict.fromkeys(
                [unit.unit_id for unit in transcript_hits] + [unit.unit_id for unit in speaker_units]
            )
        )
        bag.add(bag.body_signals, "SPEAKER_TURNS", ids, "电话会/发言轮次结构")


def _detect_release_and_deck(
    bag: SignalBag,
    observation: Observation,
    title_text: str,
    cover_text: str,
    body_text: str,
    body: Sequence[UnitRef],
) -> None:
    """Results releases and slide decks: both carry periodic numbers without being filings.

    The scan covers every probed unit, not only the cover, because an HTML release puts
    ``Business Highlights`` in the body while a slide deck puts ``Results Presentation``
    on its first slide -- and either may be the only structural evidence available.
    """
    haystack = title_text + " " + cover_text
    all_text = normalize(" ".join(unit.text for unit in observation.probes))
    all_ids = tuple(unit.unit_id for unit in observation.probes)

    deck_hits = [
        unit
        for unit in observation.probes
        if matches_any(normalize(unit.text), HK_DECK_WORDS)
        or matches_any(normalize(unit.text), SLIDE_MARKERS)
    ]
    if matches_any(haystack, HK_DECK_WORDS) or deck_hits:
        deck_ids = tuple(unit.unit_id for unit in deck_hits) or all_ids[:3]
        bag.add(bag.cover_signals, "SLIDE_STRUCTURE", deck_ids, "演示稿封面")

    release_hits = [
        unit
        for unit in observation.probes
        if matches_any(normalize(unit.text), HK_RELEASE_WORDS)
        or matches_any(normalize(unit.text), ("business highlights", "financial highlights"))
    ]
    if matches_any(haystack, HK_RELEASE_WORDS) or release_hits:
        release_ids = tuple(unit.unit_id for unit in release_hits) or all_ids[:3]
        bag.add(bag.cover_signals, "COVER_HEADING", release_ids, "业绩发布措辞")

    highlight_hits = [
        unit
        for unit in observation.probes
        if matches_any(normalize(unit.text), ("business highlights", "financial highlights"))
    ]
    if highlight_hits:
        bag.add(
            bag.body_signals,
            "SECTION_VOCABULARY",
            tuple(unit.unit_id for unit in highlight_hits),
            "Business Highlights",
        )
    elif "business highlights" in all_text:
        bag.add(
            bag.body_signals,
            "SECTION_VOCABULARY",
            all_ids[:3],
            "Business Highlights",
        )


def _detect_attachments(bag: SignalBag, observation: Observation) -> None:
    """External links are marked unread; never fetched, never invented as a source."""
    link_units = [
        unit
        for unit in observation.probes
        if unit.kind in {"link", "external_link"} or URL_PATTERN.search(unit.text or "")
    ]
    if link_units:
        bag.add(
            bag.body_signals,
            "EXTERNAL_ATTACHMENT_NOT_READ",
            tuple(unit.unit_id for unit in link_units),
            f"{len(link_units)} 个外部链接/附件未读取",
        )


__all__ = [
    "Signal",
    "SignalBag",
    "count_matches",
    "detect_signals",
    "matches_any",
    "normalize",
]
