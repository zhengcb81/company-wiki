# R7 工具门禁系统精简实施交接

状态：**IMPLEMENTED / FROZEN，待独立大节点审查与 ROOT 集成 CI**。不是自审签通过，也没有宣称真实 H1、正式摘要、缓存恢复、RF 经济采用或全项目完成。

冻结清单：`R7-tooling-freeze-manifest.json`，30 个代码/测试/当前 README 文件，SHA `1dc7488c5fb8a89b0c0da15ab94097f2b177167789972125d227f7d29ea52e91`。报告生成时逐项复核同 SHA；源代码已停写。ROOT 的 source_case 工具、CI/hooks、主 PWF、生产配置、其他 agent 的源码和其他仓库均未修改；没有 commit/push。

## 实施内容与单 owner 边界

| 共因 | 实际行为变化 | 保留的真实失败/预算 |
|---|---|---|
| 工程日志体积否决 | `_bounded_process` 新增仅诊断使用的 `log_tail=True`；pre-push 选择它。两流持续 drain，deque 仅保尾部和实际累计字节；日志大不杀子进程、不改成 125 | 默认 JSON/payload 仍按原 cap 严格；实际非零退出、共享 deadline、子孙进程回收和输入错误保留 |
| Phase C prepared/generation/capsule 固定大小 | 取消 2MiB/512KiB 等表示上限，完整 gzip checkpoint 保留原始字节/SHA与不可覆盖语义 | 错来源/字节/版本、改过历史、路径逃逸仍错误；原 owner 真失败原样抛出 |
| 观察器异常污染业务结果 | `original_prepare` 在 callback 外只调用一次；capture/event I/O/编码异常独立记 `observation_status=incomplete`、owner artifact/status、checkpoint stage 和 error type，再返回同一 owner 结果 | 无法写 event 时明确 `event_saved=false`，内存记录及 stderr fallback；不声称 checkpoint/结果已保存，不触发重做 owner/重复费用 |
| identity、G2 replay、portability 完整报告 | 删除 receipt 16MiB、report 8MiB 的输出否决 | identity 请求/实际工作界限和来源七项检查保留；非 JSON/实际 I/O 不伪报保存成功 |
| footprint / RAW-DUP | 取消报告字节、明细行、错误/跳过路径条数和文字截断。完整已观察证据落盘；旧 Python `max_bytes` / CLI `--max-detail-rows` 为兼容接受，不裁资料 | 文件数、实读字节、deadline、partial/未知分配量、原件/未知旧输出保护保留。RAW-DUP JSON/写失败将 `written=false` |
| cross-market 观察投影 | 保留全部文档、错误、job、reservation 和 parser metadata，不再 32KiB/9 项裁掉 | 仍只选元数据字段，不复制原文/提示；数据库未知不造成功、非法 JSON 不接受 |
| holdout 全树 clean | 一次 Git status 仅作诊断，失败为 unknown；不因无关 WIP 拒绝。worker 在运行后记录实际加载源码路径/SHA/bytes | 错显式 HEAD、错 import/runtime 根仍拒绝；样本与 gold 未修改 |

没有引入新的报表框架、授权 JSON、manual receipt、canary 或索引库。兼容 report 字段/函数名保留，但不再成为输出许可。三个当前工具 README 已与新规则对齐。

## 为什么保留 explicit producer commit 匹配

已追实际调用：`tools/holdout_replay/__main__.py:40` 的 `--producer-commit` 是**本次请求 required 参数**；`:125` 直接传给 runner，runner`:107` 在读取 manifest 前核实际 HEAD。不存在从冻结 `manifest.base_code_commit` 自动取旧引擎并要求新 HEAD 一致的路径。

因此保留的是“不跑错用户本次显式请求的版本”，不是冻结旧引擎。新引擎可对同一原样 sample/gold 重跑，指定新 producer commit 即可；不用改 gold、重签收或清空其他并行工作。WIP 路径和运行后代码字节单独记录，不把它们伪称为该 commit 的原始字节。文件身份是运行后观测，不冒称任意时刻不可变的执行内存证明。

## TDD 与一次受影响集成

所有运行使用正常宿主 Python、自有短 tmp 和合成资料/临时库/Git；没有真实公司原件、下载、模型或收费请求。

| 实际运行 | 结果 | 说明 |
|---|---|---|
| 新策略首轮 | **16F / 2.65s** | 日志、完整 checkpoint/report、旧体积/行截断、身份输出和 dirty-tree 均真实 RED |
| 同一组第一次实现 | **16P / 4.24s** | 中间版，不冒签最终全部代码 |
| owner 成功后 observer I/O/编码隔离 | **3F / 3.18s** | 原 callback 确实会污染 owner 返回，先留 RED，再修 |
| 一次受影响集成 | **211 例：208P / 3F / 2 warnings，144.67s** | 覆盖实际 JSON payload cap/子孙回收/超时、Phase C、identity、跨市场、两存储工具及 holdout 边界；未超时，没有猜性能根因或提高 timeout |
| 仅补失败与必要反控 | **7P / 4.66s** | 3 失败、2 CLI 编码 warning 控制、2 JSON/I/O 不伪 `written`；无 warnings，没有重跑 211 |
| 静态 | **27 个改动 Python 的 Ruff 绿；mypy 1 源绿** | 唯一 src 改动 `_bounded_process.py` 的 SHA `25dc804ddcbb15428238862d2c6a1b46958f96e9add12c96a4b339305c6743d9` |

211 域的 3F 不是靠更改业务 oracle 消掉：

- 两例为迁移 noisy-child 测试时写错 `\n`，真实子进程报 SyntaxError；正确转义后仍真实调用子进程并保留成功/失败断言。
- 一例为旧测试直接扫仓内静态夹具，已有 `__pycache__` 被算为第八个文件。现在按手工声明的七个固定输入复制到测试 tmp，原 fixture 全树前后快照不变；**没有删历史缓存，也没教产品忽略 cache 文件**。
- 两项 warning 为 child 本地默认编码与 parent UTF-8 不一致；CLI 测试环境明确相同 UTF-8 编解码，不改报告事实、实读限额或只读断言。

正确说法是：211 域的三个已定位失败已定点闭合，另新增两个 JSON/I/O 负控通过；**不是捏造一次最终 `213P` 全组运行**。完整历史 case 身份、原 JUnit SHA、可保留的 JUnit/控制台在同名 JSON。首轮失败测试曾让 pytest repr 带入继承的环境 dict，报告不复制该 repr，测试已改成只记录布尔选项，避免环境值进入断言输出。

## 旧测试政策迁移的边界

用户取消任意表示门槛，故旧“超过输出大小必须失败/截断”的期待显式改为完整保留。wrong source/hash、错误 generation/历史替换、unsafe path、真正预算耗尽、非零退出、超时、原件前后不变和 unknown output 不覆盖等原负控保留；不改公司/行业 gold，不放宽 source 事实资格。

## 清理与剩余工作

`tmp/g7` 初始 absent。已归档必要测试收据后按精确绝对路径清理 **1,074 文件、82,965,510 逻辑字节**，现恢复 absent。首次清理因 guard 发现一个测试创建的 junction 而停止；随后确认 link 和 target 均在 g7 内，只 unlink junction、不递归跟随，核 target 元数据不变，再清理自有 root。仓内历史静态 fixture 缓存保留。

ROOT 接下来只需对冻结 30 文件做独立大节点审查与既有集成 CI；不按小点增加签收，不重复此 211 域。本交接不覆盖真实 H1/摘要/cache/RF 采用，继续由主 PWF 执行。
