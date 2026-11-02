# R7 ROOT / invest 大节点独立审查 R2

结论：**PASS_ENGINEERING_SELECTED_SCOPE**，本轮实质 P2/P3 已闭合。最终绑定 `R7-ROOT-freeze.json` SHA `aa75d7159c0f6ecf150394e962488172b2de46cb2cd6d35684e84230496fbe86` 的 17 文件；报告前逐 SHA 匹配。reviewer 不审自己的 tooling30，不改 ROOT 产品/测试/PWF/Git。

R1 的 `1F9P/1.26s` 失败报告原样保留，链接为 `R7-ROOT-independent-r1.md/json`。本轮只核新增差分，不把旧结果冒充新版本整套运行。

## 实质问题闭合

**R7-ROOT-A01 / P2**：原 precommit 取得暂存文件名，却编译和 Ruff 检查工作树内容，可把坏的 index 版本放行。ROOT 已改 `git show --no-textconv :0:relative` 读取实际 index 字节，原地不 stash/改 index/worktree；自有 staged 树提供一次真实 Ruff，并保项目配置。

独立增量 **3P/1.69s**：原始 RED、stage 好/worktree 坏的真实 Ruff 正控、只有 stage 存在 F821 的真实 Ruff 负控。临时仓含中文/空格路径，运行前后 index/worktree 字节一致，暂存快照目录结束清理。未增加全树 clean、人工许可或签收。

**R7-ROOT-O01 / P3**：invest 重复前置 binding 已删除，只调用强 RF owner。强入口内部仍先 `verify_input_binding` 再完整重算；旧 dispatcher 不会把无 bound input 的当前 schema 当可用。

相邻三跳 forged input、未签正常结果不升格、经济输出篡改反控 **3P/2.30s**（总3.376s）。该次 RF80源码与四 WIP 前后未变；没有重跑整投资 suite 或固定快检。

## 上轮通过且相关字节未变的范围

- 独立 9 项 passing controls：大 JSON 不截正文/trace/必需 ID，False/None 保原值；173 层树完整、真正循环不完整；meaning/heading/physical proof 分离且重叠不丢，未知 scope 不自动 actor PASS；真实 fsync/编码错误保原 checkpoint；两类 late writer 不覆盖外来文件；大日志保真实0/23。
- 一次真实 fixed Git fast gate：**Ruff +21P1skip/1.82s，总2.716s、exit0**。没有 implicit deploy、整套 suite/E2E；caller registry 哨兵不变，自动 smoke index 结束已清。该次 RF80 Python SHA 和四 WIP 均未变。完整收据留 R1，不制造重复运行。
- 未签结果只记 `unattested_observed`，不冒成 signed/verified；不可重建索引不再否决自足且强验证通过的结果；来源/身份/期间/币种/单位及经济重算仍由原 owner 负责。

ROOT observer 源码在 R2 没变；本轮实际只追加 index 缝与 strong-owner 归并的有限验证。两次消费运行之间 RF 作者窗口曾释放，每次都有自己的稳定指纹，不把中间正常修改写成“全程未变”。

## 范围与清理

可进入 ROOT 工程集成/正常发布节点；仍受其他工作线与既有 CI 结果约束。本审查**不签真实 H1、正式摘要、缓存恢复、RF 经济采用或整个目标完成**。真实原件/来源执行/模型/收费均为0。

自有 UUID tmp `tmp/r7v-84d3dd` 初始 absent；原始探针、增量探针、JUnit 和消费窗口收据已保存在 JSON，已完成精确绝对路径/无 reparse 检查，清理105文件、195,693逻辑字节并恢复 absent；清理后17文件 SHA 再核相同。STOP。
