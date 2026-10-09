# Actual page7 bounded sample failure

See immutable page7_real_receipt.json and subsequent page7_sample_closure.json. Actual outer duration 21.959662700013723 seconds; child terminal exit1, no timeout. Protected snapshots are identical.

The actual traceback occurs while evaluating `selected.omitted_count` for the receipt. The executed code had already passed:

```python
assert language == "en" and spans and selected.status == "partial" and not selected.coverage_complete
assert all(s.parse_status == "parsed" and s.structured_value["media_sha256"] == MEDIA
           and not {"low_ocr_confidence", "locator_unstable"}.intersection(s.quality_flags) for s in spans)
adapter.phase = "selected_replay"
verified = dn.replay_evidence_spans(raw, source_id=source_id, source_sha256=digest,
                                   mime_type=MIME, evidence_spans=spans, limits=limits,
                                   ocr=adapter, ocr_limits=ocr_limits)
assert verified == len(spans) and len(calls) == 2 and not denied
```

This excerpt is execution control-flow evidence from the run script. It is not a native count/spans/bundle receipt. Exact selected count, verified count, actual OCR lines and selected spans were not persisted. They remain null. The live node is **not PASS**.

The current helper's pure writer now uses `omitted_candidate_count`, checked through the existing synthetic port test. It was not rerun against real OCR. The two authorized inference slots are consumed; no additional OCR/provider call was made. The owned readonly sample was restored and removed after child terminality. The original failed MAIN AUTO and receipt remain unchanged for recovery.
