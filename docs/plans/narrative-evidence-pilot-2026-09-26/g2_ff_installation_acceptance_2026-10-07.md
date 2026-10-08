# G2-08：FF 安装系统修复与实际安装验收

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**complete，2026-10-07。** 工具实现26e0e60、安装指导211a56f已正常并入FF main并推送。源码[CI37696236234成功](https://github.com/zhengcb81/filing-fetch/actions/runs/37696236234)。纯指导后续提交复用源码CI，不重复长测试。

## 实际改动

- 保留现有`sync/installation_diff/main`调用；增加重复`--file`、零写`--plan`和一个JSON输出。
- 删除整个安装目录扫删逻辑。用户配置、密钥、输出、缓存、未知文件均保留；公开配置模板只初始化缺失配置。
- 缺安装报告真实drift；只比较所选package-owned文件，不把用户残留算作资格门。
- 根别名合并为同一物理目标。选中子路径的链接、越界、源字节变化和目标并发改动由自动检查处理，不加入人工签收。
- 按差异逐文件暂存、原子替换；失败如实报告written/not_written/conflicts，临时文件清理，重复只补剩余。不假称全部回滚。
- 当前SKILL说明工具属于仓库工程层；定点示例需要当前其余依赖，老副本应明确包含运行依赖或使用保留用户状态的整包更新。

## TDD 与一次集中节点

旧实现初次8失败/8通过/2跳过：实际删用户文件/覆盖配置，缺安装却MATCH，缺定点plan/恢复接口。Windows无symlink权限时改用临时目录内junction，实际验证两种链接边界而非默认跳过。

新旧安装责任包集中26项通过，最终4.66秒，`-W error`无警告。补一个`.`无效scope后9项输入验证通过；正常提交钩子发现测试的宿主写法，再改为PureWindowsPath及真实不支持文件系统的fallback语义，12项相关可移植性反例1.69秒通过。不相加重叠计数；当前源码CI包含最终完整新包和既有安装surface。

实际子进程E2E在3个临时目标执行全包初始化、选中文件故意旧化、plan零写、定点应用、三个安装入口help及重复0写。没有HTTP/provider/LLM/翻译，pytest资料位于本次短owned根，退出后恢复absent。

首次Windows链接命令输出按控制台代码页解码产生线程警告，改为按字节捕获，未压制警告；宿主检查没有新增白名单、baseline或绕过hook。`.`词法输入避免空parts异常，拒绝发生在任何写入前。

## 真实用户安装

原三文件估计不足：两个实际安装都缺`ff_process_transport.py/ff_process_tree.py`，`transcript_tool_transport.py`也过旧。按fetch_filing当前仓内import闭包，显式选择8文件：

```text
SKILL.md
scripts/fetch_filing.py
scripts/ff_process_transport.py
scripts/ff_process_tree.py
scripts/ff_v2_envelope.py
scripts/filing_contracts.py
scripts/transcript_companion.py
scripts/transcript_tool_transport.py
```

`.agents/.claude/.codex`三个逻辑入口对应两个物理目标；每目标6个实际差异，共12次物理文件更新，闭包内相同的2文件不重写。先核发布HEAD与源SHA、目标preimage、未选文件清单，再从已发布工具执行，没有自动扩大`--file`的含义。

两个实际fetch_filing入口`--help`均exit0；所选范围只读check exit0；重复应用written0。未选文件size/mtime完整清单不变，18个原owner/生产保护SHA不变；FMP真实密钥不读取、不stage，config/output删除0，raw删除0，Dayu/IQS写0。

FF当前运行`scripts`Git tree与RF兼容manifest的5001dcb pin完全一致。本次改变仓库installer/tests/CI及指导，不需要为了它反复重签邻仓或重跑已经绿色的获取链。

## 临时目录恢复（2026-10-08）

本轮18个精确owned临时条目已恢复absent；删除前逐条保存字节/文件清单并拒绝tracked或reparse。实测清理1631381B、751个临时文件，原件/owner删除0，18个保护SHA不变；五个历史未分类根及交接工作树保留。[恢复收据](harness_lanes/results/g208_temp_cleanup_2026-10-08.json)。PowerShell汇总未识别ordered dictionary属性，已从保存的逐条清单重算，未估算释放量。

## 证据与下一步

- [正式结构化验收](harness_lanes/results/g208_main_acceptance_2026-10-07.json)
- [源码精确CI](harness_lanes/results/g208_exact_ci_2026-10-07.json)
- [真实安装](harness_lanes/results/g208_real_install_2026-10-07.json)、[只读plan](harness_lanes/results/g208_plan_2026-10-07.json)、[实际应用](harness_lanes/results/g208_apply_2026-10-07.json)

RF旧strict-target/coverage/mtime问题已核当前G3代码：AST跟随CI委托，数字漂移只诊断，manifest默认SHA/size且mtime诊断。此前G3已发布/验收，不重做、不改owner日志或历史baseline。

MAIN继续G2十四组当前证据/指导与最后A/B节点核对，只补未覆盖的真实行为；之后R2生产来源/ET登记→R3正式final与消费者→R5最终收口。全部PWF目标仍active，不将安装完成等同全部计划完成。
