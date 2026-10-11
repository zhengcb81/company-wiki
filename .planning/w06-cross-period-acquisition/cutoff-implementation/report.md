# ROOT W06 cutoff 共因修复作者交付

结论：`AUTHOR_COMPLETE_PENDING_ROOT_MATRIX`。本线作者和 FF 并行作者均已冻结 STOP；没有 commit/merge/push/install，没有修改 CWP 产品、205 个原工具冻结文件、生产配置/密钥/原件或其他 WIP。

## 改了什么

- **ET**：保留真实日期排除原因。FMP 已验身份/期次的唯一未来 call 返回 `not_found + error_code=call_after_as_of`；Motley exact fetch/discover 共用同一次 listing，先验证目标期，再保留 `publication_after_as_of`。原 batch dict 入口保持，空结果/别期未来记录不冒 cutoff，多候选歧义和发表日未知语义保持。
- **FF**：合法 not_found 与供应商故障分开。闭合日期码投影为同名 reason；普通/旧/未知诊断 not_found 为 `exact_transcript_missing`。实际 usage 保真，不调用 importer、不重试、不重读正文或另一身份库。新 not_found 分支仅在现有 receipt 边界一次核对 schema/request/provider/FY-Q、严格整数零候选和正常 exit；错误消息不获得合法 cutoff。JSON schema 为数组/对象时同样具名拒绝、保持用量，不抛出吞诊断异常。
- 请求/结果版本 `/1`、`/2` 和 discovery `/1` 不升级；成功/既有失败 goldens 字节不变。没有新增许可证、人工签收或生产完整合同的第二次验证。

## 实际 TDD 与集中节点

| 节点 | 结果 | 证明范围 |
|---|---|---|
| ET 正规业务 RED | 5 FAIL / 6 PASS，1.58s | 已存在 API/真实 worker 返回 not_found，但原因缺失；无缺文件/import error |
| FF 正规业务 RED | 23 FAIL / 8 PASS，1.09s | 实际 transport 状态错误和合法 not_found 消费合同拒绝 |
| FF receipt 绑定 RED | 8 FAIL，1.03s | 错消息/候选数/非零 exit 被误接受；真实 production 路径 |
| FF schema JSON 类型 RED | 2 FAIL / 1 PASS，0.95s | 数组/对象类型异常丢用量的具体反例 |
| **最终 ET 集中责任节点** | **56 PASS，40.37s** | API、CLI→supervisor→真实 worker→API、两个 provider、3 个受影响 batch metadata 控制 |
| **最终 FF 集中责任节点** | **134 PASS / 4 SKIP，1.90s** | transport/envelope/orchestrator、正常 missing、命名 cutoff、真实用量与既有失败回归 |
| ET golden / lint / diff | 10 matched；PASS | 旧 wire 冻结与窄写集卫生 |
| FF lint / diff | PASS | 最终两产品文件、三责任测试 |

原 40 PASS/1 FAIL/164.62s 的矩阵 attempt 和只读 diagnosis 全保留。FF 先前 124/4、132/4 集中结果及所有 RED/GREEN 不覆盖，最终依据 **concentrated-final2**；不是从中间绿灯推断最终产品已通过。增加测试只为实际发现的 receipt/type 风险，没有重复全量或原41矩阵。

### 4 个 SKIP 的具体边界

三个 W07 测试要求显式真实 ET tool 路径：HKEX/unsupported_market、NASDAQ/provider_credentials_missing、TOKYO/unsupported_exchange；一个真实 CWP import/replay 要求跨仓 source checkout。当前隔离责任测试不设置这些可选路径，所以 SKIP 不是 PASS。ROOT 的原41真实三层离线矩阵另负责完整联调；本线没有声称这四项已跑，也没有声称真实 FMP 权益、外网/OCR/LLM或收入模型认证。

## 冻结与接口

统一 [product-freeze.json](product-freeze.json)，schema `root-w06-cutoff-product-freeze/1`，8 项 `files=[repository,path,sha256,bytes]`，含两 TREE、只读 head_before/head_after、旧作者冻结、旧 goldens 和工具保留证据。

- ET TREE：`C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root`，HEAD 前后 `c91f5f54bc2a24e7b5d6e648dba3f9d578f5fa52`；产品 `transcript_api.py`、两责任测试。
- FF TREE：`C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root`，HEAD 前后 `88997b85ce5be20dc3d563b5c040706590df6dbb`；产品 `scripts/transcript_tool_transport.py`、`scripts/et_v2_contract.py`，三责任测试。
- 统一 freeze SHA：`e13ee23e64e0ec720edce6e4f5c6847f0dea2ead17a8d112d63874cd0e4cf28a`。
- FF 最终作者 freeze：`ff/product-freeze-final.json`，SHA `a235b0c2c25f6c52a6402dd160737f2ec6ffa10309c368ee6eb06fbdc332cf4f`；旧 `ff/product-freeze.json` 保留为历史记录。
- 实测原工具合同 **205** 文件、FF 基线保护 **354** 文件、ET 旧 golden 目录 **12** 文件、FF 旧 golden/ET合同 fixture **18** 文件 SHA 全未变。

## 资源、恢复和 PWF

各责任执行使用平台必要环境白名单、合成 HOME/TEMP/fake key、socket 拒绝、无自动第三方 pytest plugin；0 真实 key/config/raw 读取、0 外网/provider/LLM/费用。我的7个 ec-/fc- 短 scratch 均恢复不存在；FF 作者的自有 scratch 也已恢复。现有原件/文件/空目录不删除，无完整数据湖备份或恢复演练。

每树自身 `.planning/w06-cutoff-result/{task_plan,findings,progress}.md` 和 `docs/handoffs/w06-cutoff-result/` 已更新，母 PWF、作者冻结工具和其他 owner 文档只读。CWP 来源12文件的另行发布/type标注由 ROOT 管理，本线零写，不拿旧 CWP 冻结 SHA 约束 ROOT 后来的正常发布。

**ROOT Next Step**：使用本统一 freeze 的 ET/FF 树与 ROOT 另冻结的已验 CWP 树，原 CaseSpec/fixture/request/期待和 30s/180s 上限不变，只做一次完整41回放；随后一次非作者范围验收、正常并线提交/推送和必要定点安装同步。本线作者 STOP。
