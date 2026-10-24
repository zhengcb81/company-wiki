# W13 ROOT 接收独立审查

## 结论

**PASS_ROOT_INTEGRATED_FIXES**：可接收 ROOT 修正后的 W13 调度层。**原作者 a8045416 候选不通过**，不能把其 handoff 的 G02/G09 PASS 原样继承。

ROOT 当前被审版本为 pending merge，HEAD `885e140d2d69baad61ef791497e85e4f30fff366` 加 `root-final-source-bindings.json` 列出的八个文件字节；作者实现 commit `56baea4cdd8c89b5cf778d0bda948c31ec5af162`、冻结交付 HEAD `a804541661f73cd035fc25179b116ba9a51c5e55`。最终 runner SHA-256：

`a307933c216105d4a180a307c1ea4e29910432175211109afb78fbe2c6175b73`

最终独立验证：**154 passed / 125.60s；18 个独立政策探针通过；5 项真实本地 Git ref/E2E 检查通过；ruff 通过。** 154 测试墙钟包含本轮并行 AST 盘点的 CPU 争用，不是日常 push 性能数据。未重跑全量 8k，未要求每次 push 全量。

## 发现与关闭

|发现|旧候选实证|ROOT 最终处理|
|---|---|---|
|宽 closed list 仍跑数百文件，违背 G02|独立 33/65/333 文件探针分别膨胀至 62/94/362 targets；作者实际宽集 357 targets /628.6s timeout。真实 33 文件 ref 仍执行隐藏红，未 defer|明确 32 个受影响文件政策预算；去重后超预算整集交给 CI，不截取前 N；目录建议亦整体 defer|
|执行前提前报 PASS|旧 main 执行前已经含 `local_fast_pass`|执行前只报 planned；仅子进程真实成功之后输出 pass；7/124/启动及异常均非零|
|G05 看不到实际 targets|旧日志仅理由和数量，成功 runner 丢弃大部分 pytest 输出|执行前完整列出去重目标和 defer 原因，独立 runner 内逐项检查可见|
|旧 19 失败误称随机 xdist/AV flake|逐条读日志发现全部文件路径长 261/263/264；中性 tempfile 259 成功、260/261/263/264 稳定 errno2 FileNotFoundError|报告纠正为旧 Windows 路径长度问题；并非 W13 新回归，也**没有被本包修复**，留 ROOT 高优先级共因修复|
|handoff 的 sha256_prefix 实为 Git blob 前缀|例如 `61b09b3e...` 与 diff blob 对应，而实际旧 runner SHA256 为 `b5dec444...`|本独审绑定真实完整文件 SHA256，不沿用误标作为身份凭据|

同一套独立政策探针对旧候选为 **9F/9P**，对 ROOT 最终为 **18P**，见 `author-original-probes.json`、`root-final-probes.json`；未削减 probe 求绿。真实 33 文件 ref 反控也保留旧候选 FAIL 和最终 PASS。

## G01–G09 接收依据

|要求|独立结论|
|---|---|
|G01|真实 `.githooks/pre-push → python ... --push-checks` 和 Git stdin 保留；无缓存放行或许可文件|
|G02|docs/unknown/宽配置使用固定 smoke；32 以内完整文件；33/65/333 closed 整集 defer；目录不冒充一文件|
|G03|29 个共享 FAST 成员及 CI regression 成员与 a313 基线逐值相同；文件覆盖节点时去重，未删业务测试|
|G04|完整模式、skip-contract、fast-contracts-only、junitxml 的实际 argv/顺序与 a313 相同；`_run`/`_run_pytest_gate`/worker/TEMP 执行器 AST 完全相同；ROOT CI workflows 字节也与冻结基线相同|
|G05|planned/真实 targets/defer 可见；pass 只在实际成功后输出；fast/full 文案分开|
|G06|真实快集合红、缺 runner 均拒推；退出码 7/124 原样回传，启动/timeout/其他异常不能伪绿；首失败仍保留|
|G07|卡内 ref 删除、多 ref、新分支、旧 SHA 不可得、空 stdin、rename/delete、配置/文档/源码/测试矩阵原断言通过；未知建议不再导致本地 full|
|G08|隔离真实 bare remote：新分支绿、33 个新测试文件闭包整集 defer、快集合红拒推、缺 runner 拒推；同夹具完整 pytest 单测命令确实发现快集外隐藏红。完整模式所有阶段 argv 另与基线比较，未冒称该夹具跑过真实产品全量|
|G09|原作者 docs44.5s/narrow66.8s/unknown46.6s/wide628.6s 如实保留；原 wide 排除为“non-goal”不成立，现已修边界。新真实源闭包334文件降29目标；不再隐式跑全量。32文件只是调度预算，不保证任何单文件都小于60s；不添加墙钟审批阈值|

`root-final-scope-matrix.json` 是最终实际源树的**规划结果**：docs29、narrow 一文件与 smoke 去重后28、unknown29、wide334→29；不是四类真实产品运行性能或全部产品通过证明。其 AST 规划在并行负载下花46/28秒，保留为后续优化机会，不伪称已消除所有推送开销。

## 独立实际命令与结果

1. 从作者冻结 Git 对象 archive 展开必需 tracked 源码/测试至 ROOT 自有 `.w13rv`，排除公司原件、运行库、旧 output 和密钥；不 checkout/写作者索引或运行作者写入脚本。完整 1753 文件 SHA 和 protected-tree 同一性见 `frozen-inputs.json`。随后仅用 ROOT 冻结八文件覆盖隔离副本，所有测试实际从该副本导入。
2. 隔离目录运行卡内七文件测试：首轮沙箱 141P/4F，全部失败是 sh DLL/本地 transport 启动；不改断言，无沙箱重跑 **145P/57.97s**。末轮加 ROOT `test_daily_push_bounds.py`，同原断言 **154P/125.60s**，`root-final-tests.xml`。
3. 命令：`python -m pytest -q --tb=short -p no:cacheprovider --override-ini addopts='' --basetemp=.pt tests/unit/test_ci_push_selection.py tests/unit/test_changed_resource_scope.py tests/unit/test_changed_test_module_scope.py tests/unit/test_pre_push_temp_scope.py tests/unit/test_pre_push_parallel_phases.py tests/unit/test_pre_push_full_unit_workers.py tests/unit/test_daily_push_policy.py tests/unit/test_daily_push_bounds.py --junitxml=<independent>/root-final-tests.xml`。设置 `PYTHONPATH` 指隔离副本和 src、禁 pycache；`CW_SHORT_BASETEMP_DISABLE=1` 仅使自有短45字符 basetemp留在自有树，无测试跳过。
4. `python <independent>/review_probe.py --source .w13rv --label root-final`：18P；旧相同探针9F/9P。检查宽集/目录/去重、输出时点、真实退出码和异常、完整/远端命令、共享常量及完整执行器 AST。
5. `python <independent>/real_ref_probe.py --source .w13rv --label root-final`：5/5。实际 git push 用本地 bare remote、真实 hook/selector/runner/pytest；业务测试体明确为中性合成。四次 push 为20.66s/13.024s/9.369s/0.366s，不充当真实146 smoke耗时。完整命令/stdout/stderr在 `root-final-real-ref.json`。Git只读对象曾使本 reviewer 初次夹具清理失败，已仅修自有清理、重跑并验证恢复，不改产品或业务断言。
6. `python -m pytest ... tests/contract/test_b10_read_chain.py` 对冻结作者树：**3F/13P**，与原作者3节点完全相同。src/scripts/config/CI树、B10测试/helper不在包 diff，因此归旧基线缺口。该失败未删断言或登记为已修；完整本地模式仍不能称全绿。
7. `python -m ruff check --no-cache` 对卡指定工具/测试及新增 bounds：All checks passed。

## 清理、作者后续变更及剩余范围

末轮 ROOT 八文件与测试前 SHA 相同；自有 `.w13rv` 已全部删除恢复最初 absent，真实 Git 夹具 sentinel 保持且恢复 absent，无公司原件副本/DB/模型/外网/下载。收据 `pre-cleanup-final-bindings.json` 与 `cleanup.json`。

末尾无锁只读检查发现作者本人已推进至 `852dff283ed9f18dd4e0dd1376c4ca89a52b1795`，并有未提交 `delivery/w13/review.md/json`；**这些后续变更不在本次冻结审查中**，不是本 reviewer 写入，也未被清理。ROOT 应接收本报告绑定的版本，不把作者后续收据自动视为补审。

剩余：旧全量 Windows 长路径共因、既有 B10 ratchet、fresh 工区 config_doctor 缺运行目录、真实 CI 结果和真实产品全量仍由 ROOT 处理；不能以本地 fast pass 替它们签绿。本报告允许并线本次调度改造及 ROOT 修正，不代签 annual14、摘要、缓存或 RF 全流程。
