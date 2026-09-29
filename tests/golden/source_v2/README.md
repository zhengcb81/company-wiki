# Company-wiki SourceRef / SourceExport v2 producer golden

Generated from the current `source_export_v2_cli` serializer using the
synthetic, self-contained UTF-8 fixture in
`tests/contract/test_source_export_v2_cli.py::_fixture`. The test invokes the
real CLI from another working directory with network and subprocess calls
forbidden, and compares its exact stdout bytes to `source_export_bundle.json`.
All six JSON files are one sorted, compact UTF-8 object plus `\n`.

| File | SHA-256 | Meaning |
| --- | --- | --- |
| `source_ref.json` | `aca22689b9369151932d8402614c48d0122a8049fee3015b420264bcfd335cf1` | Pathless exact source version; original is 62 UTF-8 bytes with SHA `d9b0df81476e5c29dedd8acc8438f0dcfd8f45585a4f246e1cbc243ed4dd4de3`. |
| `evidence_span.json` | `752da2820441e35e41045911ea4ef90f50f8e50121b634f3c2f2622dec9b828f` | Original-text character locator `loc:v1/chars:4-22`. |
| `source_export_bundle.json` | `50127fc93f77e38f391917e5b152037c5375e385eedd0284419555348e16d793` | Real CLI stdout, schema `2.0.0`, export ID/bundle SHA bound to manifest and span. |
| `source_ref_bad_sha.json` | `45f2f3a6dfaec665ebb6ac85eb2127093092a367031952f5c7e83bc477d714d1` | Mutated ref; producer CLI returns exit 2, empty stdout, structured refusal. |
| `verified_open_receipt_normalized.json` | `b27dccb3d8f4adf101d8f66b8feb1dcc98b987ec7993fbcc9c995f865f3d5869` | Actual `source_reader_cli` success receipt schema `2.1`; the test first checks both policy pins are 64-hex and `read_at` is UTC, then replaces only those runtime values with markers. Stdout is the exact 62 original bytes, not stored again here. |
| `verified_open_bad_sha.json` | `daed1b192dab90daf50bc2c9a3dc92695009944f51457177374cc77e0d53a0b5` | Actual `source_reader_cli` exit 2, empty stdout, `expected_version_mismatch` error receipt. |

Reproduce: `python -m pytest -q tests/contract/test_source_export_v2_cli.py`.
The test creates only isolated synthetic files and removes its temporary root.
The golden does not claim a real company filing or historical availability.
PDF sources can currently produce verified manifests, while PDF page/paragraph
spans await the immutable normalized-artifact registry in E5. A consumer must
verify actual source bytes through `source_reader_cli`, rather than treat this
JSON bundle as a byte-open receipt.
