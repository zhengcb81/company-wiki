# DU6／DU7 ROOT接收与共因修复

## ROOT当前状态：DU6三包与DU7-PDF接收并线完成 — 2026-10-16

用户确认后已接收四个干净交付；DU7-ET-EXTRACTION仍IN_PROGRESS，未进入其施工目录。RF、AUDIT、FF、PDF的作者完整历史及ROOT修复已正常合入各自主线。RF/AUDIT技能已定点同步（三路径RF为两物理副本）；AUDIT无origin，明确仅本地并线/安装。RF/FF/CWP远端发布与精确CI状态随后归总，不把未观察CI说成绿。见[完整接收](review/du67_reception.md)、[紧凑收据](common-root-quality-evidence/du67-reception.json)。

大节点结果：RF199PASS+119subtests，原生季度/默认未建模/带符号目标/旧严格数值边界统一；AUDIT90PASS+15实际CLI/16checks与当前CWP公开v2/v3两项联调（v3临时合成原件经真实来源/公开读），同次正文/SHA/attempt及单8MiB物理读取、unread、投影上下文与一对一库存修复；FF305PASS，复用已有bounded process owner，删除重复taskkill/等待，不改0.2s/<5s和case30/batch180，原子不覆盖输出；PDF43短测、557旧兼容PASS/24SKIP，另两项因ROOT漏检出旧资产失败，补资产后原两项2PASS，未改断言。

PDF独审3P1/3P2已修，真实名创p12单parse所有ref真切片，2M消耗1,162,753；深页223/224因上游64页capture仍未覆盖，正式生产TABLE/摘要/消费者接线和语义验收没有关闭。已保留全部原RED/失败/未知，作者新增错误假设有原zip及独立理由，不改旧binder/layout/研究金标。不新增人工签收、许可文件或逐材料审批。0新增供应商，原件/配置保持。

ROOT原STATE效率、parent composition和跨仓E2E本地进展完整保留，未混入这四包并线；后续纳入下一主线节点。默认0.8、新0.9默认v3均未切。旧20条8/6/6、PD5/Matrix业务遗漏、母G2/G4/G5/原三→新三及八公司审查loop继续OPEN，不能以组件绿称项目完工。

**Next Step：** 完成本次远端发布收尾，随后将来源层深页捕获/原生TABLE闭包与已有STATE效率/parent组合统一接入主线；复用正式worker→公共读→RF/AUDIT做真实配置摘要和独立语义holdout验收，等待ET交付。仅原A/B/C大节点，无新增小节点许可。

---


## 精确提交

- rf: author `86ca29411fbed1eaf2958b2eff579395f7d151a7`, ROOT `2a68c6878c8bfd2b88c208d1bbc87540dedd6676`, merge `033f396279aeb9980f57dbefff85b69007fcb478`
- audit: author `c603d23d6ba731ed2f510f30a731f6ef3f3b43d3`, ROOT `8fd5a33949735422abbf3a5f39108d1fc606edb1`, merge `6ae3235db938182e0098961414348d9dd1b6fbab`
- ff: author `ff08a8e04f2ae146e42daf9b36710b3ef1f47d89`, ROOT `29dd3453c7b729c16e5fc8554d4d5fa8006106ae`, merge `d11d5f9e3e766521c84787b691f935466bf32f47`
- pdf: author `caca0eb61e657bead05609ec963e00c48502761f`, ROOT `cbd3024fe738fad01f07c51a2ab0ec0d3b6e11fb`, merge `250d1a0e759b5bd180eb45ac2bfaadc9fc526612`

## 接收工程错误记录

PDF helper首次把Git rename展示当成白名单少文件，第二次对已暂存删除路径重复git add，两次均未形成提交；按--no-renames及只添加需要更新路径修正后正常通过，未放宽文件白名单。PDF集中两FAIL来自ROOT稀疏资产缺失，未删改测试。FF最初180s harness超时原因unknown，单独保留；后续5.247s回收实证按唯一process owner修复。
