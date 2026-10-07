# 完整核查：消费者历史日期合同对齐

RF main6e6b817a、StockWiki master3fe5008只读；CWP848cacf/user配置3609e707保持。StockWiki有独立quick-scan项目，不覆盖其目录/提交。本单属于总PWF，不新增人工review门或日常长测试。

## 发现与要求

CWP已按G1约定用来源公开日决定as-of；下载日期仅是来源事实。实际StockWiki `_narrative_bundle._manifest` 与RF `company_wiki_narrative_contracts` 仍把retrieved_at晚于cutoff拒绝，且StockWiki旧测试把“未来”定义为未来下载日。需先用真实CWP发布/公开CLI证实差异，不因静态怀疑立即写外仓。

合同：2026-08-01公开、2026-09-02下载的原文，在2026-09-01查询可用；2026-09-02才公开的资料不可用。未知/无效公开日、错误身份/期次/SHA继续拒绝。retrieved_at保留字段与合法UTC格式，既有wire不改；“当时本机是否已收集”的严格回放不是默认模式，不新建开关。

## 集中顺序与写集

1. CWP新opt-in手动Integration，六用例（RF/StockWiki × 早下载/晚下载/未来公开）。真实handler/outbox发布、CWP公开reference/read、两消费者当前CLI；模型为既有本地Replay，不外发。RF只读导出已提交六模块到测试根，StockWiki显式只读PYTHONPATH和-B，所有请求/配置/DB/raw均在独立tmp，finally恢复。
2. 小收据记录实际producer/consumer返回码和静态错误、当前HEAD/保护/清理，不保存正文、密钥或未知数据。RED需发生在语义断言，不因模块或夹具缺失。
3. 若证实差异，先在独立测试副本给出最小修正并以相同用例证明GREEN。不要修改原件或伪造retrieved_at迎合旧消费者；不把测试副本修正声称为生产已修。RF/StockWiki owner的落地方式另明确，不抢现工作树。
4. 更新完整需求表，保留未落地项。日常CI不加跨仓六CLI/真实PDF长测；本仓只提交测试、细则与收据，不能把旧绿收据当本缺口已解决。

## 当前状态

真实CLI已证实4pass/2fail（25.36秒），仅晚下载两消费者RED；最小独立副本相同六例6pass/25.17秒、Ruff绿，未来公开反例仍真实拒绝。当前两仓代码未改，不能宣布生产修复。原owner不写策略要求先明确授权，已异步询问；此期间完成本仓证据、可审查diff和两张互斥卡：[RF卡](harness_lanes/revenue_forecast_asof_alignment.md)、[StockWiki卡](harness_lanes/stockwiki_asof_alignment.md)。两卡未派发、不自动开新harness。首轮6个dict/to_dict夹具错误及首次副本导出未终态/缺已提交CLI provider配置的3个环境失败不计产品RED；依赖完整后真正GREEN。正式[小收据](harness_lanes/results/final_consumer_asof_audit_2026-10-07.json)保存当前/提案区分。
