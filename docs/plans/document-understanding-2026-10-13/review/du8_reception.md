# DU8 接收与根因修复

当前状态：**AUDIT 已验收并本地并线/技能同步；FF 工程已并线推送，完整矩阵 C 仍 OPEN**。日期：2026-10-16。

## 边界与作者交付

| 包 | 作者冻结 HEAD | ROOT 接收工区 | 当前结论 |
|---|---|---|---|
| FF MATRIX | `6f381199f146109b4f517537a70da1c20c6e05bd` | `C:/Users/郑曾波/Projects/filing-fetch-du8-integration` | 工程验收并线/推送 `c7c8867d`，ROOT 修复 `41f49882`；C 未通过 |
| AUDIT MEASURE EVIDENCE | `3ed248df06b2ba00e4f59d930647149ecc1f88af` | `C:/Users/郑曾波/Projects/revenue-forecast-audit-du8-integration` | 本地主线 `a2f216bd`，ROOT 修复 `7ea6071b`；两份安装技能 MATCH，无远端 |
| RF COMPARISON | 外包施工线 | `revenue-forecast-du8-comparison` | 仍 IN_PROGRESS_EXTERNAL，未接收、未改动 |

作者工区只读保留完整提交历史。ROOT 不进入 DU9 排他白名单，不修改 Dayu、真实原件或生产配置。FF 主仓未跟踪的密钥文件保持原样，不读内容。AUDIT 无远端，不擅自创建公开仓库；验收后本地并线并定点同步其单技能。

## AUDIT：实读和比较必须由同一责任层接通

独立原版源码审查有 2 P1 / 3 P2：JSON 浮点解码丢精度；坏项及重复 ID 从覆盖分母消失；字段指针绕过调用者限额；缓存绕截止时间并重复解码/二次扫描；非法映射 digest 仍可干净 MATCH。

ROOT 的另一组实际反例还证明：账本对象与传入字节不是同一内容、同目标不同字段/哈希的绑定冲突、A/B/A 冲突复活、非法指针借回退定位成功。原始 RED 保留在本地接收证据，不覆盖。

实施顺序：

1. 先保存可复现 RED；在既有 `EvidenceReader` 中统一精确结构值、字段定位、缓存和截止时间，复用同一个预算，不在适配器再写解析器。
2. 适配器保留所有声明项的覆盖分母；坏项/重复项显式诊断，不能被筛掉后宣称全量相符。绑定冲突必须保持冲突，不随后续重复恢复。
3. 保持旧数学检查和默认 CLI 的行为。`bytes_verified`、`declared_field_match` 和恒为 false 的 `semantic_source_truth` 继续分开；不引入许可或发布门。
4. 最终冻结源码后由另一独立 agent 复核，再做一次相关集中测试、实际新旧 CLI 和清理核对；正常提交、并线、单技能定点同步。

初步 ROOT 修复后的全套结果是 **621 PASS / 1 FAIL / 2 SKIP**（138 subtests），不算最终通过。唯一失败涉及作者新增测试把不同字段的重复绑定当作缓存重复；必须按冲突契约判断是用例错误还是实现错误，不能通过放松冲突校验处理。

最终结果：已由共享 `EvidenceReader` 负责精确 JSON、指针、缓存及截止时间；坏/重复声明全保留分母，冲突保持冲突，逐行字段聚合不再二次扫描。原作者缓存测试改为完整深复制同一绑定，保留原错误断言/RED依据，未放松冲突检查。完整 unittest **620 PASS / 2 SKIP，91.330s**。该快照之后独审发现复合 locator 的 null 回退未归一化，先保存两个实际失败子例，再复用既有 `split_locator` 修正一处接线；最终 **59 PASS / 15 subtests，7.49s**（全部 ROOT 25 项、unittest 未发现的 pytest 参数化 17 项、新旧实际 CLI 17 项），不把重叠数量相加或称同一版本全套。另一独立 agent 最终核对 13 个 SHA、8 个实际控例 PASS；旧 REQUEST_CHANGES 报告保留。

完整作者历史和 ROOT 修复已并入本地 main `a2f216bd8cc8e3ed430c60ee27bdd309dabd8a17`，主树干净。`.agents`、`.claude` 每份只新增/替换本包 5 个技能文件，全部 38 个包文件核对 MATCH；其他内容保留。AUDIT 没有 remote，未创建或宣称推送成功。新增诊断仍是可选报告，不是人工许可/发布门，也不证明经济口径真值。

## FF：分别证明边界正确和覆盖完整

作者现有调度相对保存的旧 41 例真实表只节省 **1.5226 秒 / 2.02%**，不宣称成倍提升。作者 C 的三次记录分别含未跑项/部分完成，清理后没有保留全部原始证明材料；ROOT 需独立保留本轮证据。

ROOT 已单独实际跑过一次：**20 PASS / 0 FAIL / 4 PARTIAL / 17 NOT_RUN，173.27s**；仍保留原 30/180/2 workers 与 10s proof reserve。209 文件共 1,151,019 bytes 的完整 report/请求/响应/fixture/guard/restore 证据保留；scratch/bytecode cache 删除、既有 sentinel/生产 metadata 保持。原 oracle 仍明确非通过，不能因 0 FAIL 就称 41 例成功。没有重跑到绿。

观测到 197 次 Python boot、35 次 FF CLI parent call；binding 15.54s，seed 两组累计 61.66s，FF CLI 两组累计 241.93s。并发 span 的累计秒数不可相加当墙钟耗时。静态分组无法解决这部分重复启动/准备开销，下一轮需在实际启动路径定位与消除重复成本，再证明固定输入、超时/清理与来源读取等价；不是继续改调度权重或增加时限。

实施顺序：

1. 实际 GET 已发生的 provider deadline，与冷启动先耗尽 deadline 分开记录。后者可以证明有界退出，不能证明处理中超时已经覆盖；不能简单把 GET 断言改成 `<= 1` 后算全 PASS。
2. 中断恢复夹具只认自己的唯一 attempt 和真实 case/GET 证据；旧 attempt、准备期文件不算开工证明。不能把进程观察失败当作零泄漏；保留已有 sentinel，核对两次尝试各自恢复。
3. 重建三份实际损坏的 UTF-8 交接文档，保留原 Git 字节和修复依据；修正过度表述。
4. 窄测试通过后，在无其他重测试争抢资源时串行进行一次固定 **41 例 / 2 workers / case 30s / batch 180s / proof reserve 10s** 实际 FF→ET→CWP 矩阵。保留结果、阶段耗时和恢复/清理证明。不提高上限、不删 case、不反复重跑到绿。
5. 独立审查最终 SHA 后正常提交和并线。若 C 仍未完成，已验证的工程可独立并线，C 保留具名 OPEN，不能把工程接收写成完整矩阵通过。

最终工程结果：**251 PASS / 9.19s**，独立最终审查 0 P1 / 0 P2。恢复 observer 进一步修正为当前 proxy state 与本 attempt 的零→新增 GET 观察，初见累计 GET 不冒充本次在途；仍不声称准确杀进程瞬间 provider 处于网络阻塞。真实受控本地进程树进入/回收测试已通过；**完整矩阵被中断后重启恢复仍 NOT_RUN**，与全量 C 一起开放。

正常提交、完整历史并线和推送至 FF main/origin `c7c8867da35cd19d4f419fa70947332615e8e9c0`；正常 pre-push 静态/契约检查通过，行为 **754 PASS / 7 SKIP / 78 subtests，87.73s**。只核对未跟踪密钥的元数据未变，不读内容、不提交。精确远端 [quality CI](https://github.com/zhengcb81/filing-fetch/actions/runs/38977822228) 已观察 **SUCCESS**（22:48:51 UTC），不把CI绿当完整41例通过。

## 证据、空间与后续

本地工作证据：`.planning/shared-reading-production/du8-reception/`；发布时提取小型可复核收据，不提交真实原件、密钥或大响应。本轮供应商调用和新增财报原件副本均为 0。

CWP 原生表格整改另有冻结 **190 PASS**，ROOT 再独立复放生产路径 **17 PASS / 2.61s**，临时根/配置核对通过。最新真实 VRSK/MSFT 分别消耗 1,989,140/2M 与 1,035,473/2M，每份一次解析、0供应商、不耗尽、原件/配置不变；仍不代替真实摘要质量验收。母计划的默认深页、正式配置摘要、历史错引和 holdout 仍 OPEN。
