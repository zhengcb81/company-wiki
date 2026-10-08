# 本轮实测缺口的后续施工设计

本文件记录审计发现后的责任层改进，不宣称尚未实现的能力已经通过。当前优先完成三个真实执行及独立审查，不在审查期间临时改动外部Dayu或切换模型配置来凑通过。

## 0. RF正式产物跨进程确定性（Phase 5新增，P0）

固定套件已实际复现MSFT `confidence components recomputation mismatch`；`baseline_replay.json` 的 `process_seed_stability` 为FAIL。本轮仅固化测试，没有修改RF底层。

实施卡：先用同一MSFT固定输入在独立seed=0/1/2子进程生成/强复核，并增加含多组数量级权重的最小单元样本。RF `analysis/confidence.py` 的set refs遍历、权重累加和total/quality/freshness归约须有明确稳定顺序/稳定求和策略；强validator继续检查所有语义字段，不能直接删除components校验。来源/金额/期间/claimed-value仍精确验真，绝不重哈希旧input/snapshot。旧已发布产物如何兼容浮点最后位须显式定义并写兼容负例：最后位容差不能放过实质性分值/计数/覆盖率篡改。通过后按既有定点安装机制同步运行闭包，跑本full replay和相同定义compare，经济情景路径不变，seed失败变PASS，旧快照仍能正确识别运行版本。只做一个集中责任层+跨进程+真实样本验收节点。

### 固定回归入口（全部后续大改的共用验收）

`benchmarks/cross_market_rf/README.md` 定义71检查点、真实离线full、真实在线live、portable pack与compare。离线当前约93秒，不加入每次commit或日常CI；只有16小测试进现有Unit范围。真实模型刷新、新技能0–11研究与独立审查按该README的大节点卡做，不能用固定模型重放替代。工程改造完成后保留FAIL/BLOCKED→PASS的证据和未修项，而不是重设expected或删项目。

在线验证还显示FF吞掉producer的具体bounded拒绝，只留下 `ensure exited 1` / fatal。后续桥接应把安全的cause code（如bounded能力未提供、provider未启动）留给消费者；不暴露路径/凭证、不增加人工签收，不把这项诊断修复误当provider功能完成。

## 1. CWP-owned Dayu 有界桥（采集功能缺口，优先）

**事实**：旧 dayu_cli_v1 只提供 download 整流程，包含后续重处理；没有 metadata-only/预算入口。CWP ensure 在启动 provider 前拒绝。Dayu公开 `SecDownloader(client=AsyncClient)` 和 `HkexnewsDiscoveryClient(client=Client)` 支持注入；可以在CWP建立桥，不改外部项目。

**责任范围**：CWP adapter/transport及责任测试。Dayu目录零写；不让RF/FF了解物理根，不取消已有预算，不复制SEC/HKEX发现算法。

**实现顺序**：

1. 先写离线HTTPX transport预算测试：实际流读取累计所有discovery/redirect/retry/download响应字节，超量/超时中止，失败usage保留，零成本官方请求；SDK本身请求和日志不泄漏凭证。禁止仅在文件落盘后检查大小。
2. CWP-owned桥通过隔离Dayu解释器调用现有公开SDK，discovery只获取候选，fetch只指定primary；向既有JSON adapter返回真实candidates/receipt/acquisition_usage。SEC财年从真实reportDate与fiscal year end确定，不能拿自然年猜MSFT FY；HK保留FY/H1/Q1/Q3类别。8-K/exhibit旧行为须显式兼容或报告不支持，不能默默丢失。
3. 配置只增加明确的版本化桥接口，producer负责当前根/身份/SHA/类型和注册；发现/fetch共享deadline和remaining bytes，staging失败清理；不做全库Docling。
4. 一个集中大节点验收：两个市场真实缺失资料走RF→FF→CWP→Dayu新下载，再同请求0下载复用；检查raw统一存储、metadata/SourceRef、预算和全链程。独立tmp负例清理后恢复初始状态。通过后才发布配置与安装。

## 2. FF → ET能力路由（采集功能/套餐限制分开）

**事实**：FMP精确季度fetch可调用，当前账户无电话会权限；候选discover则本身不支持。FF的两阶段companion不能假定每provider有discover。0费用策略本轮先拒绝，US独立ET探测不能算FF集成通过。

**实施**：按ET公开能力描述明确 `discover+fetch` 与 `exact_fetch`；仅在请求identity/FY/Q精确时调用后者，真实provider错误/entitlement作为companion独立结果，仍不阻断财报。调用前核对当前用户配置及现有免费来源，不自行加订阅或任意换provider。实际TXT/JSON原语言登记CWP，SHA和期间验证后才成功；不翻译。

**大节点测试**：离线真实FF→ET JSON边界精确fetch成功/错误/超budget/无正文能力；配置缺失与套餐403均不变成空成功。真实账户再测一次，若仍无权限，报告功能测试通过/真实数据BLOCKED两个状态，绝不通过删测试或mock伪装真实可用。

## 3. SEC HTML 初处理（解析功能缺口）

**事实**：CWP当前narrative parser只支持PDF/TXT；MSFT raw SEC HTML实读成功，但本轮研究侧TEMP BS4解析不是CWP worker。

**边界补充（08:31 UTC）**：原R3正式微软TXT摘要已存在并可通过CWP/RF当前虚拟接口实读49证据；本轮不是证明整个Worker不存在或失效。此TXT published_date仍unknown，指定2026-10-08请求实际拒绝，不能伪填会议日来获得资格。后续先报告已有但日期未核的本地候选，区分“不存在”“不可按指定信息日使用”“provider未调用”，避免盲目重抓/重付费。

**实施**：CWP-owned确定性HTML规范化，保留原始bytes+SHA；paragraph/heading/table locator与脚注绑定、不执行script，不把导航与inline-XBRL隐藏重复算多份；选业务描述再走现有有限worker，复用统一任务库与预算。不要额外永存整份转换MD/图像。

**大节点测试**：真实MSFT10-K、合成SEC inline-XBRL表格/隐藏重复/编码/脚注负例。原文回放和locator能重定位，选片段预算有界，HTML精确财表与叙述不要混淆。测试资料在独立tmp，结束复原。

## 4. RF管理目标表达（语义可用性）

当前年度数字ledger不能完整表达季度及 mid-single/high-teens 等定性指引。暂以明确 unmodeled_data_gap/完整旁表保留，不乘4、不虚造中点、不误报公司没有指引。

后续用季度period和定性range型目标明确源口径；年度映射是另一个有来源/假设的转换，不覆盖原目标。添加真实季度、恒定汇率、区间、定性目标负例，确保无转换时不产生假年度比较。模型仍只产收入，不扩估值研究状态。

## 5. 验收与版本

本轮临时修复的运行文件SHA、RED/GREEN和新增输入枚举都写入记录。发布时记录精确Git提交/安装副本，不以只打印版本字符串证明内容一致；旧snapshot保留且使用原runtime。后续能力正式发布需明确运行版本和兼容矩阵，不能重哈希旧产物掩盖运行差异。

## 6. 输入单位与证据语义防错（本轮新增实际问题）

US错误不是算术实现错误，而是构建输入未遵守ratio单位；原input-schema只列shock类型，没有例子。MAIN补充明确四类型公式和5pp=0.05范例，不加日常审查门。现报告已显示actual requested/effective up/down与clamp，实际暴露了异常但执行者没有发现；后续构建helper使用显式人类单位转换，报告再注明参数unit/ratio语义，不重复新增已有列。相同错误输入独立重算仍会一致，不能当作人类意图已验证。

研究参数的rationale_support引用要包含支持需求/供给/增长衰减的具体上下文；只有历史基数不会自动证明未来增长区间。完整primary history、leading indicators、反证和outside benchmark分别引用；未来数值仍明确分析假设，不能把支持方向升级为精确事实。大节点抽取完整性和经济审查由独立agent完成，不引入小节点签收。

三个市场均发现“合法claim ID但文本不支持该结论”的共性问题：CN售后增收引用确认政策；HK增长引用半报收入表；US增长引用FY26基数。下一次改进输入构建方法时，先制作完整事实/历史、需求供给、反证、转换假设四列依据表，再产参数；会计政策只承担确认角色，outside benchmark只能承担相近机制/口径的参考角色。逐一写明哪些依据支持方向、哪些支持范围、哪些无法支持数值。复用同一支持材料是允许的，不能把同一摘录同时当支持和反证。仍只在正式输出这个大节点做独立语义审查，不增加每参数人工许可或额外发布状态。

HK v3复查又证明：同行公司“增长/竞争存在”的正确事实，不能标本公司增长根的独立one-step支持，进而自动升为triangulated。输入构建方法应在绑定时明确“本公司机制证据/同行类比/竞争反证”角色并采用现有inference_distance语义，不增加许可状态。一个集中回归案例同时核收入不变、peer类别、engine evidence_status与confidence limitations；金额完全不变也可能需要修复质量标签。最终仍在大节点检查文本是否真的支持所宣称机制，不能靠valid claim ID自动替代经济审查。
