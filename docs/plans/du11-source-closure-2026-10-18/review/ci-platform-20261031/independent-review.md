# CI41238915399 根修：最终独立大节点审查

结论：**PASS（当前八路径工程修复范围）**。没有未关闭的阻塞问题。实际 Linux CI 与 Python3.10 runner 尚未执行；本结论不代替提交后的 CI 结果。

审查基点：`946537d0d75ac36b22ac0bb24e0f484a896b4c95`，integration `C:/Users/郑曾波/Projects/_w22r`。本审查者没有参与这轮产品补丁创作，未修改任何产品/测试文件；只写本目录收据并运行无模型窄验证。完整阅读八路径最终 diff、完整 job_limit/run_x1/run_comparison/manifest、既有 WindowsJob 与 waiting bootstrap、相关测试与作者 test-receipt。CodeGraph 先用于共享 owner 结构定位，再读确切实现。没有访问 ROOT M8/R1 WIP、作者工区、原件、数据库或真实模型环境。

## 最终实现审查

- **导入与平台边界正确。** job_limit 模块顶层不再创建 WinDLL。Windows API 仅在明确的 Windows 观测/owner 执行时加载。纯参数、manifest、metrics/cache 和 CLI 导入不要求 Windows DLL。`require_memory_limit` 在实际 run_x1_batch 和 common comparison 的 X1 分支读模型之前执行；非 Windows 明确抛 MemoryLimitUnavailable，没有无强限推理 fallback。后者的前置顺序是本轮独审提出并已关闭的问题。
- **内存数据保持可追溯与未知。** Linux 从 /proc/meminfo 的实际字段计算；缺失/无法读为 null 与 reason。观测不声称具备强限能力。可用物理内存未知或零时不能推导 cap。移除0.5GiB人为下限符合 min(8GiB,avail/2) 既有边界。
- **复用既有资源 owner。** JobMemoryLimit.assign 使用原 Popen `_handle`，不按 PID 重开进程；共享 WindowsJob 用 JOB_OBJECT_LIMIT_JOB_MEMORY 对 owned job 总 commit 限额，峰值返回 peak_job_memory。未新增一套 Windows ctypes Job 管理。receipt 的字段/measurement_scope/方法说明均明确 total job commit，严格度不低于原单模型进程范围。
- **赋限前不执行目标命令。** 最终 run_x1 复用既有 `_WINDOWS_BOOTSTRAP`，先创建等待进程，assign 成功后才发送 NUL；assign/释放异常会关闭 stdin、kill/wait，再由 finally 关闭 owner。原 bootstrap 与 WindowsJob 都独立核对为基点未改字节。此次仍存在的初始化间隔只有等待 bootstrap 自身，不会提前运行 OCR 目标。
- **测试修改没有取消生产边界。** fake watchdog/CLI 测试显式替换 capability 和资源 owner，保留真实 child timeout、backstop、原 Popen 所有权、缓存恢复等断言；这不是生产平台检查的旁路。cross-volume 用例仅声明其 Windows drive-letter/NTFS 合同，并动态选不同盘符，生产跨卷拒绝代码没有修改。POSIX 不再把 D: 相对目录误当跨设备证明。
- **原生 Job 测法调整合理。** 120MiB cap、请求总量300MiB、失败退出、原 peak<=cap+64MiB 断言均未放宽；从单块300MiB改为保留全部4MiB chunks 的累积分配。单次失败请求产生超 cap 的历史 peak 计数本身不能证明强限失效；作者明确记录 allocation refused/current commit 与 peak 的区别，没有把当前值回填峰值。bootstrap 同时独立修复了赋限前执行窗口。

## 独立验证与证据边界

本审查者实际执行：

1. fresh process 删除 ctypes.WinDLL 并模拟 Linux 平台导入、unsupported-before-model、/proc测量/缺失、原 Popen handle 委托、无模型 watchdog：**5 passed /1.25s**，cross-review-tests.txt。
2. common X1 前置拒绝最终增量及相关两个 owner 边界节点：**3 passed /0.36s**，cross-final-tests.txt。两次命令分阶段执行，不声称是一个八例最终全域命令。
3. 独立中性 bootstrap 探针保持真实 waiting bootstrap，仅把目标替换成 tiny marker writer，并令 assign 拒绝：目标 marker 未产生，原异常保留，process reaped、stdin closed、owner closed 均为真。independent-barrier-failure.json 与 independent_barrier_probe.py。即使时序回退，该目标也不会加载任何 SDK。
4. 八个最终源码/测试 raw 与 LF SHA 全部独立重算，与 source-bindings.json 逐项吻合。共享 `_process_tree.py` 和 `_bounded_process.py` 的 LF SHA 同时与基点 git blob 一致；见 independent-sha256.json、independent-reused-bindings.json。

作者 test-receipt.json 另记录精确失败/新增小域22P（2.33s）、最后新增 fake assignment 失败次序1P（0.49s）、ruff 与 diff-check PASS。审查者已读最终测试代码及这些收据，未重复原生300MiB小内存用例，未重跑全仓或真实 OCR/SDK。实际 Linux 内核 /proc 运行、Linux CI 和真实 Python3.10 运行仍 NOT_RUN；fresh-process 平台模拟与纯观测 fixture 不冒充这些实际运行。

清理：仅删除本审查者创建的 exact `_w22r/.cix-tmp`，先核对路径属于 integration 且无 reparse；`.cix-neutral` 亦恢复不存在。independent-cleanup.json 已记录。没有修改产品文件、旧收据、ACL/MIC、持久环境或 Git 索引；没有下载、安装、模型运行或全仓测试。

## 最终字节绑定

所有下列文件本轮 raw=LF；完整值也在 independent-sha256.json：

- `tools/ocr_comparison/job_limit.py`：`ac8ae6bf24130c85110eeb4e7e48cb1ed8dfb61fc48953f069b2de7ab86b2515`。
- `tools/ocr_comparison/manifest.py`：`74d4397aa98bf32476529bf640123c5cee4fb2ac18e51b273a5b2bbc7ed889f4`。
- `tools/ocr_comparison/run_x1.py`：`70e61afe542e8b4849777eeafd066fb88c19be79f4acba6f03a360a1cb87fadb`。
- `tools/ocr_comparison/run_comparison.py`：`c86556b43f84d886440b74be379b2ecbfe519e25f4dd07a14ec44e13ea7ea290`。
- `tools/ocr_comparison/README.md`：`2bb28ac0a57874fcec9a66b8ed710d435936f95131a53d90a77ec66636efca67`。
- `tests/unit/test_w23_ocr_comparison_metrics.py`：`184417120cf750056ce80b8daaca9c2457f69add930ca6c79158f9eea139607d`。
- `tests/unit/test_w23_ocr_comparison_reception.py`：`facfafd5f8bd0822d05a363fc8194d35d6ecc377cb54f5939db7346fc2b2d97e`。
- `tests/unit/test_w22_pdf_deployment_plan.py`：`90181eae0ae461936011851ae90b18d2fe110afb39adf7f5305ce9c8c881bc5d`。
