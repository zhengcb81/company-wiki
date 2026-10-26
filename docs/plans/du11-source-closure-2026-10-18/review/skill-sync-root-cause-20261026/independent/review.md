# 全局技能同步独立只读审查

**PASS / 0 OPEN（本节点范围）**。ROOT的实际同步收据与当前安装字节、Windows令牌/标签实证一致；审查者未执行安装器写操作、未改全局ACL/标签、未读取配置或凭据正文，未提交。

独立复现了同一获批PowerShell的对照：外层Medium（8192），venv启动器及真实Python子进程均Low（4096），直接基础Python保持Medium；这两条获批路径均非AppContainer。venv文件确为继承Low标签，基础解释器和两个目标目录隐式Medium。默认受限shell则本身Low/AppContainer，直接基础Python仍Low，不能把基础解释器当自动提权方法。此结果符合[微软MIC规则](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control)：Low写Medium被no-write-up限制，即使DACL允许写；进程取调用者与可执行文件较低IL。`IsTokenRestricted=false`不能证明Medium。目录owner FullControl已只读核实。

ROOT使用相同canonical安装器（SHA `6eccbb375b25badc16684d0c79547b36c2e9ee0a68ea445b4430cf3d38ee39de`）的三文件同步确为两物理根共6次替换、重复0写，但该阶段runtime_byte_complete=false。两个fetch_filing旧副本精确对应可达历史Git blob `a1ff25acf5bc5b76c8bdd5fe744cc09dcede88d6`，差异为已发布local_read_budget兼容。随后仅补此文件再写2份；最终四路径重复0写。

我独立读取canonical owner manifest及安装副本：两物理根各22个公开runtime文件全部逐SHA相同。`.claude/skills/filing-fetch`是指向`.agents/skills/filing-fetch`的junction，samefile验证通过；`.claude/skills`父目录本身不是junction，不计第三份物理安装。与补漂移前快照相比，仅fetch_filing的size/mtime改变，无新增/删除文件，其余未知文件及配置仅核metadata且不变。用户config独立保留，不要求等于模板，不能把“全公开runtime字节一致”表述为覆盖全部用户文件。

已审真实安装入口smoke脚本/收据：从三个实际安装入口分别启动新进程，显式隔离config经真实CWP有界子进程reuse_only，各36/33/36期、9729行、12个返回SourceRef可打开、0HTTP；fixture种子15次exchange不是真实HTTP。ROOT记录13.447秒、清理前目录大小11,709,113B（非峰值）、tmp最终不存在。没有mock FF响应。此证据证明该隔离复用路径，不代签保留的默认生产config/CWP部署或所有adapter执行；installer自身仍正确标执行NOT_EVALUATED。

获批宿主运行时原则是对该已批准窄操作避免venv意外降IL，并非修改权限、关闭沙箱或另造writer。默认受限上下文仍按平台支持的审批机制处理。本节点不新增逐材料审批/许可链，也不把来源/PDF/投资研究层当成权限故障责任层。

实际SHA、根因只读对照、历史blob差异、ROOT所有durable文件绑定见JSON。C3、正式摘要/cache/RF及公司审查循环不在本结论内。
