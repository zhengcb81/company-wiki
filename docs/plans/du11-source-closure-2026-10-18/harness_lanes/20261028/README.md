# W20 三条独立外包线：总控与接口

状态：施工边界已独立审查通过。**建议本轮先启动AUDIT-CHECKPOINTS和RF-ADOPTION两条；FF-REPLAY保留为可选后续包。** 三卡技术上可以独立并行，但不是都必须现在启动。ROOT继续CWP来源具体性/财务背景、单列QA物化、PDF部署及真实摘要/缓存/RF大节点，不把它们分散给外包。

| 卡 | 工区 | 交付 | 依赖 |
|---|---|---|---|
| [W20-AUDIT-CHECKPOINTS](W20-AUDIT-CHECKPOINTS.md) | `C:\Users\郑曾波\Projects\revenue-forecast-audit-w20-checkpoints` | `delivery/w20-audit-checkpoints/handoff.md`和`.json` | 冻结公共合同；不等其他两卡 |
| [W20-RF-ADOPTION](W20-RF-ADOPTION.md) | `C:\Users\郑曾波\Projects\revenue-forecast-w20-adoption` | `delivery/w20-rf-adoption/handoff.md`和`.json` | 冻结公共合同；不等其他两卡 |
| [W20-FF-REPLAY](W20-FF-REPLAY.md) | `C:\Users\郑曾波\Projects\filing-fetch-w20-replay` | `delivery/w20-ff-replay/handoff.md`和`.json` | 冻结公共合同；不等其他两卡 |

## 不冲突的边界

AUDIT只改审查技能/检查点，不改RF/CWP/FF生产；RF只改新的离线采用观察工具及测试，不改reader/模型引擎/Dashboard API；FF只扩现有矩阵及确有缺陷的FF薄adapter，不改CWP/ET。三个不同仓、不同physical worktree，没有共享可变资料库、配置、root计划或全局技能。ROOT保留跨仓真实调用、模型费用、全局部署、主线合并。任何一条需要扩大到别人owner，交具体counterexample由ROOT集成，不抢改。

产品接口由原责任层所有：SourceRef/SourceExport及用途/角色由CWP；收入模型与snapshot由RF；采集意图/工具路由由FF；审查finding由AUDIT。卡内报告只作诊断，不增加许可/签收/发布门。AUDIT和RF本次不得依赖对方新增report才能运行，均用冻结既有artifact及owned fixtures；ROOT之后可用薄编排串接。

## 已准备的事实与接收方式

三个工区从各自当前已提交HEAD新建，初始clean。RF主目录原有三项assurance/runs WIP保留；FF/AUDIT主目录tracked clean。没有拷贝CWP原件、下载或模型调用。RF工区已稀疏检出源码/测试/docs，避免重复检出约846MB已跟踪历史.planning产物，历史可从Git只读定位。准确setup见W20-setup.json；本表不宣称其他旧分支已经全部并线。

每张卡A调查冻结预期→B TDD/共同owner→C有界真实CLI/独立审查/全部修复/复审。A/B不等ROOT逐项签收。作者交付实现commit、final reviewed commit、有关file SHA、测试/清理收据、初审和终审，三卡同handoff字段规则，各自保有完整说明。独审须真实独立agent，作者不能自签。全部本范围问题修复才READY_FOR_ROOT_REVIEW；远端有配置则推卡分支，无remote不擅自创建。

ROOT接收顺序按实际就绪，不等三张齐备：核范围/最终版本→必要短接缝验证→合主线→精确CI→必要技能定点同步→更新总PWF。不会把新诊断工具完成当作真实摘要、供应商可达或公司RF循环完成。只在这一大节点审查，不增加小节点门禁。

## 为什么不是固定三条并发

2026-10-28用户指出固定三包的模板化倾向。ROOT接受：不能先定数量再找任务。AUDIT和RF直接服务当前正式内容及实际模型采用验收；FF恢复扩展有独立价值，但不阻塞当前阅读/摘要根修，优先级后置。今后先列剩余任务/依赖、消除改动重叠、核实际收益和ROOT接收成本，再决定0/1/2或更多条，允许不分包。READY表示可执行，不表示已经启动或用户已经分发。三张卡的具体施工合同未改，优先级由本段总控负责。
