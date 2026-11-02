# 当前状态 — 先完成解耦，再按仓派发

唯一入口本页/[机器状态](CURRENT_STATUS.json)，交接[HANDOFF](HANDOFF.md)，主计划[task_plan](task_plan.md)。

**用户已调整顺序：不在半解耦状态下推进模块施工。** 上一轮准备的RF/AUDIT业务计划已改为DEFERRED_UNTIL_DECOUPLING，尚未派发。ROOT先集中完成[解耦实施与验收](review/architecture-reassessment-20261102/DECOUPLING_FIRST.md)，通过后按实际接口重新校准各仓卡。

## 当前做到哪里

- 已有存储虚拟化、SourceRef/公开export和部分命令注入；过去有界门禁修复及CI通过保持有效。
- D0已查到真实耦合：RF raw reader/FF多入口部署绑定，多仓wire适配，CWP最终入库重复预算帽，RF内部SQL夹具和邻仓CI依赖。详见本轮两份独立报告。
- D1接口/隔离测试、D2代码与测试归位、D3集中组合验收尚未实施完成。本轮是优先级和实施计划调整，不能签解耦完成。
- 原T4/SEM、RF期间/ghost、AUDIT新attempt、真实摘要/恢复/RF采用与公司循环继续待完成，但不塞成解耦前置，避免范围无限膨胀。

## 唯一下一步

先由ROOT集中完成DECOUPLING_FIRST的D1接口/隔离测试、D2跨仓适配与测试归位、D3完整组合和独审；通过后再校准并派发RF/AUDIT等仓内业务PWF。当前不在半解耦状态下启动模块施工。

验收要求：本仓无邻仓源码/内部DB也能测试；公开端点可替换；协议核心/可选诊断兼容；FF→ET→CWP最终入库/verified-open全链预算与复用；保留原跨仓测试断言并在ROOT集成环境实际运行。不能靠skip或仅画接口图通过。

原件、生产配置/DB、旧R4和外来WIP保持。Dayu/IQS/Dashboard不动。只在大节点独审，不新增授权JSON或每helper签收。没有remote的仓如实本地交付。
