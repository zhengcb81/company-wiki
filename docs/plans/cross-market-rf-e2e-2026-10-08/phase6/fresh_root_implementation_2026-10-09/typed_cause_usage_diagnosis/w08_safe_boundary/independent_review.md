# W08 独立大节点审查

## 结论

**暂不通过（W08-R1：P1 公共错误输出仍有 raw candidates 泄漏通道）。** 已修的费用/字节、六字段 cause 与阶段/计数交接独立验证通过；不能据此声称整个失败边界都不泄漏。MAIN 已通知作者先写 RED 并在公共失败投影责任层根修；不得拿最终 RF preparation 的过滤抵消中间公开 CLI 已经泄漏。

审查者 fresh_native_documents，与两仓实现者不同。审查严格只读，两仓未提交源码、生产原件/config/keys、旧诊断和旧执行包均不改。报告/receipt 仅写本目录。

## 实际验证

- FF 最小责任包：`test_failure_usage_continuity.py`、`test_provider_cause_contract.py`、`test_local_source_prepare.py`、`test_source_ref_v2.py`，**59 passed，2.85s**。
- RF 最小责任包：`test_source_failure_observations.py`、`test_source_failure_cause.py`、`test_filing_fetch_client.py`、`test_source_preparation_complete_result.py`，**73 passed，12.07s**。
- 在自己 TEMP 亲跑五条 CWP→FF→RF client→RF preparation 公开 CLI 链，使用真实工程 CLI + 明确合成、无网络 provider。具体 argv/输出/退出/计时在 `independent_review_receipt.json`；不是只复读作者258/110绿报告。

| 实际控验 | 原始 CWP usage | FF / RF 保留 | exit |
|---|---|---|---|
| discover-fail | 17 bytes，$0.01，complete=true | acquisition-failure/1 逐字段完全相同；ensure/attempts1/calls2/downloads0 | 1/2/2/3 |
| deadline | 36 bytes，$0.03，complete=false | exact 下限 DTO 与 adapter_timeout 保留，不当最终账单、不重试补造 | 1/2/2/3 |
| malformed_usage | usage=null，complete=null | 原样 unknown/null，不记0 | 1/2/2/3 |
| local_metadata_gap | 没有 acquisition failure | finite local_metadata_gap，local_prepare/calls3/downloads0；provider_started=false，usage_complete=true | CWP query0，FF2/client2/preparation3 |
| no_registered_local_source | 没有 acquisition failure | 与 metadata gap 不同的 finite no_registered_local_source，local_prepare/calls3/downloads0 | CWP query0，FF2/client2/preparation3 |

费用只是合成 fixture 的诊断观察，实际 provider HTTP/paid calls=0。CWP query 的 exit0 仅代表查询执行成功，不是找到可用来源；FF/RF 没有把缺来源改成成功。

## 已核对的责任

严格 exact-key、版本、有限 code/scope、bool/null、非负且拒 bool 的 byte/count、finite nonnegative Decimal string 验证；缺失/额外/非法 usage 不穿透新 receipt 投影。没有重算/结算费用、复制账本、按 subprocess calls 推断 HTTP、从 unknown 构造0。

六字段 `filing-upstream-cause/1` 保持兼容，新增字段 additive 放在 v1顶层/v2 filing；filing 的 failure 独立于 transcript companion。现有 retryable/status/真实 child exit 不因 receipt diagnostics 改变。stage/attempts/calls/downloads 只保留有类型的真实观察，local_prepare 没有旧 attempts 时不填0/1。读者后失败仍保留前面已观察的 FF 计数。

RF human error/reason/回退 stderr 使用固定信息与有限 subtype，既有两条 raw stderr 测试改为安全语义有业务依据，已另加 actual-CLI known cause/no raw tests，不是为凑绿删断言。未引入身份扫描、授权 JSON、人签、private/public、canary 或新的许可链。

## W08-R1：RF client 的 `candidates` 未作公共错误投影

责任代码：RF `scripts/filing_fetch_client.py`（本次源码）第61行 `self.candidates = candidates`；第264行 `candidates=detail.get("candidates")`；第362行 `payload["candidates"] = candidates`。即使 human error 已净化、typed cause 合法，另一个未经验证的嵌套正文容器仍被原样发到公共 stderr。

实际送入 fake FF 子进程的 v2 error：

```python
payload = {
    "schema_version": "2.0", "status": "ambiguous",
    "filing": {
        "status": "ambiguous", "retryable": False,
        "upstream_cause": {
            "schema_version": "filing-upstream-cause/1", "operation": "ensure",
            "code": "canonical_import_failed", "provider_started": True,
            "usage_complete": True, "retry_scope": "none"},
        "candidates": [{"error": "https://invalid/?api_key=" + SENTINEL}]},
    "transcript": {"status": "not_requested"}, "calls": 2, "downloads": 0}
```

fake只消费 stdin、打印该 JSON 到 stdout、exit2。实际 RF client 命令为：

```text
python -X utf8 -B <RF worktree>/scripts/filing_fetch_client.py
  --filing-fetch-root <owned fake-fetch root>
  --source-ref-v2 --result-envelope --company-wiki-config <owned config.json>
```

stdin 是原诊断 `reproduce.request()` 的 exact 年报请求；owned config.json为`{}`，失败发生在 reader 前，无真实配置读取。精确当次绝对 argv 已在 receipt 的 `additional_controls/untrusted_failure_candidates_rf_client/observation/argv`。临时路径现已恢复删除，不假称仍可打开。

观察：client exit2，`synthetic_sentinel_leaked=true`，stderr JSON 的 candidates 仍含 URL/凭证样式字符串（保存时已替换 synthetic sentinel，不含真实密钥）。同包给 RF preparation exit3、sentinel=false；这只证明第二个消费者再次丢弃了该字段，中间日志已经不安全。

建议在错误序列化责任层一次建立完整公共失败投影，保留合法 typed ambiguity candidates，去掉未知嵌套容器/字段而不复制任意 upstream body。不要新加身份查询、人签或清一切有用候选。聚焦回归覆盖 v1顶层/v2 filing candidates、合法候选兼容及 nested unknown字段；code/cause/usage/stage/count语义不退化。相邻已有 legacy `_resolution_trace.reason`、source-is-not-reusable raw reason、missing_capture_fields 等亦应同层盘点，不能凭新 typed receipt 的安全性宣称旧失败正文都安全。

## 粒度 / 交付限制

RF `_prepare_source_ref_v2` 同时包含 reader 与 record 构造，因此新增统一 source_reader stage是当前接口的阶段粒度；没有独立观测的 finer stage 不应猜填。此粒度不影响本包真实计数/费用连续性，不单独阻断。

作者 PWF 仍有“Plan ready; tests next”旧状态，收尾时应更新为真实测试/待独立修复验收。工程关口通过仍不等于实际供应商权限、全来源覆盖或整家公司预测 M3；旧未知费用、丢失的旧输入字节不被本包恢复。

## 清理与复审

独立 test/CLI 全在自己的 TEMP，min OS env，无真实keys外发、生产原件/config改写或外部 HTTP。baseline_restored=true，temporary_root_absent=true，受审8个源文件在控验结束时 SHA 全未改变；只保留小型独立receipt和此报告。

根修 R1后只集中复验公共 failure DTO及这条相邻错误通道，再跑必要 affected compatibility，不重复每个小节点人工验收。历史 FAIL 报告/receipt保留，新的复审另文件。MAIN负责提交/并线/安装和真实公司 M3。

## 受审源码 SHA（当次 working bytes）

- `C:\Users\郑曾波\AppData\Local\Temp\ff-fresh-transcript-launch-20261009\scripts\fetch_filing.py`: `9e0ae4dc11b12367b7498e3f80599f63df48e27efd3eebba9e6ca59e4be8de51`
- `C:\Users\郑曾波\AppData\Local\Temp\ff-fresh-transcript-launch-20261009\scripts\ff_local_source_prepare.py`: `2120ee7bb00a7ad2476fc7032db593024b0d4441c2c07a1c4529021fc21f0653`
- `C:\Users\郑曾波\AppData\Local\Temp\ff-fresh-transcript-launch-20261009\scripts\ff_provider_cause.py`: `49f6ae540b2068ab6a6c9f5c9c823128adc9095a3bce4094fcec64302e724f18`
- `C:\Users\郑曾波\AppData\Local\Temp\ff-fresh-transcript-launch-20261009\scripts\ff_v2_envelope.py`: `8bca27f2acfdb4f4ba00342fcf4b9a783da6328ed69018c2b0286ff464fda534`
- `C:\Users\郑曾波\AppData\Local\Temp\ff-fresh-transcript-launch-20261009\scripts\filing_contracts.py`: `814c63bd8b684d946e7b3a18f194ed441da375070e822eb370ec9c3a136536eb`
- `C:\Users\郑曾波\AppData\Local\Temp\rf-fresh-dag-20261009\scripts\filing_fetch_client.py`: `b3297af7f0595362b26e594732de7a7c65d7a7f2f0a6da69e5832790d4bb4f37`
- `C:\Users\郑曾波\AppData\Local\Temp\rf-fresh-dag-20261009\scripts\filing_upstream_cause.py`: `57c5c5c579a6963959dd7636fc28312338779dc1ddbedb8f36a25a163cf8f3b8`
- `C:\Users\郑曾波\AppData\Local\Temp\rf-fresh-dag-20261009\scripts\source_preparation.py`: `4038be124d06c9d3b26a5d0490f82f18e03e0dd92fa4a3b1c72625da294c9ebb`
