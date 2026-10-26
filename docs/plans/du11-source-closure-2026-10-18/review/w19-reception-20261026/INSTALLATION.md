# 全局技能同步已修复（2026-10-26最新）

同一获批shell下工作区venv因可执行文件Low标签仍降权；使用现有宿主Python后同一canonical安装器已实际成功。四文件×两物理根共8项更新，.claude junction不重复；各22份公开runtime SHA一致，重复0写。三逻辑安装入口新进程→隔离CWP三表reuse-only均通过，0HTTP/付费，测试根恢复。用户配置保留；其生产默认配置功能并未由隔离测试代签。未改全局ACL/标签或沙箱设置，不需要再授权。

唯一当前细节与命令见[根因及修复](../skill-sync-root-cause-20261026/README.md)。以下旧EACCES/六文件零写是当时真实快照，install-actual-receipt.json不改写；它不再表示当前未同步。

---

# 全局技能副本：实际OS拒写，不是项目许可

仓库主线代码已可用且两仓精确CI成功。三个选择路径是`SKILL.md`、`scripts/fetch_statements.py`、`scripts/ff_financial_statements.py`；`.claude`指向`.agents`同一物理目标，另一个物理目标为`.codex`。六个实际文件均未写入，前后SHA不变；配置、输出和未选文件不变。安装程序还诊断了原有`fetch_filing.py`安装漂移，本轮未扩大写范围。

当前执行令牌不能在两个技能目录创建暂存文件，原样返回EACCES（见install-actual-receipt.json）。用户授权一直有效，ROOT没有再询问材料/覆盖许可，也没有改目录ACL、换成直写/备用目录绕过。若要立即更新全局副本，可在具有本来写权限的正常用户PowerShell运行同一条定点命令；不需开放整个目录：

```powershell
python "C:/Users/郑曾波/Projects/filing-fetch/tools/sync_installs_b3.py" --install --file SKILL.md --file scripts/fetch_statements.py --file scripts/ff_financial_statements.py --json
```

失败保留实际status/not_written，成功才做一次安装后新进程`fetch_statements.py --help`与隔离reuse-only验收；不要先写“安装完成”。主线其他工作直接使用`C:/Users/郑曾波/Projects/filing-fetch/SKILL.md`及该仓scripts入口，不等人审。

## Windows空转共因已关闭

初次原安装器CPU空转，ROOT核对PID/父进程/精确命令后仅停止本次进程；一次20秒有界诊断的5秒栈位于Python3.14 tempfile._mkstemp_inner，旧writer调用mkstemp。Windows标准库会把PermissionError且os.access(W_OK)为True当碰撞继续TMP_MAX；预检不等于受限令牌真实可写。

同一owner已改成同目录O_EXCL/0600、有界8次真实FileExistsError，PermissionError一次原样返回。fsync、SHA/CAS、os.replace与失败清理保持；无ACL/授权策略改动。两个先RED32次的用例已绿；整体54通过/3skip（含FF35），独立5实际探针及19通过/3skip。link测试因环境Access denied跳过，不算通过。提交f7aa0ba并入FF主线5396bd6，pre-push935通过/7skip/+78subtests/105.73秒，精确CI40304350720成功。

`installer-review`对初次20秒现象的描述是历史诊断；它绑定的`install-diagnostic.json`是后续当前状态（0.381秒EACCES）的原始工具输出，不能把它当初次超时JSON。两个真实RED、标准库独立核验和有界错误收据分别保留，源码/事实不混签。
