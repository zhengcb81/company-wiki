# W08 provenance control-character supplement

Independent review found a real URL data classification omission: `ord(char) < 32` covered C0 but not DEL/C1. The helper now uses the Unicode general category `Cc` plus existing whitespace handling. A URL containing such a raw character stays unknown (`None`); raw storage behavior and the existing writer nullable interface do not change. No new permission, URL HTTP check, schema, consumer or capture rewrite.

Targeted RED: DEL U+007F and C1 U+009F failed; C1 U+0085 was already rejected as whitespace, yielding2 FAIL/1 PASS in0.54s. Targeted GREEN: all3 PASS; Ruff0. No58-test/full/public CLI repeat. Original HANDOFF.md, RED.log, GREEN.log, GREEN_final_targeted.log and old static logs are untouched. No provider/model/network/production data/Git/install operation.

## Current frozen source/test SHA256

- `src/company_wiki/source_catalog/official_json_import.py`: `604d62cefd2ceb8b566dae08cac9e1ad86e8ea285e88da84ff845b4bf93cf027`
- `src/company_wiki/source_catalog/canonical_writer.py`: `26d9c475442f5438b19b8ad6a1c8578d0f14cfd13660b5955fd04c75a798e70f`
- `tests/integration/test_official_json_capture_provenance.py`: `3b1ff1c8dee0d4e48b1012d0fd468ff17191afa24d4119c740be437bcd71b6be`

## Additional original logs

- `RED_control_chars.log`: `cc27ee0fdcf4253e77004da8bc338d56f05bc11e49a06a4cf1a07a2f302f49bd`
- `GREEN_control_chars.log`: `1a2e7269ffd98dbbc75beb09704a67fdf0d69566cead53accd9c5fdc84548f2a`
- `ruff-control-chars.log`: `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`
