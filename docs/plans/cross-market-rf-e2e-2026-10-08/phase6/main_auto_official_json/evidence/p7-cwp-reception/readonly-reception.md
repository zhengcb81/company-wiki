# P7-CWP-PROJECTION 独立接收验收

日期：2026-10-10。验收者：main_json_source_adapter_design。

## 结论

**source 叶模块接收：PASS / NO_BLOCKER。** 只验收构造确定性、深层快照所有权、存储/旧回放、新 producer 分派及 MAIN adapter 接口相容。不称 AUTO 全链或真实公司研究已经完成；未 merge、未 commit、未修改源码/P7 PWF/安装/原件/config/DB，未触其他 P7 仓。

## 实际交付与写集

- 工作目录：`C:/Users/郑曾波/Projects/_harness_worktrees/p7/cwp`。
- source base：`f8956d299b52849a4beb06e4071816ec72ddc6a3`。
- code delivery：`1c11ef0b5a838655559e91fab9a7bf38f1533d89`。
- 接收时 HEAD：`4f2c05c92f3aed9cdf91808a60e1c5d38adce6ee`，其后仅交接 PWF 文档提交，代码仍为上述 delivery。
- `git diff --name-status base HEAD` 实际唯一生产修改为 official_json_projection.py，新增两份 P7 责任测试，其余仅独占 .planning/p7-cwp-projection。未触 automation、source reader、CLI、structure/layout/import、config/raw/生产数据库和安装副本。
- 前后 `git status --short` 均为空。
- 原 HANDOFF.md/handoff.json 与 source commit、API、范围相符。8 份交接证据文件实际 SHA 全匹配声明，见 handoff-evidence-hashes.json。

## 独立验证

### 1. 新旧责任测试

再次实际运行两份新 P7 测试及四份既有 M3 parser/contract/projection/acceptance 文件：**166 PASS**，pytest 35.46 秒。

日志：p7-independent-166-tests.log。全部在独占 basetemp；禁 cacheprovider，显式 pytest_timeout。Windows relocation 清理 removed=true，外层 TEMP 删除。无修改旧测试/golden。

### 2. 真实离线 E2E

只读加载已检查的交付 E2E 程序，将其 receipt 目录显式重定向自己的 TEMP，避免覆盖交付证据；源码未改。

实际 import/2→build 1.0.2→persist→catalog close/reopen→load→replay→export，覆盖 official-paged-qa 和 official-flat-list、多 issuer、两真实母页、三页全部排列。**PASS，4 cases/4 checks，temp_restored=true**。

证据：p7-independent-e2e-receipt.json。原页每份 1 个文件、小投影独立存储、没有按公司复制整页。receipt 还记录原始 SHA、producer、span version、文件体积。零外部 provider/model，USD0。

### 3. 旧字节独立比对（不用新 golden 自证）

`git show f8956d...:src/company_wiki/source_catalog/official_json_projection.py` 读取真实已验收 base blob，在内存执行旧构造；同一小 fixture 与新默认和新显式1.0.1比较。

- canonical payload **逐字节相同**。
- to_dict DTO **完全相同**。
- 三者 SHA 均为 `df3f6502845450a90d28e82d1690e3bbd42dc326002ee19595917ca50fdbcee5`。

证据：p7-independent-legacy-blob.json。未 checkout/reset 或重签旧投影。

### 4. MAIN 接口兼容（内存覆层，不冒充已合并）

仅在独占 Python 进程，将唯一 P7 official_json_projection 叶模块以真实模块名加载，其他模块均使用 MAIN 工作树源码。真实两页 import/persist，调用 MAIN open_verified_projection→真实 selector/select handler→实际本地 prompt/decode summary→verify→replay/generation。

**PASS：**

- 新 producer cwp_official_json/1.0.2；structure parser 仍1.0.1。
- select.parser、native EvidenceSpan、bundle.versions.parser、generation.parser_component 都是1.0.2，没有硬编码回退到1.0.1。
- 正倒序同 projection ID；真实 replay 4 locators；原件未变；0 HTTP/外部模型。
- 本地离线模型只生成 prompt-derived fixture draft，不能作为真实模型质量或 whole batch 通过的证明。

证据：p7-main-adapter-overlay.json。首次探针所有流程断言已通过，最后打印内部 mappingproxy 出错；探针改用公开 to_dict 重新跑成功。这是探针输出错误，没有改生产代码或调整产品契约。

## 三不变量源码核对

1. 默认1.0.1保留输入页顺序和封存身份；只有两个 builder keyword-only projection_version='1.0.2' 才做 canonical 页排序。可靠正页号优先、SHA tie-break；页内真实 record/field 顺序不改。缺/重复页与冲突仍 partial，未凭排序补齐。
2. Projection/Record/FieldBinding 对输入/DTO 中嵌套 dict/list/range 做所有权隔离，to_dict 返回普通独立 JSON；persist 拒绝 payload/hash/ID 漂移，不静默重哈希。
3. load/replay/export 按 sealed adapter.parser 分派1.0.1/1.0.2；未知 producer、structure1.0.0明确拒绝；EvidenceSpan携实际producer版本。

已披露的 `_FrozenDict._data` 私属性旁路仍可由蓄意访问内部容器触达；不属于公开 DTO 修改路径，persist/replay会拒绝漂移，按交付记录保留限制，不新增个人项目权限/人工审查链。

## MAIN 下一步与边界

- ROOT 可按授权集成代码 delivery；不需要再重跑完整166组作为逐小门。本次真实 source责任组已经集中通过。
- MAIN 新构造调用可显式 opt-in1.0.2；旧 sealed1.0.1继续封存解释，不能批量重排/重签。
- MAIN source稳定后，最终集中重跑 mixed AUTO CLI/public read/费用/恢复/终态责任组即可。
- 原交付 exact HEAD CI 为 not_triggered（分支push未触master-only workflow），本验收只确认本地真实测试；不伪称远端 CI green。安装候选仍空。
