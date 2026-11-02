# 当前状态 — D3解耦独审通过，发布收尾

唯一入口本页/[机器状态](CURRENT_STATUS.json)，交接[HANDOFF](HANDOFF.md)，主计划[task_plan](task_plan.md)。

**D0–D3工程已完成。** ROOT已通过[解耦独审](review/decoupling-20261102/independent/review.md)，普通测试与真实组合已归位。[发布记录](review/decoupling-20261102/release.md)单独列实际commit、推送和远端CI。RF/AUDIT仓内业务未派发、未开工。

## 当前做到哪里

- RF原文/摘要两个端口可替换；FF的六个操作走统一连接；StockWiki保现有独立reader。日常CI没有邻仓源码/DB依赖，ROOT[组合入口](../../../integration/README.md)负责当前真实进程链。原25个跨仓套件的487条断言保留，历史canary/签收只作显式重放。
- 已移除JSON排版/重编码一致性阻断、本地输入和末端入库重复固定帽。保留实际字节SHA、来源身份/期间/as-of、真实资源上限。正常未找到与进程故障分开，22MiB额度下大于17MiB原件入库/实读、真实16MiB超额和再次零下载均验真。
- RF隔离712通过，FF946，StockWiki110，AUDIT43，ET95；CWP受影响契约30项；ROOT组合39项全过/124.35秒/零跳过。真实A股半年报只读，原文SHA、期次和测试库/配置前后一致。三个RF/FF技能入口已定点部署并新进程实测，重复同步零写、临时根清除。
- 旧RF日检仍可能追加诊断；不在当前计算、提交推送或CI入口。初始WIP完整保留，新增264字节没有回退或暂存。旧任务查询受Windows系统访问限制，未声称全局调度已退休。
- 原T4/SEM、RF期间/ghost、AUDIT新attempt、真实摘要/恢复/RF采用与公司循环继续待完成，但不塞成解耦前置，避免范围无限膨胀。

## 唯一下一步

完成正常主线推送并记录精确CI后，ROOT恢复T4来源父链、SEM-QUAL-01限定语义，然后做新版真实摘要、缓存恢复和RF采用。RF/AUDIT已有仓内PWF按实际公开接口校准，等待总控明确分工；本轮无外包派发。

工程通过不代替真实语义或公司循环通过。旧T4/SEM、RF期间/ghost、AUDIT新attempt、真实摘要/恢复/RF采用及固定公司仍按既有顺序闭合。

原件、生产配置/DB、旧R4和外来WIP保持。Dayu/IQS/Dashboard不动。只在大节点独审，不新增授权JSON或每helper签收。没有remote的仓如实本地交付。
