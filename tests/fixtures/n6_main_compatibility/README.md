# Frozen selector 0.3.2 finals

These three fixtures were generated once on code `ca6d9ced5981f4f84a247ef5b90095d651ccb805`, with selector 0.3.2 and parser 0.1.0. Actual select/summarize/verify jobs and outbox publication produced the stored canonical `narrative-bundle/2.0` bytes. Sources are synthetic English TXT, provider-shaped JSON and a one-page synthetic PDF. The model was deterministic and local, with no external request or fee.

Each JSON contains original bytes, complete historical bundle bytes, their SHA-256 values, source identity metadata and provenance. This is a historical compatibility oracle, not an investment or vendor-quality oracle. Do not regenerate it using a new selector to make a failing test pass. Generation-time read-policy hashes are lineage; the integration test also verifies the current catalog and original bytes.

The integration test registers these unchanged historical bundles in an independent scratch catalog. It disables the current selector, simulates a later version/group publication, verifies exact old references and confirms changed original bytes still fail. Temporary source copies, artifacts and SQLite files are removed in `finally`.
