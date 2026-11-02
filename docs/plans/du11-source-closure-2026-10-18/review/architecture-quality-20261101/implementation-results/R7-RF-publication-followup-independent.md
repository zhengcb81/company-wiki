# R7 RF 发布小补独立增量审查

结论：**PASS**。仅审本次 6 文件增量，不重签之前的真实业务验收，不声称完整 CI 已新跑通过。未发现需要 ROOT 修复的实质问题。

版本绑定：作者 `R7-RF-publication-followup.json` SHA 为 `7dcf9082044483e99a8bff359aaf69152e16af15482b1cdea640bc02c2459827`。六文件前后 SHA 均匹配，原已审 29 文件全部不变；四份 assurance WIP 与 `rf-commit.json` 中恢复后的 `wip_after` SHA 一致。完整 manifest、用例源码及清理收据见同名 JSON。

## 定点独立验证

正常宿主 Windows / Python 3.13.9，新建独立用例 **10 PASS / 0.74s**；未运行旧 29 文件组、690 行为集或完整 `--ci`。

1. 实际 `main([])` 与 `main(['--ci'])` 的计划均正确。日常只有 Ruff 和固定 12 个现有节点；CI 只有一次 Ruff、一次 public-contract mypy 和一次完整行为 pytest。测试用替身只拦执行昂贵命令，不替换 main 的 dispatch/临时目录管理。
2. 从真实 Git 基线 `a922305a87e6e5014edcceb4bc394c5b56a3d35a` 读取旧 `SMOKE_TESTS` AST，其 41 项逐项等于新 `CI_TESTS` 与历史 alias；不是只相信作者报告中的前后表。
3. 两种模式通过真实 Python 子进程返回 23，main 均原样失败，未误标 GREEN；各自临时目录退出后为空。
4. 实际 `_run` 的 0.05 秒 timeout 触发 `TimeoutExpired`，不会返回成功。CLI 未吞异常，因此仍是非零退出；没有新增忽略超时或 skip 开关。
5. 全部父仓 Git 上下文变量均去除，保留非仓绑定的显式 Git 配置；真实独占子 Git 仓解析为自己的 cwd。测试子进程关闭 dotenv、清空签名 provider，不能误调用用户真实签名服务。未修改父仓 Git。
6. 两个 confidence generations 的 v2 独立行重排后，audit/lookup 仍保留各自 revision/result SHA 配对。
7. 真实 v1 链重排仍失败；v1/v2 分别篡改 revision 而不重签行 SHA，audit 和 lookup 均拒绝。新测试确实区分新独立行与旧链，没有为了旧测试恢复全局链许可。

## 静态核查及边界

workflow 明确调用 `python tools/pre_push_gate.py --ci`，没有 `continue-on-error`、条件跳过或删减表。原 CI 工具/type 参数、子命令 300 秒 timeout 和作业 10 分钟界限保留；本轮没有抬上限。日常输出 `local_fast_pass`，没有冒充全 CI，通过固定节点减少重复工作，后续作者仍需运行变更相关测试。

修改只涉及工具、测试、workflow、工具 README；没有 RF 正常计算/来源/数字/发行 runtime 变化。stdout 尾部裁剪只用于工程命令日志展示，不修改预测、引文或来源结果。完整 runtime 与原 29 文件哈希身份未变。

一条 pytest warning 来自关闭插件后既有 `asyncio_mode` 配置，不影响所选同步用例。宿主 basetemp 每次由现有清理 hook 删除；自有 `tmp/r7rf-followup-independent-a3` 初始不存在，用例源码已归档到 JSON 后恢复 absent。未动 Dashboard、output、assurance、配置、安装目录、原件或收费模型。无 commit/push/index 写入。

ROOT 可正常提交推送该 6 文件增量；远端完整 CI 的结果仍由发布后实际收据决定。本独审到此 STOP。
