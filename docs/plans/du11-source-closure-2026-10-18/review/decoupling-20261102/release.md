# D3发布与增量验收

> 2026-11-02后续全面复核：已发布成果与测试事实保留，但六项真实入口/边界遗漏使全面完成声明不成立。当前以[复核和D4细则](../decoupling-recheck-20261102/README.md)及CURRENT_STATUS为准；业务模块暂不派发。

**D3已完成。** [独立工程验收](independent/review.md)通过，正常提交、推送、部署和相关远端CI已核实（2026-11-02T21:50:39.370275+00:00）。没有提前派发RF/AUDIT业务卡。

| 仓库 | 版本 | 发布与验证 |
|---|---|---|
| company-wiki | `a03d0c0296496eeb8aac23fa0ed3774f2b31abcf` | master，[Source system integration通过](https://github.com/zhengcb81/company-wiki/actions/runs/41531674700)；原生产源码`3d822c41`的[普通CI](https://github.com/zhengcb81/company-wiki/actions/runs/41528855117)和[组合CI](https://github.com/zhengcb81/company-wiki/actions/runs/41528854781)也已绿。随后只改测试归属/路由，源码与普通测试未变。 |
| revenue-forecast | `ad178dbcc4c407c1006659c537b09d88728b5af9` | main，[quality通过](https://github.com/zhengcb81/revenue-forecast/actions/runs/41529763715) |
| filing-fetch | `508aba308cf5206c486119c446b66172debdc09a` | main，[quality通过](https://github.com/zhengcb81/filing-fetch/actions/runs/41530743017) |
| StockWiki | `d8d3303` | 本地master，无remote；普通提交静态检查通过 |
| earnings-transcripts | `003c1c065109d0b02c7bd4de09ad3e8461a99c0e` | 既有源码，隔离/组合通过，无本轮改动 |
| revenue-forecast-audit | `f1ae262ed85b6da5d8b040a0b691f1041e20f0cb` | 本地main，无remote；仅PWF更新，既有运行源码独立43项通过 |

CWP测试归属版本`fbc2c858`的[普通CI也已通过](https://github.com/zhengcb81/company-wiki/actions/runs/41530809013)。最后的检出精简只触发组合CI，没有再次启动普通单元CI。最新组合job实际81秒，其中测试步42秒，检出后处理完成。

### 发布复查修复

- **RF摘要回执的最后一道排版拒绝**：RED复现多行合法JSON被拒；移除单行/末尾换行限制，仍拒多对象、重复键和非有限数，并验实际SHA/大小/身份。RF受影响75项、ROOT双消费者20项增量通过，远端已绿。
- **FF干净Linux失败**：[旧远端失败](https://github.com/zhengcb81/filing-fetch/actions/runs/41528697145)的同一Git快照在Ubuntu 3.12复现4项失败。Windows可见真实邻仓，掩盖了默认配置和Dropbox策略测试的错误依赖；另有同一个测试类被重复收集。改用临时profile，迁移生产者断言，避免重复收集。真实POSIX进程组在SIGKILL后仍有短暂活进程；清理在原grace内等owned组停止，区分zombie，独立探针处理reap竞态。WSL受影响50项+grandchild定点、Windows38项、迁移断言1项通过。没删失败断言、没提高超时；CI失败公开注释包含具体测试名。
- **本地与组合测试分工**：正常推送快测CWP17项约11秒、RF12项约2秒、FF11项约1秒（仅测试耗时）。静态/类型钩子不承担Linux进程生命周期全量；独立Linux与ROOT组合查真正行为。组合测试/运行器单独触发source-system，避免为同一组用例重复跑CWP普通单元CI。
- **检出与测试分开计时**：fbc2c858的实际组合测试步53秒且报告已上传，长等待发生于GitHub检出后处理。组合CI现在按RF既有常规CI范围稀疏检出；Git树中需检出的RF文件从50,594个约902MB收窄到459个约5.7MB，只读checkout不保留凭证。这里是文件树估算，不冒充实际磁盘或下载节省。最终组合状态见上表，没有增加测试。

最终两组RF/FF运行文件已定点同步；三入口再次以新进程真实运行通过、0 provider下载、临时根恢复、重复同步零写。生产原文、配置和封存未改，真实收费调用0。5个初始WIP完整保留；旧RF日检追加诊断单列，不影响当前发布/运行，不冒充已退休。

本地原始证据根`.planning/decoupling-implementation-20261102/`：system-final（39P/0skip）、各隔离log、receipt-regression、ff-linux-ci/ff-linux-grandchild、dropbox-owner、installed-execution-final、remote-ci。PWF收尾为文档提交，代码CI绑定表中版本，不伪造文档提交的CI。

下一步依[主计划](../../task_plan.md)恢复T4父链、SEM-QUAL-01、新真实摘要/恢复/RF采用。架构完成不代表公司循环已验收。
