# DU5 接口、隔离与统一交接 / 1

这是工程交接说明，不是许可合同。已有资料处理授权沿用；本轮外包默认离线、0 供应商调用，不需要另建 authorization/receipt/canary 放行系统。原件、密钥和生产配置不得变动，API/费用工具由 ROOT 沿现账本负责。

## 开工方式

1. 只在卡上指定的全新工作目录运行。先读本目录 task_plan、施工卡和本文件；核对 branch、base、`git status --short`，不要清理解释不清的别人的文件。
2. 工作树仅复用已提交 Git 对象，不继承主目录未提交 alert/output/密钥。不要复制 companies、原始 PDF、AUTO 或整个 .planning。不要全局 `pip install -e .`，避免将其他 harness 的 import 指向这里。
3. 先列本卡实际文件与现有测试；结构查询优先 CodeGraph， literal 搜索用 rg。无索引时按仓 AGENTS 处理，不把缺索引当代码不存在。
4. 日常只跑本包快测；B/C 跑一次相关集中回归与实际 CLI。不把慢 native/全仓/付费套件挂入每次 commit。已有 normal hooks 保持，不在本卡升级 CI。

## 数据接口

### CWP benchmark → ROOT

沿用 `du-gold/1`、`du-observed/1`、`du-evaluation/1`。`sample_id` 由作者选择，统一 `du5-` 前缀；原始 SHA/原文 locator 按现 loader 验证。新 metadata 如 split/freeze/阅读范围写现有允许字段或自己的 manifest，不擅改公共 schema。原文打不开和无法观测分别给 UNAVAILABLE/NOT_EVALUATED，不制造空正文与假召回。

金标先于该样本候选输出冻结。独立作者只能证明自身未用候选调金标，不能保证所有历史模型从未见过公司；诚实记录已知 prior use、抽样范围和冻结时间。所有旧分母/状态保留，新样本单列；改错金标需单独更正记录和版本，旧值仍可回放。

### AUDIT → ROOT

使用调用方显式提供的产物映射，原 ID/hash/locator 保持；不发明 v4 传输格式。最小输入含 run/attempt、版本、来源片段定位、实际 selection、逐 claim 的 support/context、来源侧目标报告、输出侧独立审查报告。无 hash 可由现 EvidenceReader 实读并报告 observed SHA，不新增缺 hash 阻断。原件身份/期间验证不在这里重复实现。

审查包输出应明确区分 `reference_resolved`、`semantic_verdict`、`target_coverage`、读取范围与 unknown。程序不凭正则自动签发自由文本语义 PASS，不自己生成 reviewer verdict。前后比较绑定同一冻结目标集，新增目标、消失 claim、版本变化、不可比项单列。

### RF → ROOT

保留 `rf-input-quantity/1` 形状和现函数旧调用方式。新货币/尺度只是有限词汇扩展，同币缩放与跨币 FX 严格分开。单位描述由唯一责任层导出/解析，sensitivity consumer 使用它核对真实 parameter；不在多个调用处重建平行单位表。详细端口与测试见 RF 卡。

## 独立测试环境和空间

- 测试输入只读；输出放自己创建的 TemporaryDirectory/tmp_path，保留测试前 sentinel，正常/错误/超时都恢复初始内容。只删除本次明确拥有的临时目录，不做全备份恢复演练。
- 已有真实原件通过现有 bindings/reader 只读取得；不为方便复制全文进夹具。可存最小必要原语言摘录，标 synthetic/real，保存真实来源映射。缺资料就报告，不能猜。
- 每包保留首个行为 RED、最终集中结果和一次 CLI/E2E 收据；优先 JSON 汇总和压缩原日志，交接证据目标不超过 10 MiB。若达不到，解释具体内容，不用删失败或裁掉证据来凑上限。
- 不打印环境变量/凭证；不提交 API key、本地绝对原件 binding、AUTO DB 或下载文件。源码、测试、计划按正常 Git 提交。

## 仅三个大节点与交付

A：读实际代码/历史记录，先写正确行为反例。新文件 import RED 不能替代真实语义或机制反例。注明假说、已复现缺陷、已有正确行为，不把设计推测写成事实。

B：共同根因实施、一次本包与关联集中测试；只修本卡责任层，不以删断言、提高预算、特判公司或跳验真掩盖问题。

C：实际公开 CLI 与恢复测试、集中静态/独立质量核对、正常 commit。交付后 STOP，不合并主线、不安装技能。ROOT 在原有大节点统一接收。

自己的 PWF 内交付 `handoff.md` 和 `handoff.json`：

```json
{
  "schema_version": "du5-handoff/1",
  "card_id": "DU5-CORPUS|DU5-AUDIT-SUMMARY|DU5-RF-UNITS",
  "base_commit": "full40sha",
  "branch": "codex/du5-...",
  "implementation_commits": [],
  "changed_paths": [],
  "entrypoints": [],
  "interfaces_reused": [],
  "red_receipts": [],
  "tests": [{"command": "...", "exit_code": 0, "passed": 0, "failed": 0, "skipped": 0, "receipt": "relative/path"}],
  "fixtures": [{"path": "relative/path", "sha256": "...", "kind": "synthetic|real_excerpt|real_original_binding", "scope": "..."}],
  "independent_review": [],
  "old_failures_preserved": true,
  "not_run": [],
  "known_limits": [],
  "root_integration_steps": [],
  "production_writes": 0,
  "supplier_calls": 0,
  "cleanup_receipt": "relative/path"
}
```

`production_writes=0` 指生产原件/配置/AUTO，不是禁止本卡源码修改。commit 后可用单独 handoff commit 记前一实施 SHA，避免在同 commit 内自引用最终 SHA。失败/未知照实写；不能因形式齐全宣称生产已改善。
