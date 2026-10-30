# CN source preparation independent review, initial

Scope: `local_reconcile.py` and author `test_cn_source_header_titles.py`, before final scope/freeze. Product files are read only. No final approval is issued.

## P2 — legal name beginning with the display abbreviation is skipped

Given matching same-page code 600999 and canonical display name 和光科技, both `和光科技股份有限公司投资者关系活动记录表` and `和光科技股份有限公司2026年半年度报告` remain unresolved. `_cn_cover_titles` strips the short name, leaving the legal suffix; its legal-name fallback runs only when that strip changed nothing. The legal-name candidate must be considered independently of whether the display-name candidate changed the heading. The author positive cases use disjoint short and legal names, so they miss this common form.

## P2 — unpunctuated reference sentences become source title proof

With the same matching code, `请查阅海川股份有限公司2026年年度报告` and `请查阅海川股份有限公司投资者关系活动记录表` both return a proved document kind, although the only line is a reference instruction. The arbitrary punctuation-free prefix in `_CN_CODE_BOUND_TITLE` consumes the reference predicate as part of a putative legal name. Title candidate purpose needs a boundary, independent of a company alias dictionary. The author colon-prose negative does not cover this form.

## Evidence and limits

Independent six-case synthetic-only PDF replay: 4 failed, 2 passed, pytest elapsed 1.72 s. Full failure evidence: `cn-initial.txt` and `cn-initial.xml`. Cases are retained in `test_cn_titles_neutral.py`. The conflicting security-code negative and a disjoint legal-name positive pass. No originals, credentials, SDK, network, external API, W21, holdouts, or production configuration were read or changed. Temporary PDF bytes existed only in memory. No product or author-test write occurred. Existing shared PWF and hook WIP were untouched.

Candidate work remains bounded by the preexisting page/text limits and the explicit 12 starts × 3 widths, rather than source length without a cap. This observation does not sign the later benchmark preparation hookup or US recovery change. Both issues were sent directly to ROOT for repair; final raw/LF sealing must use repaired final scope.
