# 全局技能同步拒写：根因调查与修复

状态：已修复并完成实际同步、幂等和三个安装入口的隔离验收；独立复核已PASS / 0 OPEN，见[报告](independent/review.md)及[JSON](independent/review.json)。用户明确要求查清并修复全局技能副本拒写，优先于C3。沿用现有PWF及授权，不另加人审/许可文件。

## 真正根因

不是缺少用户授权，也不是目录只读/DACL。获批执行的外层PowerShell是Medium；但工作区`.venv/Scripts/python.exe`继承了Low完整性标签`S:AI(ML;ID;NW;;;LW)`。Windows启动程序时按调用者与可执行文件的较低完整性创建令牌，所以该venv及它启动的基础解释器实际为`S-1-16-4096`（Low）。全局技能目录无显式标签，按Medium处理。MIC的no-write-up先于普通DACL，即使个人用户FullControl、`os.access(W_OK)=true`，Low进程仍然不能写Medium目录。

同一获批shell直接运行**已经安装的基础Python**，进程为`S-1-16-8192`（Medium），同一canonical安装器随即成功。没有改ACL/完整性标签、关闭沙箱、请求管理员权限或另开不受支持的执行通道。默认受限shell仍可能保持Low/AppContainer；不能把“基础Python”当作自动越过父shell边界的方法。

此前检查外层`whoami`、`IsTokenRestricted=false`和DACL不足以判断实际Python的完整性；把现象笼统记为“环境拒写”是不完整定位。`IsTokenRestricted=false`不等于Medium。独立的Windows tempfile权限错误碰撞空转是放大问题，上一节点已在FF `5396bd6`修复，它不解释实际EACCES。

只读复现：在**同一已获准的宿主shell**中分别调用venv和基础Python运行[diagnose_runtime.py](diagnose_runtime.py)，对照[venv令牌/标签](venv-runtime.json)与[宿主令牌/标签](host-runtime.json)。诊断脚本不写任何全局文件或修改权限。微软规则见[Mandatory Integrity Control](https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control)；Codex运行边界与审批是不同机制，见[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)。

## 实际修复与验证

1. 同一canonical `filing-fetch/tools/sync_installs_b3.py`，SHA `6eccbb375b25badc16684d0c79547b36c2e9ee0a68ea445b4430cf3d38ee39de`；以正常宿主Python执行已有显式三文件同步。两物理目标实际写6文件，重复0写。
2. 另两份`fetch_filing.py`旧安装的blob `a1ff25acf5bc5b76c8bdd5fe744cc09dcede88d6`在canonical Git历史中存在；差异仅已发布的`local_read_budget`观察兼容，并非用户定制。用同一安装器仅补该文件，两物理目标再写2文件。没有扩大到用户配置。
3. 最终两物理目标各22份公开runtime文件与canonical FF `5396bd6`逐SHA一致。`.claude/skills/filing-fetch`是指向`.agents/skills/filing-fetch`的junction，不重复安装。用户`config/company_wiki.json`单独保留，不要求等于仓库模板。再次四文件同步两目标均0写、无暂存残留；其他文件元数据及配置SHA保持。见[实际三文件写入](install-three-files.json)、[三文件幂等](install-three-files-repeat.json)、[旧漂移修复](install-legacy-drift.json)、[最终零写](install-final-repeat.json)、[完整SHA/保留验证](final-verification.json)。
4. [安装后真实CLI复用验收](installed-cli-reuse-v1.json)：独立测试根使用既有Sina冻结字节先由CWP fixture port入库，再逐个以新进程从`.agents/.claude/.codex`实际`fetch_statements.py`入口执行reuse_only→真实CWP子进程。三次均36/33/36期、9729行、12个返回SourceRef直接读取、0HTTP；没有mock FF响应。13.447秒、清理前临时目录11,709,113B（不是峰值测量），测试根恢复不存在；0真实网络/付费、原件不变。可重复脚本为[verify_installed_cli.py](verify_installed_cli.py)，每次用新的output文件，不覆盖历史收据。

此为技能部署/安装入口验收，不冒充C3正式摘要、LLM缓存或RF采用验收。CLI测试显式传入独立测试配置，不能据此声称用户保留的生产默认配置已做功能验证；默认配置没有覆盖。C3及公司审查循环继续OPEN。

## 后续统一执行方式

在平台**已批准**的宿主shell里使用现有解释器的base路径；这个路径从运行时发现，不硬编码用户名或Python版本。安装器仍保留定点选择、SHA/CAS、原子替换及配置保护：

```powershell
$hostPython = & .venv/Scripts/python.exe -c 'import sys; print(sys._base_executable)'
& $hostPython docs/plans/du11-source-closure-2026-10-18/review/skill-sync-root-cause-20261026/diagnose_runtime.py
& $hostPython "$env:USERPROFILE/Projects/filing-fetch/tools/sync_installs_b3.py" --install --file SKILL.md --file scripts/fetch_statements.py --file scripts/ff_financial_statements.py --file scripts/fetch_filing.py --json
```

shell本身仍受限时，base进程同样受限，应按平台支持的审批方式执行该窄操作；不自提权、不改目录或文件标签。部署使用宿主Python、业务测试继续使用各仓venv，避免把解释器完整性故障传给来源/解析/研究层。项目`AGENTS.md`已补同一运行时原则，不新增产品门禁或逐材料审批。

## 历史调查（已被以上实证收敛）

2026-10-26新增实证：`require_escalated`进程是个人用户、中完整性；Python `IsTokenRestricted=false`，目标目录无只读属性，`.claude/skills/filing-fetch`是指向`.agents/skills/filing-fetch`的junction。用户本身具有FullControl。相同Python O_EXCL小探针仍对`.agents`和`.codex`返回errno13，但`os.access(W_OK)=true`。因此上一轮“受限令牌/目录ACL”只是未经完整证明的归因，不能据此修改ACL。Windows tempfile误把PermissionError当碰撞导致空转的代码缺陷已修复，但它不是实际拒写的根因。

当时计划：核对实际文件API、物理路径与执行环境，再恢复同步并验证新进程/幂等。现已完成，不能再把本段当待办。AppContainer、普通DACL、Defender受控文件夹和路径转义没有解释获批shell下的失败；实际解释为venv可执行文件Low标签。

范围限定为filing-fetch技能三文件；不修改Dayu/IQS/RF工作、生产原件、用户密钥或全局目录ACL。

独审归档保留原始字节；[映射](archive-map.json)记录来源及SHA。独审时README快照保留在independent/reviewed-root-readme.md，独审后仅更新本页完成状态和junction路径表述，两个可执行脚本与全部运行收据未变。
