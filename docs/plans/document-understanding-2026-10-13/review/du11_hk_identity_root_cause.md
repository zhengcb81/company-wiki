# HK 来源复用身份表示不一致：根因与实施边界

## 结论

这次失败由同一个证券代码在三层使用不同表示方式引起。原件清单保存 `HK / 9896`；官方身份快照返回 `HK / 09896`。CWP 查询按等价代码匹配成功，但 public candidate 返回原清单的 `9896`，FF 随后把它与 `09896` 再做字符串全等比较而拒绝。财年、as-of、原件 SHA 均不是本次失败点；FF 两次调用、零下载。

具体链路：`fetch_filing.resolve_filing` 使用已核身份的 `09896` → CWP `SourceResolver._identity_matches` 去前导零匹配 → `SourceReader.describe_candidate` 返回观察值 `9896` → FF `validate_source_candidate` 的 `handle[field] != company_identity[field]` 抛出真实错误。`validate_handle_metadata` 的日期/SHA/大小约束与此问题无关，应保留。

## 同一责任层的修复方案

由 CWP 来源身份层拥有一个纯粹、按市场定义的严格证券代码表示/等价函数。resolver 的严格匹配与 public SourceCandidate 的身份投影共用它；FF 消费同一个规范化投影，不另抄去零规则、不增加一次身份 RPC。

推荐将 SourceCandidate 的身份字段明确为规范化的匹配身份，`describe_version` 和 source facts 保留忠实观察值。不得按请求覆盖来源事实。若既有候选契约明确要求字面观察值，则改用显式 canonical 身份投影并加兼容测试；不要只在 FF 放宽字符串比较。HK 数字代码可按五位统一，CN 使用已有市场宽度规则；US/class ticker/未知命名空间不能被无市场限定的去零或去标点合并。当前 resolver 的无市场 `lstrip("0")` 也应纳入同根整理。发现查询别名的宽松 `_ticker_key` 不等同于严格来源身份比较，不可不加区分直接套用。

不增加登记库、缓存、人工许可、供应商或公司特判。缺失/冲突字段按原 owner 规则处理；原件 SHA、SourceRef、期间、publication/as-of 仍由原责任层校验。

## 集中 TDD 与验收

1. **A RED：** 多个 HK padded/unpadded 两方向、不同代码、不同市场；CN 六位和 US 类别符号反控；unknown/conflict；query/resolve 一致；candidate 规范化但真实 manifest 不变。
2. **B 实现：** 一个 CWP 纯身份 owner，两公共入口与候选投影使用；不把来源观察值改成请求值。
3. **C 离线端到端：** 使用独立 Temp 的合成原件与真实格式身份快照，走 FF→CWP identify/query/candidate/open。两种 HK 表示都应 reuse，下载/provider/model 调用为零；错代码、市场、期间、未来日期、unknown publication、原件篡改仍按原契约拒绝/明确 gap；核对 SourceRef/字节 SHA 不变。测试前后 sentinel/目录清单/哈希完全恢复。

无需再跑模型或读取真实原件来证明此缺陷。修后真实三公司 C 的消费者节点再统一复验，不把目前摘要/恢复已通过误报为全链 PASS。

## 并行边界

FF 外包作者正在拥有四个 transcript 模块、`tests/test_du11_transcript_reuse*` 与其计划，均不触碰。实际报错模块 `scripts/ff_source_candidate.py` 在作者白名单外；优先通过 CWP 规范化公开投影使现 FF 严格比较自然成立，FF 仅补集成回归。若必须改 FF 契约，由 ROOT 在冻结版本上统一处理。当前仅诊断，不实施。

## 证据与局限

真实收据：`live-v5-hk-a8eef273-20261018/ff-reuse.stdout.json`、`registered-source.json`；官方 snapshot 过滤该公开代码记录；所述函数实际源码。没有运行新测试，没有读取密钥/原 PDF，没有网络/收费调用。FF 主仓与 Projects 祖先无 AGENTS.md，已读主仓 SKILL.md。具体文件路径、测试矩阵和证据值见同名 JSON。本报告不宣称契约兼容性已通过；须由上述 TDD 建立。
