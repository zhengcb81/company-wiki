# W04 G3 独立审查：原冻结快照

原快照工程判定 **FAIL**；研究质量 **NOT_EVALUATED**。未改源码、旧运行、配置或 canonical，零网络/模型，未重跑历史 suite。

## 发现

- **G3-01 P1** — skills/revenue-forecast-audit/scripts/execution_request.py:230。Composer forwards nonnull blob_store without retention_mode=cas into ROOT default legacy boundary. 反例：input_snapshot_blob_store_mode_mismatch; no child.
- **G3-02 P2** — skills/revenue-forecast-audit/scripts/authoring_provenance.py:113。Period comparison checks year and quarter/half to annual conversion, but omits same-year quarter/half identity. 反例：PASS; diagnostics[]. H1->H2 also PASS.
- **G3-03 P2** — skills/revenue-forecast-audit/scripts/audit_run.py:627。Rows append only after materialize succeeds; partial-copy cleanup failure goes only into store cleanup_pending. Capture pending paths/recovery recognize only completed snapshot rows. 反例：input_snapshots[]; summary pending paths[]; sealed blob pending contains existing c-*.json; recovery rejects outside_owned_attempt.
- **G3-04 P2** — skills/revenue-forecast-audit/scripts/audit_blob_store.py:362。Seal checks at entry and during blob verification, then performs final physical inventory without a completion deadline guard. 反例：Returns seal observation with no error after D.
- **G3-05 P2** — skills/revenue-forecast-audit/scripts/execution_request.py:59。Alias dict comprehension silently overwrites canonical dimension; conflicting equal-dimension bounds become insertion-order dependent. 反例：Effective and native observed1000 accepted.

## 检查

| 检查 | 原快照状态 | 证据 |
|---|---|---|
| real_builder_to_cas_helper | FAIL | original-composer-red.log |
| exact_builder_stream_digest | PASS | boundary-probes.log |
| money_zero_explicit_native_unknown | PASS | boundary-probes.log |
| conflicting_alias_caps | FAIL | alias-probe.log |
| cas_no_replace_private_isolation | PASS | boundary-probes.log |
| physical_peak_and_restart_inventory | PASS | boundary-probes.log |
| failed_authoring_input_pin | PASS | pin-seal-probes.log |
| partial_private_cleanup_recovery | FAIL | recovery-status-probes.log |
| same_stage_real_child_timeout | PASS | boundary-probes.log |
| seal_inventory_crosses_stage_deadline | FAIL | pin-seal-probes.log |
| source_identity_transport_business_status | PASS | recovery-status-probes.log |
| period_same_kind_substitution | FAIL | boundary-probes.log |
| research_authority_boundary | PASS | boundary-probes.log; recovery-status-probes.log |

命令、原始输出、SHA 和精确输入见 JSON / evidence-manifest。后续 ROOT amendment GREEN 单独复验，不覆盖本次 RED。各 owned 短 TEMP 已清理。
