# v4 冻结字节漂移调查与续接说明

日期：2026-09-03（UTC）。范围仅限 Source Catalog worker 的隔离计划目录。

本文是作者只读诊断记录，**不是**正式独立审查 PASS、实施授权或 worker 恢复授权。
它位于 v4 明确排除的 `reviews/` 目录，不改变任何 v4 normative 文件或历史 manifest。

## 1. 当前结论

- v4 manifest 自身未变；48 份 normative 文件中 27 份当前 raw bytes 与冻结值不匹配。
- 16 份在内存中仅将 CRLF 转为 LF，即可精确复现冻结 SHA-256；这 16 份已证明只是换行差异。
- 另外 11 份当前规范化内容与 pre-commit 保存的补丁结果相同，但尚不能复现原冻结的混合换行
  排列；因此**不能宣称这 11 份已证明只有换行变化**。
- 安装的 pre-commit 在处理未提交修改时执行整仓 checkout，再恢复补丁。与统一写入时间、
  Git 提交及 `core.autocrlf=true` 结合，构成“并行提交的 hook 恢复触发字节变化”的强因果证据。
  这是基于机制和时间关联的归因；没有进程级文件写事件追踪，不能把关联说成直接捕获了写入者。
- v4 当前状态为 `INVALIDATED_FROZEN_BYTES / HISTORICAL_ONLY / NOT_IMPLEMENTATION_AUTHORIZED`。
  无论内容是否语义等价，都不允许按当前文件重算覆盖 v4 manifest。

## 2. 时间与证据链

| 事件 | 证据 |
|---|---|
| v4 冻结 | manifest `frozen_at=2026-09-03T17:43:17.152301Z`；48 normative 文件 |
| 冻结时 Git HEAD | `16ef042f40cc85375d0de5196c654a9c027a6ef2`，仅作漂移线索 |
| 冻结后检查 | 作者当时再次运行得到 7696 PASS；测试/DAG reviewer 后续消息也确认曾独立核验 48/48 hash 与 7696 PASS，但该审查未形成最终 verdict |
| 后续四份 hook patch | `patch1788462572-20524`、`patch1788465177-11488`、`patch1788469100-19540`、`patch1788470956-14668` |
| 四份 patch 相同 | 每份 552211 bytes；SHA-256 均为 `11e0a7bc6649485cedc85b6f22c5535c817a38779e915d861f118c2e6d7d790b` |
| 最新 patch 写入 | `2026-09-03T21:29:16Z` |
| 27 个规范文件写入 | 集中于 `2026-09-03T21:29:17.252–266Z` |
| 同期提交 | `a0c7629be6608fb668bbaf8856950df1b265d61b`；reflog 显示 commit 时间 `2026-09-03T22:29:15+01:00` |
| 续接时检查 | `FAIL: 27 error(s) after 7696 checks`；全部为 `MANIFEST-BYTES` |

v4 manifest SHA-256 仍为：
`c34b849475f1efeb0a3237af2d4a748a6e36c276f7c91b6ad07cae8ea3004711`（9598 bytes）。

冻结前输出 `plan_freeze_check.v4.txt` 的 SHA-256 为：
`ca47be86a15d94c68787c637d08567cdf57b2be51e27ee67f2cdff84b9137af7`。

注意：7696 是**计划一致性检查项**的数量；315 是**计划中登记的测试 ID**数量，
不是已实施并运行通过了 315 个 worker 测试。项目修复实施尚未开始。

## 3. 本机机制证据

只读检查得到：

1. `git config --show-origin --get core.autocrlf`：
   `file:C:/Program Files/Git/etc/gitconfig true`。
2. 对计划目录里的 Markdown/JSON 执行 `git check-attr text eol`，两项均为 unspecified；
   该目录当时没有 `.gitattributes`。
3. `.git/hooks/pre-commit` 调用本机 Python 的 `pre_commit`，配置为根目录
   `.pre-commit-config.yaml`。没有运行或修改这个 hook。
4. 安装代码
   [staged_files_only.py](</C:/Miniconda/Lib/site-packages/pre_commit/staged_files_only.py:23>)：
   - 第 23 行定义整仓 `git checkout -- .`；
   - 第 54 行通过 `git diff-index --binary` 保存未暂存差异；
   - 第 75 行将差异写入缓存 patch；
   - 第 81 行临时 checkout；
   - 第 86 行在 finally 中恢复 patch；
   - 第 26–32 行说明 apply 失败时可用 `core.autocrlf=false` 再试。
5. 上述安装源码 SHA-256：
   `a0c5aacfbfaa02de4370a2e9d2ee1f092016c8304ac2dc6c4a4d4451158aab96`。
6. 最新 patch 的 diff headers 包含全部 27 个失配文件，也包含本目录其他未提交计划文件。
   该 patch 还涉及其他任务文件；本调查只读取/处理本计划路径的 diff，未恢复或修改其他路径。

因此，即使各任务没有主动编辑对方计划文件，**共享工作树的提交 hook 也可能触碰对方未提交文件**。
只限定 AI 的编辑路径，不能保证这些文件在别的任务提交期间保持物理字节不变。

## 4. 逐文件原值与现值

下表的“LF 可复现”表示：只在内存把当前 CRLF 转 LF，再算 SHA-256，是否等于冻结值。
false 不等于确定存在语义修改，只表示这个简单变换不能证明等价。原文件未被转换或覆盖。

| 文件 | v4 冻结 SHA-256 | 当前 SHA-256 | 当前多出 bytes | LF 可复现 |
|---|---|---|---:|---|
| acceptance_thresholds.md | d8feb22e26378924a611e5aa6cdecf3b54270671ede0a5c4b6ecaf15aaf871db | d6f3068498c8c6d8064c0babae809afbb320916da240567805f9a4cab20c96af | 336 | True |
| agent_review_gates.md | 51923c8576f4c5441353af12e40d29abe5fb7a804087316bc4cf5a8827a77da6 | bbab56f39b7a9392295bca855f65ad99c5f7372dc54f4d4039adf909a3641a26 | 567 | True |
| authorization_manifest.schema.json | 7bc50fb71eb4ee4840286fb33aac9707289f6279b8ac65a5dc38ffbe1cf81bb7 | 4c9458d6e3da59d2ed3e588051ed4f393183e3ccc25606a150567b310e28d446 | 45 | False |
| evidence_manifest.schema.json | a60bfe37fd1ddee6ee4cac4a2f14d68c6ca397909a9bed42e7033d1452209a33 | 561a0c289751e5f1e0cda4f203c3393dc4a175051c439c03f983b79b180bfd3a | 132 | False |
| execution_playbook.md | 77503ad91939595d7dc01594b1c26e11c82f96626ec32ede8a5d52451fa1cc32 | 14bfca6216acc8f4de49ec59b58e11906f40dd9d416e9da15493322e8696ecba | 1171 | True |
| findings.md | 4bd0b89fb25a786e8297162a450ee33ebf7be8861b691c0d8284bc603dba5505 | e246b222fac6da7682f6af680029eb8d5dc9e36a05714eae15ea5f6074e090f1 | 92 | False |
| gate_dag.v4.json | 3183cd016ed4bdd8ad7883afdd65f1991471e2f46f57654ec49c495a26542992 | c06b20d040eb8c7adcb4186986c6e0ddffb83b1d122e9773ea415d9bf038dee1 | 285 | True |
| gate_ledger.schema.json | 7cfc8abd3ad7fc32d6d0fd2bf952bb76a3d10008ba1910f9ff023816c25037af | f9f14cc3f73bd34b4cd56a17454be80b40b1ea83ae0bedf450e2723106588b55 | 384 | True |
| gate_ledger_validator_vectors.schema.json | 7a0891291345bda03ccf6850326935faf7566e30960f3e8e33a463fd9e2ffc77 | d1395630ad9419692ba37be3b40ff4e55701560c6c4dbf1557a1f71063b2ed10 | 170 | True |
| gate_ledger_validator_vectors.v4.json | b932f9c879b1254be973cdffe615c0689a94315191b8257b8067179d17e8dfc4 | 7e2472d76ae93e9338d5c5b8ec02ec5f44806b9da3e159ccc4cebb46cee1fcef | 270 | True |
| gate_state_machine.md | 860c3472ab35708fe0caef1b4a0af17752bab0e24b18c23317e6ce6ce4285700 | 49940700b4ee117211bbafef50b8d0c55c2f1045a324a29f06bfce2fea3b3c47 | 453 | True |
| implementation_agent_prompts.md | 8b805ec7a1799ac7cc988e521a2b98b516b1f3f18086359f65414463f875e92a | ab5c2fbc28996f5d501fff39e2a314030886857b5f246db58293df283f00c73d | 388 | True |
| ledger_validator_contract.md | 441a3276ebcd049efa738c602a98fe102a02634cbd8f8f4e9dbefe75b2ecefab | c5b94e63b055ef6a989cb77282e2ade13cd5ae330899c90ee32567fbcf877978 | 249 | True |
| operation_contract.schema.json | 9a074cba494e9ce8e670ab3940201280aacfe01d0aa880a52873e42b238b1721 | 7e44a159d83801565478bf0fc34ce6809d0871d68f4d140020af2110d91d07f8 | 82 | False |
| operation_contracts.schema.json | 5f3350756c169582076091cbed3017544017a0c72cc3e85111f70fd65aa6808a | e4924cfbad3087fceafc6d5a9f60216a325d31ec768d557775c3c5c407b58b31 | 7 | False |
| operation_contracts.v4.json | ea5350c66b701b34888bb4197e56e79f64e8e421004a96a01194ec159c462098 | 4cf7dab5c2ced9f0ddb73319d1ef278467ba00fc4e36fb126fb37bb3cfe9f187 | 7 | False |
| operation_intent_manifest.schema.json | 36e41bc0c6bdbbd9d14e2f2d3c6d6c38fbb09ae66368197d863a4872c77412ee | 57363a15c67498a384800aa0b8bf9140b9a8cc77edc4bbf80c1bc18965053a9d | 32 | False |
| operation_intent_template.schema.json | 50ef54451e389c66ce1efeb297da80b359048f00bf1213b2e4cf718e080e7fd9 | d1a8ec48d648257bf32ae014dfe9e8fb788400a2d30657ec6261317494001b9a | 1 | False |
| plan_consistency_check.py | 3897ee37d67765846ab72b3826a2725944236b934cb28a4c0ff8b8e21988698b | 0f008bad07297c4fa86261a3473dd0dbdccd4f86f64821e2014710be1618661f | 578 | False |
| plan_review_findings.md | c7c120beb76598c6256ef7874681562dd8127ab5e1bddef4d28fe4f04c61b183 | 17206a816de688afa29bfeff734e0abc79954cef7964f0d4de568f6e07dd9559 | 187 | True |
| README.md | e39d86bbe87bf5243c7097ab243133d6e6b864d54c168680f98af3aabe920c3a | 200e618179a360bc558b8c0e50140cca2b4858a846b3172d9fb0bcb229567e7e | 16 | False |
| rollout_rollback_runbook.md | 1fe062b08e778eb9a468eabcfaa3ee86d3aebb6fd703f32ac552fe6fae2576d9 | 2728be56f758a53d9a91631707909ff88e0a5d394760bccdbbaaed67c64786a4 | 515 | True |
| task_plan.md | 2bd0aa046a8f71ab17df69fdb498fb1709fc2fcc95272583bed5c90ae2ccf305 | 46634bec14cf3046c30b4b0159413b91ea66e00fb8833c3ab046dc7b14f2e336 | 829 | True |
| test_acceptance_plan.md | fad4e438de826cdf68ffbe6ca3cdc8087c3eef88f8713aa7c2d289887ddd2fed | 8f0a86919e60d1cac6b022cb2bb26a284748c707bdf35972a0938a8a609bffc3 | 793 | True |
| test_id_registry.schema.json | 73f7d9dbb4ace209d76df95b91f11e4a8a770dee9a96911879b01e8f8d6500cb | 7f61d64464437b83b2bc14da06b33acc53691263859679fd9ca8093f7c0c1d74 | 173 | True |
| test_id_registry.v4.json | 673dc7a6526c7b02c7944727a1c6d4f570b5e61971d8b0d7a192ea19b8299629 | b2040c1557ed6b4efb1fa9cee029375594c0bc9285c1d7ccb566937a6ac85add | 5971 | True |
| traceability_matrix.md | 90d96446a5a67fa34c358ce82326a2c55d02839875d68249b3ec939e19689595 | 7a6865532489f8783b34cd62e138f4f2de8ce8fb89bbf56d819a7c3567626ef4 | 227 | True |

## 5. 另外 11 份文件的补充核对

作者读取最新 hook patch 的对应 diff 与其 `index` old blob，使用只读 `git cat-file blob`
取得基础内容，在内存解析 unified diff，重建标准 LF 内容。全部 11 份重建结果都与当前文件的
LF 规范化结果逐字节相同，没有执行 `git apply` 或 checkout。

进一步分别尝试“base 行 LF/CRLF × 新增行 LF/CRLF”四种重建方式，均未复现这 11 份原冻结
SHA-256。因此现在只证明它们与 hook 保存的文本一致；不能声称已找回原冻结字节。
可能存在更复杂的历史混合换行，但不能把这个可能性当成已验证事实。

## 6. 独立审查状态

原三路正式审查均因账户用量限制结束，没有最终 verdict：

- SQL/性能：`INCOMPLETE_USAGE_LIMIT`；
- 生命周期/安全：`INCOMPLETE_USAGE_LIMIT`；
- 测试/DAG 可实施性：`INCOMPLETE_USAGE_LIMIT`。

重置时点之后，测试/DAG agent 被重新派为**只读 forensic 预审**，不计作 v4/v5 正式审查。
其最终诊断结论另行追加；作者不得代签独立 PASS。

## 7. 不能采用的“快捷修复”

- 不覆盖 v4 manifest，不把现在的 hash 填回 v4。
- 不用 `git checkout`、stash restore、reset 或 apply 恢复其他任务的文件。
- 不在当前共享工作树执行 pre-commit 重现破坏。
- 不声称仅添加 `.gitattributes` 就能完整隔离：它只能控制 EOL 转换，不能阻止 hook 临时
  checkout tracked 文件。审核者仍可能读到短暂旧态。
- 不把 v5 manifest 改名后仍盲用硬编码 v4 的 schema/checker/入口文档。
- 不以继续调查或额度恢复为理由启动 worker、启用自启动或开始项目修复。

## 8. 建议的安全续接步骤（尚未执行）

1. 保留 v4 manifest、冻结输出和当前文件；先取得稳定审查边界。
2. 优先使用不会被当前仓库 hook checkout 涉及的新独立快照；若仍审共享 tracked 目录，
   必须先协调暂停另一个任务的 Git 提交/hook，并验证审查前后文件 hash 不变。
3. 仅在该计划范围内定义 byte-preserving Git 属性；不改全局 Git 配置、根 hook 或其他项目文件。
4. 由于原 11 份冻结字节尚未找回，v5 应当作为**重新审查的新基线**，而不是宣称 v4 等价恢复。
5. v5 版本合同必须闭合。两种方案择一并独立预审：
   - 完整迁移所有 plan revision、schema 常量、machine instance、文档与 checker；
   - 显式区分已有机器协议版本和冻结 generation，新增严格的新 generation manifest/schema/
     checker、supersedes hash 与入口说明，不能含糊混用两个含义。
6. 冻结前执行所有只读一致性检查，保存精确输出；冻结后重新逐项核验字节、大小、路径、
   source report 和排除集合。任一变化即拒绝送审。
7. 三路独立 reviewer 对同一稳定冻结输入从零审查；所有 P0/P1 关闭前不得作为实施输入。
8. 最后再次只读核验 worker paused、相关进程为 0、自启动入口 absent，并更新 excluded 日志。

本轮没有添加 Git 属性，没有创建 v5，没有转换任何规范文件，也没有改变 worker 状态。

## 9. 独立 forensic 预审实际返回结果

实际 reviewer：`/root/v4_test_dag_review`。以下为主agent对其本轮完整返回文本的忠实摘要，
不是代填正式Gate machine payload，也不是v4/v5正式PASS。

- reviewer独立重算manifest和27个漂移文件，确认27个当前文件均为纯CRLF、16个LF-normalized
  hash匹配，另外11个仍不能证明仅换行变化。
- reviewer独立从patch old blob逐hunk重建，27/27 context完全匹配，重建结果等于当前文件的
  LF-normalized内容；没有执行git apply。
- reviewer核对同一次提交的文件清单只有`tests/contract/test_zr1006_broker_cohort.py`，没有计划
  文件。ruff/mypy的files过滤并不能防止pre_commit外围整仓暂存/恢复流程触及本计划。
- 独立结论：当前v4冻结失效，高度支持pre-commit恢复与换行转换的解释；未取得进程级写事件，
  也未找回11个原冻结字节，故保留这两项不确定性。
- reviewer明确否决“只加.gitattributes即完成隔离”：checkout可能在审查过程中替换字节，随后
  恢复，导致仅前后hash相同仍不足以证明阅读期间输入稳定。
- 属性保护实施时须逐文件检查有效`text/eol/filter/working-tree-encoding`，属性文件本身必须纳入
  新冻结集合。
- 新版本必须解决冻结generation与现有协议revision的身份映射，不能只改manifest文件名。

## 10. 本轮末 worker 只读实况

- `worker_control.json.desired_state=paused`，`updated_at=1787262212.37034`；本轮未写该文件。
- HKCU Run 的`CompanyWikiSourceCatalog`精确值不存在。
- 扩大匹配以覆盖`company_wiki.source_catalog.cli worker`后，目标进程为NONE。
- 对应计划任务、服务、Win32 StartupCommand均为NONE（只读授权查询成功，非权限失败空结果）。
- 未启动、停止或重配worker；没有修改生产数据库、配置、源码或主线计划。
