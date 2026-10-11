# ROOT W04 实际运行接口

此实施记录补充封存专家卡，不改其21文件SHA。ROOT独占audit_run.py和runtime tests；WP05 helper已STOP，具体composer CAS接线修复由ROOT接收为amendment。

- freeze_command_inputs旧五个位置参数保留。新增keyword expected_digests（argv index→exact {sha256,byte_size}；原tuple[str,int]兼容）、deadline（monotonic）、retention_mode='legacy'、blob_store=None。预期校验比较实际保存流的SHA/字节，不能先hash当前文件代替builder记录。CAS store必须显式cas；composer传store时统一设mode。
- SourceRef2只管原件，FrozenBlobRef4键只管准确调用输入；两者不能混。CAS body完整包括坏JSON/空字节，不假冒有效source。记录frozen_path实际CAS路径、frozen_ref不透明引用、consumed_path独立ordinarycopy；不可硬链接给可写CLI。失败blob可保留pin，不能宣称成功。
- capture optional Namespace：expected_digests、retention_mode、blob_store、stage_deadline。CLI --expected-input-sha256 INDEX:SHA:SIZE、--stage-timeout-seconds；CAS CLI explicit --cas-root/--cas-max-retained-bytes/--cas-max-peak-bytes/--cas-other-owned-bytes/--cas-scratch-reserve-bytes。other-owned baseline不含有界库存CAS root；保留unknown allocated，不把unique SHA体积当实际磁盘释放。
- 同stage deadline覆盖freeze/publish/prelaunch/child remaining/postcheck/seal；legacy只传原timeout保持。CAS seal观察在postcheck后、private清理前；record明确observation_phase。清理失败secondary不盖primary，input_cleanup_pending_paths写实际路径；recover_capture_workcopies只处理既有capture事件列出的同attempt c-*.json，append恢复事件，不删CAS/原件，不建立第二任务库。
- 同有效HTTP选项null与omitted等价，raw/projected共享optional canonical seam；thinking/effort/temperature/output变化仍失效。旧omittedSHA保持、旧null artifact/母账不改，不从新生成键盲目重发收费请求。production config仍原SHA、purpose策略将在真实G2使用tmp明确配置验证。

目前是工程实施状态，G1/G3独审和集中发布未完成，G2真实摘要/研究G4/G5未执行；预算和旧失败记录均保持。

## Final engineering acceptance

Audit main c0993332 and two single-skill installations now contain the final runtime. Final 147 tests PASS and all five independent material rechecks PASS; exact version receipts live in evidence/integration/audit-publication and evidence/independent/g3-audit. WP05 min-alias normalization and same-year quarter/half comparison are diagnostics/owner request checks, not new manual permissions. Failure recovery explicitly records partial private copies before a completed row exists; CAS originals remain retained. Historical RED and receipts remain unchanged.

## ROOT publication logging and scope

Ordinary CWP publication uses the existing push gate/CI scope, not all manual contracts. The mistaken 5627-case manual command timed out at360s and is not PASS; truthful failure receipt retained. Stream stdout to exclusive log files and persist timeout receipts before leaving, rather than buffering all output until success. This is coordinator execution detail, not a new project gate or runtime permission.
