# 节点 C 真实资料验收准备交接

状态：准备完成，等待 ROOT 下一次源码冻结；**未运行选择器或正式摘要**。ROOT 曾通知可执行H1，但随后撤回当前freeze、通知A旧fastpath要R3返修；本agent收到后一律等待，未启动该次测试。

独占文件位于 `.planning/architecture-quality-20261101/real-acceptance/`：

- `README.md`：唯一准备入口、准确阶段1命令、阶段2已确认参数、恢复与清理规则。
- `run_source_case.py`：generic单case真实owner replay；90秒父deadline、只读Store拒绝、DB/WAL/SHM/runtime前后指纹、小JSON；native成员逐slice对齐，不仅查独立span。
- `cases.json`：6个来源SourceRef。H1冻结12个原文unit（p12三遗漏、D&M、p14八成员）和9个旧context错配pair；7个合成语法反控另列、不算真实覆盖。
- `phase2-observed-native-entrypoints.json`：R4成功paid prepared/same/cross观察的准确argv，标记不得原样执行旧树。
- `catalog-sample-inventory.json`：经只读catalog/query_ref/describe列举的真实候选；没有打开原文/解析。
- `preparation-ledger.md`：所读证据和准备错误记录。

## 已确认的来源与边界

H1、华利IR、BRK股东信、微软原语言TXT、A股招股书、港股年报候选均有已登记SourceRef。后两类只准备工程replay，业务段落oracle/原文内部身份尚未冻结，不冒内容或身份PASS。BRK股东信也不能代完整10-K。

华利旧temp catalog配置 `cwplC-8tlwvdcu` 和BRK `cwplC-27v2wjpg` 已不存在。旧命令不能原样重跑；正式摘要须新独立catalog/AUTO，通过source owner注册原根只读引用及既有冻结source facts，不复制PDF/整DB、不向生产补事实。H1纯只读选择仍可复用原p3w12 config。

读取了旧canonical脚本但未运行，因为其输出路径指向旧证据。读取了R4 storage/native-crosscheck/context-observations和成功operations；未读密钥、未执行旧observer/bootstrap、未写原R4/R3。

## 验证

- 六case全部通过当前 `SourceRevisionEventPayload.from_dict`。
- runner AST、ROOT解析、native-member正反slice、`--help`及Ruff通过。
- 一次请求准备使用None lineage被真实合同拒绝，改由所属 `source_read_policy_sha256(config,None)` 生成真实SHA；原H1历史pin保留作为lineage。
- 仅当前readonly SourceCatalog.reader列举/describe来源，断言 `_store is None`；没有调用open_version/verify_version、selector、parser、模型、下载或RF。

## ROOT下一步

下一freeze后按README仅跑 `r4-cn-h1-real`，输出新 `h1-current-v1.json`。若runtime前后不同或90秒超时，不签当前版本，不重复整批。收据只观察源工程、partial、覆盖和旧context是否重现；未见旧context不自动证明语义正确，需集中独审。

阶段2等待A复审及ROOT确认当前配置/母账；原生configured CLI参数已从当前 `--help`核对。新工作区重新记录真实POST→prepared中断→same/cross零追加→新artifact实际RF参数/公式/report/snapshot。不得复用旧artifact返回值或旧收费余额冒新验收。

该agent未修改产品/主PWF/Git/index，未复制或删除原件，未修改或恢复生产/旧隔离数据库。准备完成后可STOP释放槽位，ROOT后续followup运行同一H1即可。
