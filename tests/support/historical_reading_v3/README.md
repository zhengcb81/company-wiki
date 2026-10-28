# Actual pre-use source producer fixture

Exact Git bytes from commit `5002e8c3c40ca14a29f3ed8a08f6fcab2ec14b9c`, `src/company_wiki/source_catalog/narrative_reading.py`, blob `8a06bfa7b92808db448fa8dee1eb2ba016cfc140`. The gzip is deterministic and preserves LF source bytes; the manifest binds both compressed and source SHA. Tests deploy it as an actual .py file before source reading loads; the current dependency inventory observes that physical file. No version/tag/group/hash in produced data is rewritten.

Only this source-producer component and the existing typed-v3 codec are historical; all other modules are today's runtime. This is not a full historic release, original company content, PDF fixture, or copied SDK. Current /4 producers must still refuse the legacy codec. Normal CI needs no Git objects or network.
