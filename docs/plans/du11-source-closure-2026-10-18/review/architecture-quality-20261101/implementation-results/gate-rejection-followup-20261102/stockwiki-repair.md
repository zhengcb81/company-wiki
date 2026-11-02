# StockWiki source transport and diagnostic separation

ROOT author scope frozen; awaiting one concentrated independent review. The JSON binds 13 exact source/test files. No production data/config/database or research state was written.

The source/raw and narrative transports now enforce actual configured output/time/process limits. Fixed 256KiB/16KiB/1.31MiB representation caps, groups512/views2 and reason80 limits no longer act as extra permission. An explicit receipt budget remains available; exceeding it stops actual reading. Default receipts scale with their source metadata.

Valid formatted JSON is not required to be byte-canonical after the exact original artifact SHA/size was checked. Benign diagnostic lines do not veto a complete receipt; genuinely different schema-matching receipts remain ambiguous. Duplicate keys, nonfinite data, identity/period/as-of/hash, references and support/context partitions retain their actual correctness controls.

Optional prompt-review unavailable/foreign/malformed notes become not_reviewed observations; missing optional trace and current source_processing_complete metadata do not refuse valid source material. The current assessed schema is consumed without discarding its uncertainty. No research acceptance is inferred.

TDD: refined first group 12F/1P ->13P; trusted local task >16KiB produced a separate real RED. Affected once 136P/1F/1skip in23.78s, with only the retired301s maximum oracle failing. Framing group4F/1P -> final targeted27P/1.65s, including explicit actual budget stops, duplicate/nonfinite receipts and invalid timeout controls. These are separate runs, not a fabricated one-shot total. Ruff8 relevant source/test files passed; final cosmetic/path-validation simplification will receive only focused checks.

All dynamic examples are synthetic/golden, with a real stub-child raw transport and a real local task CLI. They prove the technical gate failure and repair, not a new real-company summary or actual RF adoption. Test UUID directories are restored absent and RF four external WIP hashes unchanged, as each linked receipt records. No network/provider/model calls.
