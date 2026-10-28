# A+B 质量节点独审：中间 CHANGES_REQUESTED

两个P2实质问题，均已先报ROOT。审查人非A/B作者，产品、既有测试及PWF零编辑。

1. **SQ-IR-01：无明确指标主体的前句被签为unique支持。** `There was an increase of 12%.` 后接 `This increase was due to expanding our cloud services.` 时，reference返回unique；真实_cand路径进一步把后句送作meaningful_fact/operating_causal_driver。`An increase of 12% was reported.`、`It increased by 12%.`、`本期同比增加12%。`同类失败。仅用方向词前非空字符串判主体，把There was an/An/It/本期同比当作已闭合主体；同源同节邻接不补出缺失的指标身份。应复用已观察的源断言/metric主体绑定，保守延期。
2. **SQ-IR-02：每task硬cap2未在decoder落地。** 实际模型边界对t1传3条合法局部clauses，保留t1-1/2/3，无异常；当前只查全局40。请求/prompt宣称超逐task上限会整响应拒绝，实际不符。此缺口旧HEAD也存在，不误称B新引入，但本节点明确要求40/2硬cap。独立反例应抛`NarrativeContractError`，路径见同目录`test_independent_quality.py::test_per_task_hard_cap_is_enforced_below_global_cap`。

首轮实际收集71：62PASS/9FAIL，4.89秒；其中A原43与B10通过，A作者在审查期间追加4个同类反例也进入收集并失败，自有14项中9PASS/5FAIL（4同根反例+1真实生产路径）。随后cap单项1FAIL，3.04秒。不是10个独立根因。Conda -B，timeout插件显式加载，仅asyncio_mode未知选项警告。

其余已审：unknown降description/失去金融豁免且经营正例存活；support-owned hint不二次分类、context不捐排名；歧义数表uncertain不能绕过；不同role/context/kind/section不去重；显式annotation registry与reading hash共享且任意reading_*事实字段仍严格验真。cause action扫描16/32/64动作的实际regex输入为11160/22040/43800，近线性；6→14预留是新增扫描，16M cap不升。

两组旧测试调整合理：未绑定数表的原文/flag/citation仍留存，仅生成defer；restart由durable paid pin复原scratch下界，按pin字节断言符合真实owner，且完整reservation/费用/POST相等断言仍在。未重跑661/125/完整clean-deploy，不替作者未完成整批签绿。

0POST旧材料回放范围准确：60→53可发送，旧响应24→19剔除5财片，sourcegold3/3、研发/计划保留；t37旧漏项仍缺。不代表新全文选材或新摘要通过。

A在审查期间继续修复，报告时有文件相对handoff变动。下表是**报告时当前18文件SHA**，不是把旧RED或旧GREEN冒绑到修复后源码；待v2冻结，仅对两根因及相邻必要合同定向复验。

| 文件 | 当前LF SHA256 | 与初始handoff一致 |
| --- | --- | --- |
| `src/company_wiki/source_catalog/narrative_business_policy.py` | `d813a6ec983c11a3df7076831e06675027548a19b6fe94b0e9a20fcf70a28550` | False |
| `src/company_wiki/source_catalog/narrative_business_disclosures.py` | `3818577d5249f2d517ae26eb5c2877cf1bf375858ed19559ebfd43f091360351` | True |
| `src/company_wiki/source_catalog/narrative_operating_relations.py` | `977b0fc2d9c47143f20c70d0899f85167b06eec5b10ea237af2dfca192435b8e` | False |
| `src/company_wiki/source_catalog/narrative_reading.py` | `51ecc1ca4ba55f170786af2d7aea28ee5dfe05cf9f0d2711d8f617ef16cd74b9` | True |
| `tests/unit/document_understanding_selection/test_summary_source_admission.py` | `fac00ed764f9deaab88c4550476cf8ff20915a2e4e85124c858ce082ac603f6a` | False |
| `src/company_wiki/document_understanding/source_cards.py` | `e769d288d6fc20735319db027fe21a03e6b121a6144bcded9c22bab324d1ba29` | True |
| `src/company_wiki/automation/narrative_model_scoped.py` | `01f17b424ed4230aacca5f61a2cfc5c05dd542307f9c89ba96ee0e91a7fc09b9` | False |
| `src/company_wiki/automation/narrative_model_extractive.py` | `de68b05034bf9517bfafcfb7b2ee680db6cf92f97aa585e45e11dc38380bf177` | True |
| `src/company_wiki/source_catalog/narrative_finalize.py` | `00f9b88d6661b5a164ef0f434f454d2270f2b84dafa01419acf04d9a1ef4c07f` | True |
| `src/company_wiki/automation/narrative_replay.py` | `7d0f8f6de962713d955a8afdbc8be1b9990a1e443aa5b06be1aa7449bbc0f222` | True |
| `src/company_wiki/source_contract/selection_annotations.py` | `bb242e46cf636fa91b1e6448614d98a788523f88ed9a85cbb7021bf54dd8a444` | True |
| `src/company_wiki/document_understanding/decision_inventory.py` | `d3562d70470e6cd50f1e638e63e817199e3acedd67cbed3f59a34137ea8344ff` | True |
| `tools/document_understanding_benchmark/phase_c_observer.py` | `4d7da3911ae502944c273f3f3e7b8c62f5675aa9d92a9730ed3efeb9c7a4e525` | True |
| `tests/unit/test_scoped_source_admission.py` | `93735de0411c7c554063ed165ea0ef6508c0793dd12a5cdd523a9fe3cc9d2080` | False |
| `tests/unit/document_understanding_selection/test_reading_untyped_numeric_quality.py` | `11f0b5d768bcfebf690a8bafaebc640511e42545ae945cedaabb4683dd79fba5` | True |
| `tests/unit/document_understanding_selection/test_reading_untyped_numeric_prose_controls.py` | `40f99cadadde7ebac7e5868e8c51e5120502fa0100049c49563a1d98f3816a84` | True |
| `tests/unit/test_narrative_scoped_runtime_recovery.py` | `9413ef69e40e8330a47be70d80b69244d4113f6aa27ab358eeee9997c1f68971` | True |
| `tests/integration/test_shared_scoped_public_request.py` | `b56c880f6037dd113e4b2f5852a3c76a82c2b434f1f08a2c7b07301ce0d0ed8a` | True |

自有`.qir28`已按绝对工作区边界核验删除；同步进程全部结束，环境变量仅存在于已退出child shell。无模型/网络/PDF/下载、生产配置或原件写入。证据保留`tests.log/xml`、`cap.log/xml`、`scan.json`及短独立测试。
