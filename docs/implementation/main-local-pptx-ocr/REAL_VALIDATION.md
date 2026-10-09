# Fixed 22-page PPTX local validation

This is upstream extraction validation, not complete document recall or a public narrative-batch acceptance.

## Source and environment

Read the actual US-MSFT object reference from canonical `benchmarks/cross_market_rf/cases.json`, then the read-only RF archive bytes. Raw SHA `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`, size 4,016,522 bytes. The benchmark's legacy alias is `src_presentation`; its source_ref was null. MAIN's public `official_source_cli` registered these exact original bytes in an owned short TEMP catalog, returning actual SourceRef 2.0. `SourceVersionReader` reopened the registered bytes and confirmed SHA/size. Source metadata: MICROSOFT CORP / MSFT / US / investor_relations, real original URL, published_date=null and fiscal_year=null (no inferred publication date). This temporary registration is recorded in `real_import_receipt.json`, not a production ingest. It returned download_events=0; publisher projection was null even though the local request supplied Microsoft, retained as the actual receipt result.

Local explicit CPU configuration: RapidOCR 3.8.1 / ONNX Runtime 1.26.0, three pre-existing models with pinned SHA and package defaults SHA. Machine-specific resource paths are in `verified_local_config.json`; the pathless identity/fingerprint in the real report is `7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d`. The local package and installed models were not modified. This does not prove other installations have these dependencies/models.

## Results and bounds

- Pure 1.1.0: 22 display pages walked, zero native-text units, 22 opaque image pages. OOXML slide IDs 256..277 stay separate.
- OCR 2.0.0: 22 distinct media inferred once each, 1,067 lines, 81,100,800 decoded pixels, 145.549077 seconds (includes engine initialization and current CPU contention). No parser/image errors; low-confidence detected lines on pages 11, 20 and 21 (one each). This is detected-output quality, not missed-text recall.
- Eight selected spans on cover/body/numeric pages: one package verification, four media inferences, 16.570420 seconds; all selected text/box/config/media/quality metadata exactly replayed. This is selected-span evidence only.
- Bounds: source 8 MiB, uncompressed package 32 MiB, media 8 MiB, 22 pages/images, 4 million pixels/image, 90 million total pixels, 3,000 units, 200,000 emitted UTF-8 bytes, monotonic soft deadline plus 240-second parent subprocess hard deadline.
- Network/download blockers were active for sockets, requests, urllib and RapidOCR DownloadFile. Recorded 0 network attempts and 0 supplier POST. No remote vision/text model was called.
- Complete OCR was only in child memory. Only bounded selected spans/QA previews and per-page statistics were written. No full OCR MD, full page-image set or additional database persists.
- `coverage_complete=false` and all 22 image pages remain opaque/reviewable. Every page having detected lines does not establish complete body recall.

## Per-page statistics

| Display page | OOXML ID | Detected lines | Low-confidence lines | Status | OCR seconds |
|---|---|---|---|---|---|
| 1 | 256 | 4 | 0 | recognized | 3.800 |
| 2 | 257 | 6 | 0 | recognized | 3.920 |
| 3 | 258 | 8 | 0 | recognized | 3.632 |
| 4 | 259 | 12 | 0 | recognized | 9.201 |
| 5 | 260 | 15 | 0 | recognized | 10.655 |
| 6 | 261 | 1 | 0 | recognized | 1.411 |
| 7 | 262 | 22 | 0 | recognized | 14.758 |
| 8 | 263 | 8 | 0 | recognized | 5.537 |
| 9 | 264 | 51 | 0 | recognized | 6.936 |
| 10 | 265 | 1 | 0 | recognized | 1.240 |
| 11 | 266 | 15 | 1 | low_confidence | 7.880 |
| 12 | 267 | 34 | 0 | recognized | 6.197 |
| 13 | 268 | 23 | 0 | recognized | 14.834 |
| 14 | 269 | 1 | 0 | recognized | 1.486 |
| 15 | 270 | 170 | 0 | recognized | 6.374 |
| 16 | 271 | 225 | 0 | recognized | 7.026 |
| 17 | 272 | 250 | 0 | recognized | 9.456 |
| 18 | 273 | 85 | 0 | recognized | 7.293 |
| 19 | 274 | 1 | 0 | recognized | 1.450 |
| 20 | 275 | 60 | 1 | low_confidence | 10.996 |
| 21 | 276 | 73 | 1 | low_confidence | 9.705 |
| 22 | 277 | 2 | 0 | recognized | 1.609 |

## Visual checks: cover, dense body and numeric table

Original images were viewed at exact resolution. Pages 7 and 12 are information-dense body; page 18 supplies a numeric table. Pages 3 and 10 were candidate agenda/divider checks and are not counted as dense-body evidence. Only these individual images existed in owned TEMP, then were removed.

| Page | Original visible fact | Actual OCR / limitation |
|---|---|---|
| 1 | Cover title and September 2026 | Title/month preserved. Low-contrast footer ends Confidential; OCR reads Confidentia, missing final l despite confidence 0.98347. Earlier investigation's different preprocessing missed the whole footer. |
| 7 | Top paragraph starts with transition to two reporting segments | The whole first paragraph line at y≈180 is missing; ordered output jumps from title to the next line at y≈220. This is a meaningful body omission. Source remains partial. |
| 7 | Agents and Infra section label | OCR merges the space as “Agents andInfra”, confidence 0.95847. Later licensing/support operating lines are individually readable and replayable; they do not restore the absent line. |
| 12 | Two columns headed FY26 and FY27 | Both labels and metrics are detected; top-left bbox sorting outputs right FY27 before left FY26 because the right header is slightly higher. Ordering does not encode historical-to-current column relationships. |
| 18 | Subtitle explaining restated metrics | Subtitle at y≈173 is missing: output jumps from the title to As Restated. High-confidence detected entries do not capture all text. |
| 18 | As Restated Azure row, Q1/Q2/Q3/Q4/FY numerals | One bounded single-media follow-up selected six raw excerpts and exactly replayed them in two inferences total (initial + replay), 14.822453 seconds, 0 network attempts. Visible 40% / 39%, 39% / 38%, 40% / 39%, 42%, 40% all match these excerpts. Top-left sorting emits 42% first (y407), before Q1/Q2/Q3 (y408); no financial table cell is inferred. |
| 18 | Footnote contains LinkedIn and spaced non-GAAP CC terms | OCR confuses LinkedIn/Linkedln and merges spaces, still above 0.97 confidence. Numerical accuracy and semantic row/column linkage are not certified by confidence. |

The detected lines are useful upstream evidence when MAIN's bounded selector retains reliable business text and exact replay. Key omitted body lines, ambiguous relationships and low-confidence selections remain explicitly partial; no complete source or complete financial table claim is made.

## Restoration and reproducibility

`run_real_with_temp_import.py` invokes MAIN/src only for the public source import/read, then this worktree/src for OCR. It uses subprocess-specific environments and a TemporaryDirectory finally. Owned catalog root `cwocr-source-bz1xdap2` is absent after completion. Owned image root `cwocr-qjn2cp9j` contained only six QA images + marker; exact names/SHA were recorded before deletion, then its empty root was removed. `environment_restoration.json` confirms both absent, original SHA/size/mtime unchanged and all installed model SHA unchanged. No production config or installed copy was written.

Earlier attempts are recorded honestly: one rejected an installed RapidOCR enum API mismatch before successful output; another recognized the deck but rejected the legacy source alias when creating EvidenceSpan. Neither produced a successful check artifact. The valid canonical-source run above is the completed acceptance; no supplier cost occurred in any attempt.

Normal CI uses deterministic fake adapters and small in-memory packages. Reproduction is opt-in: use the two real runner scripts and explicitly supplied suite/object root/model config/real public-import receipt. Do not schedule this full deck for each small edit or commit.
