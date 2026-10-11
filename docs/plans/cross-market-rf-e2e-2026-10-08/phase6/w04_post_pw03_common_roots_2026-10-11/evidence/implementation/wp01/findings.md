# Findings

Existing projection loader opens through open_verified_projection -> build_projection_export -> _verify_projection_from_parents once. Existing /2 ref and read receipt contain full subjects and duplicated parent refs, exceeding 16 KiB at 65 parents. source_reader.prepare_source_result currently always requires a period for capture_ready.

OWNER_MATRIX.json is under work_packages. Overlay pins tests/unit and extends ownership to narrative_evidence_view.py. Isolated CodeGraph is already confirmed not initialized; known source files read directly per ROOT instruction.

/3 exact schemas were added, with no replacement of /1 or /2 constants/fields. Subject resolver reuses open_verified_projection once and passes its detached VerifiedProjectionView to replay. The /3 receipt includes canonical full-subject lineage hash and parent count; no raw SourceRef is invented.

Meaningful RED: investor_relations and broker_research capture_ready False despite complete no-FY provenance; compact resolver absent. Final owner tests include 65 true imported source parents, 257 synthetic records, 24 synthetic issuers (test only), strict DTO and native issuer/asof/generation/parent/pointer refusal. 18 tests pass; 110 old compatibility tests pass.

Real PW03 data differs from test shape: latest has 65 parents/195 records; questions has 11/33 and precollect 10/29, 257 total records. Across projection records, provider_company_id non-null union is 21; issuer_observed dict union is 36, including empty/alias/stock variants. Do not relabel either as 24 issuers. Raw projection fixture and bundle preserve existing SHA/generation. Real bundle 59247B, source opens/read exactly 65. Six actual protocol wires 424/579/667/725/931/981B. Real Microsoft deck c02f4e...dcd4 and Synergy208fdd...9554 now capture_ready true without fabricated FY, exact original byte read succeeds, wrong FY query still has no match.

Public fixture remains owned TEMP w4p1-k4f7_7dv for WP03/ROOT integration, contains only selected 65 CN and 2 US originals plus existing copied metadata/1 projection/1 pin bundle. Public samples persisted under WP01 evidence. Zero provider/HTTP/model calls and actual cost USD0. Final cross-repo G1, RF consumer integration and independent contract review belong to ROOT/WP03 and are not declared complete here.
