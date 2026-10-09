# W05 transcript snapshot 修复独立集中复审

结论：**通过本次冻结的 snapshot ownership 修复范围**。原 W05-CACHE-R1 的外部可变引用问题已由构造时深快照统一修复，没有增加重复全文解析、人工门禁或降低原件验真。本结论不代替整家公司 M3、catalog/StockWiki 消费接口或后续主线发布验收。

## 版本、范围和源码审查

- 源码：`146491aeeeacee9d01dd10d4ae7ee91a2b790bf7`；审查工作树 HEAD/PWF：`20be9dfc942abb71e41dfedb93a180e800dc0e67`。
- 工作树：`C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki`。
- 本次实现 delta 只有 `narrative_retrieval.py` 的 deepcopy import、构造时 `deepcopy(dict(record))` 和明确 ownership 的 docstring；另有六个参数展开后的 ownership 测试及自己的 PWF。没有重写 parser、selector、SHA 或 locator 校验。
- 已读取原独立 `transcript_compat_review.md`、作者 handoff、真实 snapshot RED/修后记录。旧 FAIL 和初稿证据均保留。

接口语义清楚且合理：一个 resolver 消费创建时的独立来源记录和路径映射，外部随后修改的是未来 reader 的输入；旧 reader 不接受变更后的合同。缓存保存原合同的解析结果，每次 resolve / resolve_group 仍实读原件 SHA。深快照覆盖嵌套 contract、parser_options、evidence 文本、locator 和身份字段，避免逐字段 cache key 或重复解析。

## 独立实际复验

集中责任集 **16 PASS / 1.18 秒**，含新增六个 ownership 情形、已有版本/文字/SHA/locator/格式六个合同拒绝情形，以及原件 SHA、伪 hit locator、伪文字和未知 selector 四个旧守卫。没有跑 208 或全 suite。关闭可选插件自动加载产生的既有 `asyncio_mode` 配置 warning 不是产品失败。

另外独立建立合成 TXT、生产 parser/selector 生成的包和真实 search hit，执行 **17 个控验全部通过**。控验源码、实际 argv、每项有限拒绝原因、源码 SHA 和清理事实都记录在 `transcript_snapshot_re_review_receipt.json`；模块加载路径强制核对属于上述工作树，避免误用 MAIN editable installation。

| 独立控验 | 实际观察 |
| --- | --- |
| 创建 reader 后、首次读取前修改外部输入 | 八类变更：未知版本、合法版本错声明、文字、文字及同步伪 SHA、locator、source SHA、selector、parser_options；旧 reader 的 resolve 与 resolve_group 仍返回原正文/0.2.0、内部记录等于原快照；清空外部路径映射无影响 |
| 首次读取后修改同样八类输入 | 旧 reader 重复 resolve 与 resolve_group 等于首次结果；不是“变更合同获准”，实际内部快照仍是原合同 |
| 新 reader 消费变更后的输入 | 上述 16 次都按具体已有校验拒绝，包含 supported version mismatch；没有只对 9.9.9 作特判 |
| 解析和 SHA 实际调用计数 | 每个旧 reader parse 只有一次；首次读取前变异情形两次读取共三次 SHA，首次读取后情形三次读取共四次 SHA；每次读取都核字节，首次 replay 多一次前后核对 |
| 命中缓存后同长度修改真实 raw 字节 | resolve 与 resolve_group 都拒绝 `raw source SHA-256 differs from bundle`，没有重 parse 来掩盖缓存复用 |
| 恢复 raw 的精确字节和 mtime | 同一 reader 再次 resolve / resolve_group 等于初始结果、仍只 parse 一次；合成原件 SHA/mtime 恢复 |

真实 MSFT 的先前独立 41-span 验真与作者最新 41/41 snapshot replay 已读，不再次重复整份真实解析。本次独立实跑针对新增缓存 ownership 和保持每次原件 SHA 的责任，其证据不借用真实 MSFT 的非变异回放来抵消原 RED。

## 清理与限制

四个审查源码/test 文件前后 SHA 相同；没有源码、共享 PWF、CI/hooks、生产配置、安装目录或生产原件改动。所有本次 owned TEMP 不存在，网络和付费调用均为零。

沙箱初次 `git -C` 调用在 TEMP 创建前失败，改为 subprocess 显式 cwd。随后首轮 16 测试已通过，但平台沙箱 TEMP 在写独立控验脚本/清理空目录时拒绝访问；该空 owned 目录先解析核对精确绝对路径再由原生 cmdlet 删除。最终复验使用获准的显式独占 Windows TEMP，完整控验及清理均成功；这两次是运行环境问题，未据此修改产品代码或降低测试要求，receipt 明确保存说明。

本次 reviewer 仅写这份报告和 receipt，不提交、并线、推送或安装。MAIN 可继续既定大节点发布验收；不需要另增小节点签收。
