# M3-USAGE：三仓下载用量与原因完整传递（lane_id=M3-USAGE）

## Goal
让成功、失败、复用都能沿 CWP→FF→RF 看见真实已观察的下载开销与业务结果；
response_bytes=已观察响应正文 wire bytes；费用/计数未知不冒充已知 0；
旧 acquisition_usage 1.0 与 acquisition-failure/1 语义不被静默改义。
总卡：docs/plans/cross-market-rf-e2e-2026-10-08/phase6/m3_parallel_handoff_2026-10-10/acquisition_usage_chain.md

## Worktrees / Base
- CWP  C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/company-wiki   base 3c791e3c2a16c12627cc25d0bd8681cc9458e48b
- FF   C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/filing-fetch    base 41ba0150c9c634f6021c9346744cada391ec2c4c
- RF   C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/revenue-forecast base 0c248d9a07a2dd7a2c756946d88507479d5e9d15
branch 全部 codex/m3-acquisition-usage-20261010。唯一总执行 PWF=本目录。
Seed 来源：W06 前期骨架（docs/plans/.../m3_root_implementation_2026-10-10/W06/，骨架无实质内容，已按总卡扩展）。

## Phases

### Phase 1: 状态固定与消费方映射
**Status:** complete
- 三仓 HEAD/status 记录（progress.md）；精确 write set（INTERFACES M3-USAGE 清单）。
- CodeGraph consumer map：acquisition_usage/acquisition-failure 从 CWP producer 到 FF/RF 消费者的完整路径。
- 旧错误通道（RC14 limited causes）接受证据定位，不重做。

### Phase 2: INTERFACE_CHANGE.md 合同冻结
**Status:** complete
- 实际字段、完整/下界/未知三态、success/failure/reuse 样例、旧版本兼容、CWP→FF→RF 消费者路径。
- observation sibling 或显式新版本二选一，先定再写码。

### Phase 3: CWP RED→GREEN
**Status:** complete
- RED：bounded loopback provider，metadata GET×2 + body GET×1，gzip wire < 解压 entity；当前 success 投影不完整。
- GREEN：同一 operation 的 success/failure/reuse 安全 DTO；已知 HTTP status/content-type/content-encoding 有限投影；未知 null/unknown；预算/清理异常不抹 primary cause 与 usage。

### Phase 4: FF GREEN
**Status:** complete
- source_candidate/缺失/失败保真投影 + 原 business status；不重新校验 MIME/身份。

### Phase 5: RF GREEN
**Status:** complete
- client→source_preparation 继续传递；不补网络账。

### Phase 6: 公共 E2E 离线链
**Status:** complete
- 实际子进程 CWP CLI→FF CLI→RF public client/preparation；生产 provider 映射换 TEMP loopback 配置；无隐式 dotenv。
- 至少两不同 source/市场控制；stdout/argv/exit 全存。

### Phase 7: 控制矩阵
**Status:** complete
- 第二市场/格式、reuse 零 GET、pre-launch 失败、mid-body 截断/timeout、未知费用、metadata 错误、cleanup secondary error。

### Phase 8: 恢复
**Status:** complete
- TEMP 初始目录逐 SHA 恢复，额外原件清除，restore receipt。

### Phase 9: 提交/推送/交接
**Status:** complete
- CWP→FF→RF 顺序正常 commit/push 自己分支，核 exactCI；runtime SHA 闭包；HANDOFF.md/handoff.json。

## 排他边界（提醒）
禁碰 JSON/schema/metadata/canonicalwriter、AUTO 模型与存储、RF drivers/contracts/schema_compatibility/revenue_report、assurance/output、installed skills、所有 key/config/raw。
source_catalog/cli.py 总入口留 MAIN；只交 source_operation 的 DTO 及 CLI 最小接线 patch。
测试只用专属 test_m3_acquisition_usage* 与已列现有失败用量责任测试。
0 公网 provider/模型/费用；loopback 只允许自身地址。scratch64MiB/persistent32MiB/final2MiB 或既有更小界。

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

## Next Step
无（lane complete；MAIN 集成与真实大节点见 HANDOFF §7）。
