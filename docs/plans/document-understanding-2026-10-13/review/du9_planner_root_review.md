# DU9 PLANNER ROOT 接收节点独立审查

审查者：`/root/du9_planner_root_review`。范围为母卡固定的纯 POLICY→PLANNER 接口及 ROOT 合流 delta，不接管作者工区，不将组件通过等同于真 PDF、默认生产或正式摘要通过。

## 当前结论

**PASS，未解决 0。** 作者 `db126f24` 的独审收据不等于 ROOT 新的集成验收；本次独立审查使用主仓真实 `compile_geometry_policy` 输出，自建有限反例，未修改源码及 ROOT 测试。最终受审代码已提交 `a4ca0a8535d3b157e2cc7ff0dbdb8efe2ca65ee4`；审查者核对同名 JSON 的 11 个源/测试/fixture 工作区 SHA 均未变，提交 Git blob 内容一致（部分路径仅 checkout 的 CRLF 与仓内 LF 区别，两组原始 SHA 分别记录），未重复跑不变代码。独立运行时基线 HEAD 为 `f4ef8531e5ebe8c66b3a9b3da8df5a5f3162b8cc`、已包含同一冻结 delta；后续仅补发布文档无需重跑，源码/测试如变更则应对实际 delta 复核。

| ID | 级别 | 根因与真实反例 | 状态 |
|---|---|---|---|
| ROOT-R1 | P1 | 配额仅用 max_pages，忽略更紧的 max_requests。operating 前 50 页、project 后 11 页、max_pages=64/max_requests=2：前两候选都被 operating 消耗，后部 project 虽持保留额度仍 request_limit_exhausted。实际可执行容量必须同时受两个上限约束。 | CLOSED，按 min(max_pages,max_requests) 分配；原反例现为前部一次、后部一次 |
| ROOT-R2 | P1 | 把配额归因与同页请求语义混为一个窗口。相同 scope 外层 discover-only 覆盖内层 on_candidate fine，内层透明 quota=0；传全部覆盖 keys 后返回 fine=false，内层合法请求被吞。唯一计费归因应与覆盖窗口的有效请求组合分开，行政/取消窗口不能借其他窗口激活 fine。 | CLOSED，覆盖且 reserved 的请求能力组合，仍只向唯一归因扣一页/请求；cancelled 不供能力 |

## 独立实测

可复现脚本：`.planning/shared-reading-production/du9-planner-reception/reviewer_probe.py`。首次有限验证 **7 PASS / 2 FAIL**，保留 `reviewer-first-red.json`。两项失败对应上述 P1，不是测试收集或环境失败。

ROOT 修复后审查者**原样复放 9 PASS / 0 FAIL**，留 `reviewer-final.json`，未改独立期望。另亲跑 `python -B -m pytest -q -p no:cacheprovider -o addopts= tests/unit/du9_geometry_planner`：**55 PASS / 3.12 秒，exit 0**。此为实际 ROOT 独立结果，不引用作者旧 47 项来充数。

其余控例实际通过：已耗尽同一 WorkBudget 保持 partial/零 allocation；父文 scope 隔离及重复 ACK；JSON 恢复与连续调用等价；absent/unknown 不伪装业务否定；window 顺序稳定与 rule 因果绑定；行政 fine 抑制；输入不被修改。ROOT 额外新增真实可转债路由→resolve→compile→plan/admit 及 cancelled 嵌套能力负例，全部通过。旧请求上限测试改为单类夹具，继续断言实际 quota=1、第二页 exhausted、state.pages/requests=1；这是去掉错误的“行政先到必获公平名额”假设，不是放宽上限。原 64/64 手算 gold/fixture 未变。

性能抽样：50/300/1000 窗口各 10 次 admission，平均约 0.401/1.745/6.774 ms；plan 约 0.71/2.86/13.6 ms。每页重验与复制为 O(plan+state)，作者“几十至几百窗口亚毫秒”应限于特定机器/更小样本。现有 64 页上限下未实证造成 15 秒风险，本节点不因此扩成无依据的大规模重构或再加防伪门禁。

## 隔离与边界

0 供应商、0 原件读取/复制、0 生产配置写入；仅审查收据及自有 Temp sentinel，sentinel SHA/mtime 未变，Temp 已清理；作者工区只读。not_arrived 按作者明确契约表示 reserved-but-unused，不是“确定尚未到达页数”事实；部分/未知保持诊断。原生导航、唯一 matcher、真实表格工作耗费、source 单 parse、正式摘要和质量 heldout 仍由 ROOT 后续生产验收覆盖。
