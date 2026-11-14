# Actual pre-use source producer fixture

Tests deploy exact Git bytes for the pre-support-use source producer from commit `5002e8c3c40ca14a29f3ed8a08f6fcab2ec14b9c` and its last compatible operating-session dependency from commit `a6a2a8be54e628e68569caea245a48888744d607`. The manifest binds each Git blob, source SHA and compressed SHA. Both modules load from their physical fixture files. The test observes produced schema, groups and hashes unchanged.

This mixed-version test uses the two frozen modules and a legacy codec with today's remaining runtime. Current /4 producers still reject legacy codecs that lack support-use semantics. CI reads the vendored fixture without Git or network access.
