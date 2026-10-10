# 原三家 M3：当前修复后的真实新执行

## MAIN最新交付状态（2026-10-10T14:09:19.972711+00:00）

12份独立报告已完成，专家诊断包已冻结且23份内容SHA全部实核；157项/26共因/9卡。计划交付已接受，工程及研究目标未完成。本地master45533e88的配置/计量改进待主线发布与精确CI；失败正文及真实再验仍待。详见root_plan_main_delivery_observation.json及../m3_root_remediation_2026-10-09/task_plan.md。

状态：三executor封存partial，12独立报告已齐；共因专家正在冻结新9卡包。已发布CWP13a/RF0c精确CI绿；模型配置/计量候选62770fea正常支线发布并合本地main45533e88，remote main/精确CI待归总。生产配置不变、失败final/真实及研究复验未完成，当前goal active。

## 最新协调状态（2026-10-09T22:17:16.174061+00:00)

以 first12_review_observation.json、当前task_plan/findings/progress和新根因包为准。下面来源执行与预算部分是本M3实际冻结交接，不能把它当后来修复已重跑。新JSON契约/index已核对SHA，并纠正2508385旧定位及36395非空answer。新共用包以独立专家最终交付为准，草案不代表施工完成。

## 已封存交接与当前工程调查

- 腾讯：[executor交接](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-hk-00700/execution/execution_handoff.json)、[manifest](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-hk-00700/execution/manifest.json)、[协调员只读封存观察](hk_executor_seal_observation.json)。manifest SHA2b6b9d56e6e59b47a7316266149efefe36bb67351281a026d92fe5dd041d6252，执行partial/554引用，四审已交付、研究仍partial。
- 中微：[executor交接](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-cn-688012/roles/executor/handoff.md)、[manifest](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-cn-688012/execution/manifest.json)、[协调员观察](cn-688012_executor_seal_observation.json)，605文件/partial。
- 微软：[executor交接](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-us-msft/execution/handoff.json)、[manifest](C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-us-msft/execution/manifest.json)、[协调员观察](us-msft_executor_seal_observation.json)，218项/108capture/partial。
- [十二审查调度](review_dispatch.json)记录实际agent与尚未启动的角色，不代表接受。
- [四审交接](REVIEW_HANDOFF.md)；按剩余slot分批，各角色只写本报告，不跨角色读初稿。
- [电话会角色/QA版本化施工](transcript_speaker_root/IMPLEMENTATION.md)：原件真实RED、隔离0.3实现/90责任+58共享快测green，支线8c154b11正常commit；主运行时未切换，选择仍只覆盖4/6QA，不能当全部源问题关闭。
- [模型配置与计量共因](model_output_runtime_root/INVESTIGATION.md)、[有界HTTP解码调查](http_content_coding_root/INVESTIGATION.md)、[官方JSON来源施工细则](official_json_source_root/IMPLEMENTATION.md)均按实际材料定位，未实施部分明确待四审/专家整合，禁止盲收费重试或假SourceRef。

## 本次与封存旧执行的关系

- 固定 CN688012 / HK00700 / USMSFT、as-of=2026-10-08。旧执行、输入、12审查报告和64finding保持封存；新运行不覆盖它们。
- 当前修复已正常并主线；CWP 88c4f29a 源码发布 CI37973817060成功，最终文档7caedd19；RF5dcd19be CI37972797793成功。运行使用实际当前安装/源码，精确字节由 `runtime_observation.json` 记录，不能只信版本号。
- executor 不读旧模型/预测答案来构造新研究。`w09_material_coverage/initial_inventory.json` 提供来源、发现线索和18项材料任务，旧审查问题是协调员后续核销依据。
- 复用每公司的既有 mFresh 隔离来源库和公开 SourceRef；新 run、AUTO、工作目录、TEMP、RF registry/output 分开。不能复制生产222MB catalog或整套原件。通过已有公开接口追加来源事实、规范化资料和原文，不能SQL改身份/公开日或改原件。旧来源版本/断言不删除。

## 预算与配置

`budget_observation.json` 重新只读核对三份原生 AUTO：29,572 tokens /31,894 microUSD已在母账计过，本次追加为0；母账236,614 tokens /151,565 microUSD估算，历史unknown7、FX2,764及旧 acquisition unknown保持。上限仍累计2,000,000 tokens/USD20，不重置。

原每公司120,000 tokens/USD2额度扣除其已有原生消耗后作为这次剩余额度；每家公司内所有新有限批次共用该剩余量，不给每份文档重发完整预算。三家公司总量仍受母账限制。新 unknown先保留和计量，不能盲重放。实际定价/供应商费用与估算分别记录。

本次选择当前已经配置的 DeepSeek Flash；`Config.load(llm_provider="deepseek")` 和 `model_options_from_config` 产出实际模型/温度/max_tokens等，不猜默认、不私自改8192。继续用已有版本化保守峰价预算；2026-10-09复核[官方定价](https://api-docs.deepseek.com/quick_start/pricing/)的Flash峰值input/output为每百万tokens $0.30/$1.20，低于现有保守0.333334/1.333334估算。无缓存/低峰折扣或免费假设；凭证只记环境变量名/可用性，不记录值。

## 三执行接口

1. 读取新scope、当前 revenue-forecast-audit 的 executor/workflow/artifact-contract、当前 RF/FF SKILL及各仓AGENTS。先以本次身份/期间实际调用 RF source_preparation → FF → CWP；已存在先复用，真缺才通过当前provider有界下载。
2. 按W09每公司的六项来源动作，查原件、真实日期/同SHA、正文及重要新增条款。IPO/发行/可转债/投资者关系/电话会/演示材料按价值和业务需要处理，不机械各下载一份，也不把所有类型写N/A。SSE跨公司QA要分公司、完整分页和问答归属；搜索片段不是已获取原文。
3. 当前配置的有限叙述batch实际执行原语言解析、业务选择、摘要、公开bundle读取，并证明本次研究实际使用。对年报/H1/电话会/演示中有价值内容进行对应处理；原文与精选摘要保留逐定位语义核对。初次成功后同规格新AUTO/新run复用检查0模型/费用；不要以文件存在冒充复用证明。真实公共locator回放仍有解析成本。
4. 按RF当前全流程建模并真运行lint/hash/validate/compute/render/strong gate/sensitivity/snapshot/registry；所有可包装调用由audit capture先留存并实际消费确切输入。失败也留账，输出完整步骤与fact→parameter→formula来源映射。
5. 研究校准遵守现有W13/RF合同：独立来源同口径/期间/币种/单位，产品证据对应产品，不把行业规模或单季guidance当所有未来增速证据。不充分就减少自由参数/缩短有支持的显式期限，诚实给条件范围；不能靠假设标签或算术正确冒称实证。共有需求/供给/确认时点约束用现有公式算联合stress，不把单因素敏感性相加。
6. 封存交接：全部工具/UTC/调用前输入、文档与来源矩阵、数据事实、管理目标/反证、真正费用和unknown、真实RF结果与trust声明。executor不自己签收、不改源码/技能/共享PWF/生产config，不看其他executor初稿。

## 隔离与保留

三家公司目录互不重叠，外部Dayu代码不改；FF、ET、StockInfoDLSimple按当前能力调用，未提交key/assurance/output owner内容不动。每次新batch用其独占工作子目录，不启动全库或常驻转换。

`initial_environment_inventory.json` 留存三公司原件/旧配置的SHA、size、mtime与新执行子目录初始不存在状态。新AUTO/work/registry和新的原件保留到四审结束。MAIN最后对照原库存，只清确实属于本次测试且原先不存在的派生物；需要保留的正式财报原件先经来源接口纳入永久存储再清理测试副本，不能丢原件。测试不写生产 source_catalog.yaml。

## 大节点验收

三executor封存后四路独立reviewer逐公司审查全部步骤与每个事实/参数/结果，原报告不改、新报告独占。MAIN汇总64原finding逐项处置，新问题回共用根因，不用工程绿或结构check替代研究质量。发现确切阻塞时仍完成不依赖它的工作，保留partial与影响；重要来源和模型问题未解决不能进入M4。无新小节点人签。
