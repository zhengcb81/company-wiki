# S5 验证与发布台账

[复审原报告](../module-boundaries-2026-11-11/review/s1-s4-post-rollout-12-module-audit-20261125.md)记录调查快照。[实施顺序](s5-closeout-plan-20261125.md)保留职责和测试范围。以下按复现、修复、正式发布、实际启用分别记证。

| 模块 | 核对项 | 当前证据 |
|---|---|---|
| CWP / F4 | 异常类别、强停前 stderr、轮转、CLI、边界扫描、AUTO 账本 | master@11ca01c57 的[诊断版同版 CI](https://github.com/zhengcb81/company-wiki/actions/runs/45698586312)通过。独审 10 项通过。远端暴露旧故障注入取了移除的导入名，改用实际标准库轮转方法，82 项通过、2 项环境跳过。边界扫描 `bbd0e96e4` 103 项通过。[扫描器证据](../module-boundaries-2026-11-11/review/s5-layer-boundary-scan-20261125.md)覆盖六种盲区和合法对照。AUTO 账本原本反向导入 Store，现共用事务叶子，真实 SQLite 和强停 67 项通过，Mypy 检查 523 个文件通过。独审确认只读快照、租约和回滚。保留三个旧懒加载别名兼容已启动的 worker。 |
| StockQA | 凭据脱敏、stderr 尾段、显式环境、日常测试 | master@0674d51 已推送并切换实机，[同版 CI](https://github.com/zhengcb81/StockQAbyLLM/actions/runs/45700454968)通过。Bandit 把含 TOKEN 的裸正则误报为凭据，改用编译模式。精确 Git 内容在 Ubuntu 3.10.20 用默认编排，静态检查、420 项及 smoke 通过，3 项 Windows-only 跳过。原观察目录与付费账本已经核对。 |
| RF | CI 实际收集、FF 子进程诊断、资料根、跨层探针 | main@1577be3c 的[同版 CI](https://github.com/zhengcb81/revenue-forecast/actions/runs/45696604761)通过。修复了历史夹具依赖及两个 Windows 专用探针，精简 Ubuntu 911 通过、2 跳过、46 子测试。实际 report/reconcile 已统一代码检出。两条已有原失败冷读一致，费用状态仍未知。回告目录没有旧终态，前后返回同一文件缺失。四个逻辑技能入口与 1577be3c 对齐，两份旧 SQLite canary 已退役。来源冷读边界 `49a4013db` 已推送，Ubuntu 106 和总控另验 31 项通过，CI 和部署待复验。 |
| MC | 配置优先级、运行时校验、ffmpeg、HTTP 资源、日志 | master@fa1f840d 已推送，现场已快进并保留其他改动。[同版 CI](https://github.com/zhengcb81/MeetingConverter/actions/runs/45692989173) 通过。底层候选 386 项通过，最终无 stderr 和独立复验 7 项通过。 |
| FF | 异常类型、T3、旁路、矩阵跨仓调用、轮转 | main@7651f70 已推送并快进现场，[同版 CI](https://github.com/zhengcb81/filing-fetch/actions/runs/45702059828)通过。95 项定向通过，公开 CWP CLI 核对原 CRLF 字节。Ubuntu 三市场合成矩阵各一例通过，零取件与费用。定时、普通作业、T3 共用本仓轮转记录，实测双进程轮转。四个技能逻辑入口已对齐，每个物理目录同步 31 项，配置 SHA 相同，复查零差异，四个新进程 CLI 正常启动。 |
| ET | worker 导入和用量流、并发、manifest、中断、帧 | main@7f4c1e7d 已推送并快进，[同版 CI](https://github.com/zhengcb81/earnings-transcripts/actions/runs/45698502294) 通过。复现基线和首候选的并发半份快照。修复后 12/12，强停后仅补投原启动，一次用量语义保留。manifest 写失败返回非零，原件保留。 |
| SID | CWP 适配器、句柄、stderr 兜底和轮转 | v2-clean-rewrite@9b0c07c9 已推送及快进。[同版 CI](https://github.com/zhengcb81/StockInfoDownloader/actions/runs/45699176729) 通过，58 项及独立 9 项通过。普通失败的原单 JSON 协议稳定。 |
| Audit | journal 降级原失败冷读、轮转、技能 | main@560ae51c 本地正式快进，本仓无远端。837 项离线和独立 4 项加两子测试通过。先存原失败再发可引用观察。技能四个逻辑入口每份 52 文件均通过清单校验，已补 Codex，第二遍零写。 |
| StockWiki | 跨库恢复、复本补投、日志和错误码 | 基线 dd5b0338 注入 receipt DB 提交后发生公开确认故障，同一子收据和身份版本已可重入。保留事务设计。独审复现只有历史副本时误写归档与 Windows 并发轮转丢行。修复 `d09e2bef` 已快进本地正式 `master`，74 项及最终独审 3 项通过。仓库当前无远端。 |
| IQS | 非法/截断 HTTP、同阶段不同题、StockWiki 接口 | master@2d803a9a 已推送及快进隔离运行，[同版 CI](https://github.com/zhengcb81/invest-quick-scan/actions/runs/45698671343) 通过。Windows 92 项、Ubuntu 同款 41 项通过。旧鲜度 oracle 调用的两项均是 StockWiki 声明的公开纯值端口。 |
| Dashboard | 相关号、原文预览错误与取消、旁路 | main@df39a22f 已推送及快进实际隔离运行。23 项后端、293 项前端、TypeScript 和独审通过。详情可查但 ready 拒写时保留真实相关号，流水按原 ready 协议。当前未登录会话无法读该私有仓 CI。 |
| IR | HTTP 200 响应坏或截断、末次 429、旁路与技能 | main@42c23330 已推送，实际 F4 切到同版运行检出。47 项及 7 子测试通过，独审三项证实 HTTP 200 读错均只发一次，最后 429 无等待。四个逻辑技能入口 16 个差异全部对齐，均已核对第二次零写。当前未登录会话无法读该私有仓 CI。 |

## 实机口径

实机沿用原观察目录和付费状态。验证使用既有故障与本地隔离的替身，真实新财报下载、转录和模型请求为零。已知失败与未知费用分别保留。代码发布、技能同步与原作业可冷读分别记证。

## 审计判定

- **S5-01 至 S5-04**以表中失败复现和原入口回归为准。StockWiki 跨库提交可恢复，修复集中在复本重投冲突和日志轮转。ET 捕获退出类异常的分支已经清理并继续抛出，修复集中在真实强停和写盘失败。MC 拒绝把布尔值当整数，合法的零次追加重试仍执行一次初始调用。
- **S5-05 与 S5-06**按公开路径验收。采集、摘要、服务、宿主和冷读的定向结果见表。历史工具、所有入口的日志覆盖及多种基础设施同时失效仍需逐仓补证。日志与反馈投影失败保留原业务结果。
- **S5-07**以实际调用归属验收。FF 矩阵走 CWP 公开 CLI，RF 探针使用结构化返回，旧已安装的私表探针已退役。IQS 历史鲜度验收使用 StockWiki 声明的公开端口，保持版本兼容。
- **S5-08 与 S5-09**按已复现的耦合改善职责和扫描范围。循环报告用于调查，生产运行沿用原业务契约。其余仓内环和私有访问以原审计为索引，按真实边界验证。
- **S5-10**升级专用运行检出，复用原数据根。在途工作的主目录保留原工作分支。实际已有冷查与隔离夹具各自按表记录。
