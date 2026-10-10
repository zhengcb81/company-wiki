# 三卡验收结论

**结论：源工程已验收、正常合入主线并推送、精确CI全绿，安装后独立测试通过。** 当前整体goal继续active，真实公司研究与AUTO公共接入仍待。

| 施工包 | 本次验收主要修复 | 发布范围 |
|---|---|---|
| M3-JSON/W02 | 持久化重放/各页原件绑定、主体/日期语义、分页冲突/重叠、精确整数身份 | CWP source层，解析1.0.1；AUTO路由归MAIN后续 |
| M3-USAGE/W06 | 未知费用保留未知/已知下界、坏诊断不吞原错、三层DTO一致、真实子进程失败计量 | CWP→FF→RF公开同级观测 |
| M3-FLOW/W07 | 期间进入事实身份、实际机制claim来源计数、精确财年窗口、现代schema共同输出验证、年度消费单一合同 | RF4.2.0 /输入3.9；3.7/3.8和历史兼容保留 |

原生TDD失败和修复记录在root_fix_register及各交接.receipts；未删测试或放宽断言掩盖问题。半年事实可作旁证或显式全年派生输入，不能直接作为全年金额。point存量与价格按明确业务角色保留。新回归使用既有快速门；未新增材料许可/人工签收/canary。

- CWP正常主线push2744PASS/168.74s；source HEAD f94b9ef0，CI38083232923 success。
- FF正常主线push646PASS+78subtests/6明确skip/67.77s；HEAD e1e3ad86，CI38083419792 success。6skip是3真实ET工具路径、2生产身份快照未在夹具、1本机symlink；不冒称该测试覆盖已跑。
- RF正常主线push260PASS+2subtests/28.79s；HEAD6883bf00，CI38083371392 success。
- 公共FF→CWP→RF离线跨进程101PASS，涵盖下载/复用/缺失/硬失败。各计数有交集，不能合计成覆盖率。
- 定点同步FF4+RF14工程文件到.agents/.codex两个物理根，共36文件；554其他安装文件SHA未变，.claude为.agents junction。独立18次fresh -I -B子进程验证真正导入installed模块，RF CLI→compute→strong→render、H1负控、fullFY/derived正控、FF成功/失败sibling及未知费用保留通过；590安装文件无测试变更，22测试产物随ownTEMP清理。
- 155保护SHA最终未变；原件、production配置、FF密钥、Dayu与RF assurance/output ownerWIP保留；本节点无新增provider/model/费用。累计USD20/2M及旧unknown继续执行。

## 下一步

MAIN先完成AUTO official JSON公共路由/投影复用与generation绑定，再按原九卡继续W04/W03/W05/W08/W09及真实公司复验。源工程工程绿不是公司研究通过；原三家四审、新三家泛化、池loop/条件八家目标不能提前签完成。

可重放安装探针见installed_probe的README/脚本；机器收据ACCEPTANCE.json与verification.json记录每次真实exit/日志SHA/恢复。发布后产生的Git/CI回执留下一节点归档，不为回执递归触发新commit。
