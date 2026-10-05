# N4C 私有请求降重与政策跳过收据

配置不变：MiniMax-M3/国内端点/max_completion_tokens8192/temperature1.0/reasoning_split=true，使用现有Config.load入口。当前模型prompt1.3.0、private request schema1.1；selector0.3.1，parser0.1.0。SourceRef/Narrative公开wire不变。

| 真实文档 | 精选正文 B / spans（不变） | 同配置旧→新 HTTP B | 当前保守token预留 |
|---|---:|---:|---:|
| P01 年报 | 10,551 / 96 | 33,146 → 15,805 | 24,125 |
| P04 招股书 | 10,391 / 160 | 45,471 → 16,543 | 24,863 |
| P07 IR | 3,920 / 11 | 10,257 → 8,035 | 16,355 |
| T01 英文TXT | 1,809 / 14 | 8,064 → 5,810 | 14,130 |

计算仍为实际HTTP UTF-8 bytes+128+配置输出上限。空间数字只表示发送输入，不是供应商实际token或已释放磁盘空间。所有正式定位/角色/quality flags保存在canonical selection，模型仅收到短alias和同值默认项；模型返回后恢复正式引用，持久request hash同时绑定本地映射和HTTP正文。原件SHA与独立目录恢复均通过。[测量JSON](n4c_offline_compact_2026-10-05.json)

英文policy旧标题规则缺失已复现并修复：[前测](n4c_policy_fixture_2026-10-05.json)、[后测](n4c_policy_fixture_2026-10-05_after.json)。真实SourceCatalog入库后通用IR类型/原英文标题，经正式handler成功skip；不靠修改中文标题过关，业务无候选或不完整扫描仍不自动跳过。

134项集中Unit GREEN；3实际CLI/Worker/本地HTTP E2E GREEN，包含配置、canonical引用、原语言、幂等预算与英文政策零模型调用。没有外部模型HTTP或下载；未生产删除。RF主线8a153f33/owner两文件保持原样，P5外包写集未进入。

下一有限真实尝试先核当前配置的套餐/价格，再处理P04+policy：剩余26,340tokens/$0.083420只保证这份最大请求可准入，不保证四份同时完成。拿实际usage及CWP/RF公开read后滚动计划。官方[Responses token估算接口](https://platform.minimax.cn/docs/api-reference/responses-input-tokens)未用来替代当前Chat硬上界；国内pricing页面未取得，未编造国内费率或改模型配置。N4C仍待真实provider/final/消费者验收。
