# W06 cutoff v2：非作者集中复验

## 结论

**PASS_SCOPED_CUTOFF_PRODUCT_ACCEPTANCE_PENDING_ROOT_MATRIX**。原 P1 用量投影共因已修复；只跑原三个失败和四个必要控制，**7 PASS / 0 FAIL / 0 SKIP，1.39 秒**。没有重复 42 个独立探针、ET 56、FF 137、工具 195 或整链 41 矩阵。作者的四个可选显式路径 SKIP 仍不算 PASS。

对象是新产品冻结 `87495b11e3c41986c3a10374bae0c603af6db4d61d7b8ed8c6a01771b7ed3381`，8 个 ET/FF 文件实际 SHA 均匹配。此次 ET 三个文件相对第一轮不变；FF 产品的变化集中在唯一 receipt 结果投影。ROOT 仍负责完整矩阵、性能诊断和发布，这份报告不声称整项目或真实供应商网络已验收。

## 原问题与复验

1. 原三例 `stdout={broken-json`、`[]`、`null`，stderr 为当前 request 绑定的合格用量（1 请求、987 字节）均使用原 `probes.py` 的同一组断言。现在仍 `provider_unavailable/provider_result_invalid`，实际计数保留、complete=true，无新增调用。
2. 合法 `/2` cutoff 回执仍为 `not_found/call_after_as_of`，保留合格实际用量。
3. 旧 `/1` 普通 missing 仍为 `not_found/exact_transcript_missing`，没有猜成 cutoff 或 provider 故障。
4. cutoff 缺用量回执时，计数仍为 null、complete=false，未伪造零。
5. 新的一条必要控制：stdout `[]` 且没有用量回执时，仍拒绝结果，计数 null、complete=false、provider_started=null；保留 snapshot 并未制造 complete。

静态检查确认：stderr 在唯一边界解析一次，之后 malformed JSON、非 dict、错误绑定/退出和其他错误走同一 `unavailable` 投影。有效和 unknown 用量都从既有 snapshot 返回，没有新的许可、身份库、重复获取或 importer 调用。

## 原证据保留与 CWP 澄清

原失败 manifest `3140797e6c6839063446565ea88d89138ec4a9afae84ad1c8da03138443c9050` 及其 9 个文件全部在复验前后匹配；39 PASS/3 FAIL 的原日志、原预期和原测试源码不覆盖。

原 `probes.py` 的 trace 默认写父目录。为了保持冻结的原失败证据，retest 插件仅在测试执行期把 `TRACE` 输出路径改到本目录；没有修改任何断言、输入、fixture 行为、结果值或原文件。完整复验命令与所有前后 SHA 在 `retest-result.json`，新输出在 `trace.jsonl`。

ROOT 已澄清第一轮观察到的 CWP 漂移：只有 `operation_contract.py` 中 `acquisition` 的显式 `dict[str, Any]` 注解，用于 pre-commit mypy，无运行行为变化。现在绑定正式 ROOT 来源冻结：`397a02e903e1543c6ca4d3116eff10c03d46cb9d6fe657a1c93fb2860f1fcb2c`，该冻结内全部 12 个产品文件匹配并前后稳定；旧作者冻结继续保留。

## 边界和恢复

- 新 ET/FF 8 文件、CWP ROOT 12 文件、205 个旧 CaseSpec/工具交付文件、30 份旧 golden、原 9 个独立失败证据及作者修复 manifest 所列证据，均复验前后 SHA 相等。
- 作者修复 manifest SHA `2176c0c39e97d20ce510f73b7d72c47175ff1834e702b6e1a9d252621b6905c0` 匹配。
- 唯一新建短 `company-wiki/.tmp/cut-review-<uuid>` 已删除，恢复最初缺席；既有父目录/其他任务资料不动。运行环境仅允许 Windows 运行必要字段，HOME/TEMP 使用本次 scratch；真实凭证未读取或继承，socket 网络拒绝。
- 无产品、Git、config、key、raw、安装或共享 PWF 写入，无实际网络、provider、LLM 或费用。

**FROZEN STOP**。ROOT 可以根据原第一轮日期/绑定正控、未变化的 ET SHA、当前 7 项集中复验和其原 41 CLI 回放完成最后接收；性能问题属于 ROOT 后续单独诊断，不通过改 CaseSpec 或放宽 timeout/期待来解决。
