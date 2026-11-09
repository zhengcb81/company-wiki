# 进度

## 2026-11-09 计划形成

- 读取三个 Dashboard owner handoff，共 13 项反馈。分别安排独立 agent 核对代码、Git 版本和原回执，总控归总责任、依赖及验收。
- 只读查询三个 owner 远端主线。确认本地旧 CWP master、FF 本地已并接口和 RF 候选的发布状态各不相同。
- 采用上一轮隔离验证。CWP 基础浏览三提交叠在当前主线，15 项通过。原文流式兼容性观察中，两条读取路径均按当前主线语义报告实际策略指纹。
- 记录阿里六路线与 E12 的不同故障。更正 MDB 成功报告误用失败尝试登记命令，保留成功发布所需原生证据的审计。
- CWP 本地只读探针复现 HK FY2026 原件已登记但历史市场事实为空。FF 只读代码检查定位缺键/null 分支差异，以及 Dashboard 的 reconcile 漏传非默认配置。均分派到实际责任层。
- 当前已完成规划。下一步为 CWP 基础浏览隔离候选，以及 FF/RF 各自的主线发布范围复核。此轮执行范围是只读核查与本独立计划目录。

## 2026-11-09 启动 P1

- CWP 远端核对 `5e4bc087b`。隔离 worktree 挑入 G-CWP-01 的三提交，暂为 `fcceba302`，净新增 5 个预期文件。独审核对实际 CLI、版本重开和 Dashboard 消费。
- FF owner 已核实 `bf7e1dab` 远端和 `154c292c` 的窄快进候选，复查中断和幂等绑定；RF owner 已核实 `90c562ac` 远端，开始最小公开端口移植。
- 独审复现深 stdin、深 snapshot 和无效根相对定位三个反例。CWP 用共享 JSON 及定位工具修复，保持原文实际验真在 Reader。34 项浏览与复用组合、Ruff、469 源文件 mypy 和正常提交钩子通过。精确候选为 `e2a448cc902c1e5f4e49ca02e6ba8515f25331df`。
- Dashboard 真实 adapter 的语言筛选当前发标量，CWP /1 公开合同使用列表。由 Dashboard 写域加回归并转换。该适配缺口与已知 FF 非默认 connector 恢复配置分别测试。
- FF 实测旧并发提交双绑定和半写指针永久 busy，开始用实际中断和跨进程测试收口。RF 的作业首组 33 项通过，正按主线原生捕获时间语义对齐目录夹具。
- CWP 精确候选独审 59 项通过，远端候选运行 [42607965033](https://github.com/zhengcb81/company-wiki/actions/runs/42607965033)。正常 pre-push 18 项通过。
- Dashboard 本地消费基线 `17da5241` 领先实际远端 `main ced8b88` 110 个提交。远端具基础 CWP adapter，缺 FF job adapter。两处兼容修改在单独 Dashboard 工作树提交，组合固定实际消费基线。整段 Dashboard 历史另归其发布计划。
- FF 发现 companion 重设调用截止时间，将与前一阶段复用 FF owner 同一 deadline。原七提交含机器部署记录，正式候选只取可发布代码、合同和测试。RF 检查旧 B34 对 CWP 私有文件和已移除校验函数的依赖，保留源证据真实性，转接现主线公开合同。

### 第一批 CWP 已发布

- `e2a448cc902c1e5f4e49ca02e6ba8515f25331df` 的 [候选 CI](https://github.com/zhengcb81/company-wiki/actions/runs/42607965033) 通过。独审复跑 59 项。远端 `master` 已从 `5e4bc087b` 正常快进，二次快速钩子 18 项通过。源码增量仅基础浏览接口、合同测试和原交接，两个浏览 /1 公开协议可供 D00 验收。
- Dashboard 适配器候选 `4b30e1d9` 和 `8e3231c3` 分别转换基础语言筛选列表、给 FF reconcile 传同一 connector。相邻回归 72 项通过。临时合成目录经真实 CWP 命令验证语言筛选、空结果、原件重开及 SHA。候选固定在 Dashboard 自己的本地消费基线上。
- FF 第一版最小候选 `57351d00` 的作者定向 98 项、Windows 组合 902 项、Ubuntu 51 项通过。真实 FF/CWP CLI 用临时目录验证零下载的复用及只读恢复。独审又实证 ensure 无回执被当已知零开销、未知 reconcile 无结果仍允许 retry，以及伴随采集超过实际请求 deadline。主线等待同一 FF owner 根修后的候选。
- RF Job `ff1c69e0` 已提交在独立 RF 候选，33 项协议与 2 项真实公开 CLI 端到端通过。通过受控公开来源进程执行实际 RF 源准备、计算和发布，覆盖幂等重放及同长度原件篡改拒绝。目录候选继续收口。
