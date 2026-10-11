# W04 大节点超时只读诊断

状态：`DIAGNOSIS_COMPLETE_WITH_EVIDENCE_LIMITS_STOP`。没有修改产品、测试、门禁或配置，没有重跑全套，没有外部调用或费用。

## 已证实的原因

本次 `pytest tests/unit tests/contract -q --tb=short` 的范围不同于当前 CI，也不同于此前 116a39d8 的普通 push。它额外带入整个 manual contract 目录。此前 3206 PASS／195.93 秒的原始日志 SHA 与收据相符；不能把该耗时当作这次全目录的基准。

| 范围 | 当前收集项数 |
|---|---:|
| 全 unit | 3103 |
| 全 contract | 2524 |
| 本次失败命令范围 | 5627 |
| 精选 gate | 137：integration 45、contract 86、unit 6 |
| 正常 push 合并去重后 | 3234 |

本次命令多带了 **2438 项非精选 contract**，同时漏了精选 gate 的 **45 项 integration**；比正常 push 的唯一检查项多 2393 项。新 unit 28 项与旧 3206 → 当前 3234 的差额一致。当前 CI 分两步执行，6 项 unit 重复属于既有行为，此调查没有更改。

## 耗时与死锁

全目录含 parser-liveness 的真实 45 秒成功慢解析与 10 秒超时解析等重型恢复检查；精选 gate 不包含这些例子。只读源码确认其设计，**没有实际执行或将静态等待数值当成本次测量**。并发负载、具体慢例、完整目录的合理耗时区间均未测得；目前没有新代码死锁的证据。

原 driver 在异常前没有保存 `TimeoutExpired.stdout`，也没有落盘 UTC／PID／receipt，所以无法恢复卡在哪项。该缺口不能用猜测填补。以后应在启动前把 stdout/stderr 流式写入自有文件，成功、失败、超时都保留日志、SHA、命令、cwd、UTC、PID 和 duration。

## 进程与清理

普通沙箱 CIM 查询失败，不能据此声称没有进程。经过批准的只读精确签名查询，未找到本次 `pytest tests/unit tests/contract -q --tb=short` 主进程；没有输出其他进程命令。原 PID 与时间缺失，不能唯一归属任何孤儿子进程。**没有终止任何进程**。

收集器只执行 `--collect-only`，完整 stdout 已保存为 `collect-all.log`、`collect-fast.log`；test tree 精确解析为 5627／137。collection.json 保留原始计数器未识别 tree 输出这一细节，准确解析结果记录在 review.json，没有重写原证据。自有短 TEMP 已校验绝对路径并清理；生产配置、gate、CI、pytest 配置前后 SHA 一致。

## 建议的下一步

ROOT 按当前 CI 范围做一次正常 unit＋精选 contract 发布验收。手工重型 contract 保留给对应风险的大节点，不再无差别整根重跑。不要以这次超时为由修改产品、删测试或放松断言；若以后对应重型节点再出现超时，再凭完整日志定位具体根因。

机器可读细节、工具记录编号、原收据路径与 source/log SHA 见 `review.json`。
