# ROOT 自持任务 — D4 两仓测试归位与最终组合（已完成）

**这是总控收尾步骤，不是外包施工包。** 实现卡 D4-01 到 D4-05 都接收/独审通过后再做。AUDIT 没有远端；本地 ROOT 组合必须明确包含 AUDIT，不得把缺仓 skip 算通过。`company-wiki/integration/` 和 `tools/run_source_system_tests.py` 完全归 ROOT，施工卡不得改这些路径。


> **状态：COMPLETE — 2026-11-04。** D4-06 已由 ROOT 实施；D4-01～05 的提交均已接收。强制离线组合 27/27 通过，0 skip，五个消费者均有实际通过用例，AUDIT 两个必需 node id 覆盖，scratch 清理、源码版本前后稳定。独立审查 PASS。结果见 [D4 closeout receipt](../../../review/d4-closeout-20261104/README.md)；以下为已满足的原始验收契约。

## 第一段：AUDIT 两项用例归位

输入：`revenue-forecast-audit/tests/test_du6_current_cwp_bundles.py` 当前两项实际测试、其真实断言及 ROOT 公共 bundle contract。

1. 在 AUDIT 默认 unittest discover 中移除 `CWP_SOURCE_REPO` 条件 skip 和 CWP 私有 fixture/import。保留 AUDIT 本仓 portable contract 单元覆盖。
2. 在 ROOT `integration/` 建真实 producer→AUDIT importer 节点，通过现有 public bundle 请求/响应，不动态加载 CWP 测试文件。
3. runner 对 AUDIT path 显式参数化；不提供 path 时要明确显示未纳入，不把 RF-only 结果标为 AUDIT 组合通过。默认 CI 无法取得 AUDIT checkout（无 remote）时，远端范围照实声明；总控在本机拥有的独立工作树运行真实 AUDIT 节点。
4. 保持原两项关键断言和真实 producer/public consumer：不是删断言或改写期望。scratch 仍用唯一临时根且退出时清理。

## 第二段：一次 D4 跨仓组合验收

接受五条施工包的精确源码 commit/version，并组装当前入口：

- StockWiki `run-company`/`enrich-evidence`/`extract-document-signals` → CWP company source index → pathless SourceRef/open + narrative.
- RF prepare → 实际摘要 consume → claim/used parameter/formula/report，独立 endpoint，不含 CWP checkout/PYTHONPATH。
- 独立新进程实际 HTML/DOCX normalization + `understand_units`；没有 catalog/service/DB 的模块装载。
- FF→ET/provider fake HTTP→CWP transcript import literal wire→verified-open；长stderr+已flush有效native结果不失败；原 bytes/hash、身份/as-of/期间和实际资源反控正确。
- AUDIT 两项实际 producer bundle consumer 集成均在明确的 AUDIT root 执行。

组合以隔离临时 catalog、虚构公司、合成原件/源字节/本地端点运行，不访问生产文件或供应商，不用真实付费摘要。记录入口 commit/临时目录恢复与实际参与测试集合。各施工卡中的单项通过不是组合结果。

## ROOT 完成标准

五条卡已有自己的独立审查。ROOT 只需在汇合节点再作一次集成质量复核：写目录一致、失败 fixture 与原卡问题匹配、没有 private path/内部类型流到消费者、所有自动 skip 都不充当 pass、临时原件清理复原。发现问题时由对应 owner 修，再重跑受影响域和一次组合；无须重跑所有仓全量。

收尾后更新唯一 PWF 状态：D4-01..06 全关闭、旧 D3 版本历史保留、六仓真实接口边界/CI范围明确；正常提交/推送有 remote 的仓、记录无 remote 的 AUDIT 本地 commit。此时才能把 RF/AUDIT 从 `DEFERRED_UNTIL_D4_CLOSURE` 改为 READY；不会自动启动其业务改造。
