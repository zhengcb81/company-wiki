# FMP transcript producer golden

`fmp_v2.fetched.json` is copied byte-for-byte from the earnings-transcripts producer's
`tests/golden/fmp_v2.fetched.json` at commit `4924d57`.
It is a synthetic, producer-generated offline fixture, not a successful live paid API response.
No API key is present. The envelope retains unknown `publication_date` and
`as_of_cutoff_verified=false`; call date is not a publication date.

G-A0 uses this fixture only for original JSON byte SHA, untranslated content and
locator/lineage replay. Import-envelope compatibility and historical cutoff semantics
are separate remaining G-A work. Tests never write the original fixture.
