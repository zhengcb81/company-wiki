# Findings

The current PPTX parser uses OOXML slide_id (256..277 in the real deck) as page_number; HTML identity is 1.0.0 and must remain unchanged. Current unit identity hardcodes one parser version, NormalizedDocument also requires that version. OCR must use a distinct version and retain 1.0.0 read-only replay.

RapidOCR 3.8.1 and ONNX Runtime 1.26.0 plus local det/cls/rec ONNX bytes are present. Explicit local paths and SHA verification are required to avoid its automatic download path. The earlier offline cover trial read three major lines, missed low-contrast footer: confidence is not recall. Actual OCR body/full deck quality remains unverified.

The pure parser is no-model; the optional composition will be explicit and receive an adapter/config. No production configuration or shared caller changes belong here.

## Actual implementation and real-check findings

- Current pure PPTX identity is 1.1.0/shape locator2; explicit 1.0.0 retains old OOXML IDs, including under a current global OCR adapter (zero inference). HTML source file and identity remain unchanged.
- OCR composition 2.0.0 binds actual source/media/shape/page/config/box/text, and selected-span replay parses original package once and infers only selected media. 10 spans/2 media proof passes with third media unselected.
- Actual local config fingerprint 7834f117defffd44dc4719eda68151371b5f5cb68f2c51f2b968c02290126b1d; from_dict/identity are I/O-free. Optional validate_environment explicitly verifies local hashes/runtime/defaults/dictionary/CPU engine, zero OCR inference.
- Full real check: 1067 lines, 145.549077s, 22 unique media; selected 8 spans/4 media replay16.570420s. Per-page low-conf11/20/21, coveragefalse. Meaningful missing first body line page7 and missing subtitle page18; high-confidence footer/spacing errors. Confidence cannot indicate recall.
- Page18 bounded numeric check: 6 selected raw excerpts exactly match visible Azure-row digits, but output starts Q4 due y sorting; no financial-cell semantics. Initial + replay2 calls,14.822453s,0network.
- Public official import in owned TEMP yielded true SourceRef2.0 and exact reopened bytes, published_date=None. All TEMP removed, original and installed models unchanged.
