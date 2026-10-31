# CI41238915399 isolated platform fix

状态：工程修复完成，独立大节点审查PASS，待ROOT复核提交；未提交/推送。起点 `_w22r` clean HEAD `946537d0d75ac36b22ac0bb24e0f484a896b4c95`。只改8个实验工具/专属测试路径，完整raw/LF SHA在source-bindings.json。ROOT主工区M8/R1与作者树未改。

## 根因和修复

1. `job_limit`模块顶层调用ctypes.WinDLL，导致Linux上连纯参数校验、fake CLI、缓存恢复和3.10兼容导入也崩。改为import-safe平台能力边界；实际Windows-only强限明确MemoryLimitUnavailable。`run_x1_batch`和common CLI X1都在读模型前检查能力，非Windows没有无界推理fallback。纯metrics/cache/参数CLI仍可跨平台导入；fake测试显式替换能力/资源owner。
2. 原工具复制了一套Windows进程资源管理。现在复用现有`company_wiki._process_tree.WindowsJob`，赋原Popen handle，不通过PID重开；共享owner对总job commit施加限额，严格程度不低于原单模型进程上限。receipt明确owned-job-total-commit及真实job峰值，不伪称ProcessMemoryLimit。
3. 独立审查发现启动/assign竞争：现复用已有`_bounded_process._WINDOWS_BOOTSTRAP`，job assign成功后才放NUL启动真实命令；assign失败不释放，kill/wait/reap并close owner。无新线程/进程框架。新增纯fake失败次序反例；独审核真实tiny marker未启动。
4. 内存快照复用同一接口：Windows调用时才加载API；Linux读取/proc/meminfo的MemTotal/MemAvailable/CommitLimit/Committed_AS；不支持/缺失为null+reason。资源清单不造固定成功数值，不把观测当成强限支持；未知available无法推导内存cap。移除原默认min0.5GiB可提高低内存边界的行为。
5. cross-volume测试的D:假设仅对Windows有意义。用Windows-only平台声明保留真实生产错误断言，并选择与实际tmp盘不同盘符；POSIX不假装D:是另一个设备。不改生产部署代码，也未将其升级为跨平台部署支持。

## 验证

- 精确失败节点及新平台小反例22P，2.33s。
- 最后新增assign失败/不释放/回收次序1P，0.49s。
- ruff及git diff --check通过。
- fresh process把sys.platform设linux且删除ctypes.WinDLL，参数/manifest/common CLI import成功，真实JobMemoryLimit明确拒绝。此为API边界反例，不冒称实际Linux CI已经绿。
- 原生Windows Job测试保留120MiB限额、300MiB请求总量、失败退出和原peak<=cap+64MiB断言。初测单块300MiB拒绝分配后job peak333MiB、PeakPagefile324MiB、当前commit9MiB，说明该失败请求会污染峰值计数；改4MiB递增并保留全部已分配块，既证明累积请求无法越限又保持峰值断言有意义，没有提高限额或放宽上界。保存的测量应如实报告失败峰值，不能从当前commit回填历史peak。
- subprocess捕获显式UTF-8，修复宿主GBK对UTF-8 child日志的thread warning。旧LaTeX字符串SyntaxWarning与此次平台修复无关，未扩范围。
- 不安装WSL、依赖或模型，不运行OCR/SDK/全仓。真实Linux/Python3.10 runner回归仍由后续精确CI确认。

独立大节点审查由未参与本补丁的PDF agent进行，最终PASS，报告independent-review.md。8路径raw/LF与本绑定一致，共享两模块与946537d0基点blob一致；独立5P/1.25s+3P/0.36s及真实tiny bootstrap拒绝探针通过，owned scratch已清。实际系统能力和Job限制的说明参照[Microsoft Job limit文档](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)，本轮测量/平台限制以自己的收据为准。
