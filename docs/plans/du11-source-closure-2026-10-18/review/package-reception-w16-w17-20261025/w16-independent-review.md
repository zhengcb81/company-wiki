# W16-RF-BASIS ROOT 独立接收审查

日期：2026-10-25。第一轮结论：**REQUEST_CHANGES**。作者的单一 owner、DU5 复用、输入/输出绑定和真实 CLI 接线成立；B03/B04/B06 的语义闭环尚未完成，不能沿用 handoff 的全部 PASS。以下第一轮 finding 保留，ROOT 修复后的复核应追加，不覆盖原始失败。

本报告只验工程组件及合成输入行为，不代签真实公司 RF、ST-A02、原始来源内容或来源真值。

## 审查对象与绑定

- 作者工区：`C:/Users/郑曾波/Projects/revenue-forecast-w16-basis`，分支 `codex/w16-rf-basis-20261025`。
- 主仓只读 HEAD：`094d55ad884e4a886b1537c0e76f3a0bede16ca2`。
- 完整审查范围：`094d55ad884e4a886b1537c0e76f3a0bede16ca2..611b1d62b2eb3228df037c95145a1d8d8d1f01d8`，27 文件，+2627/-24。检查产品、测试、交付报告及 PWF；中央施工卡、COMMON 与作者报告一并读取。
- 功能修复 commit：`cb60bd21122d63e1724213cee79281c0c1e33e42`；最终代码 commit：`95c25c4b7be7cdf89d3356054fc60fb28be4c875`；两者之间只有 lint 注释变化。95c25c4b 后只有文档变化。
- handoff 的 `final_head=24c0ca0c` 早于实际 HEAD 611b1d62，属于一轮文档自描述滞后；不构成功能代码漏审。产品/测试 8 项与分片独审报告 6 项 SHA 共 14 项逐一匹配 handoff。精确值见本报告 JSON。
- CodeGraph 当前索引未覆盖 RF 的 `scripts/research`，因此按已知路径有界读取；未在作者工区建立索引。
- `git status` 在当前只读沙箱返回 work-tree/cwd 权限错误；未借此推断工作区干净，也未升级权限、checkout 或修改 Git 状态。

ROOT 候选 `C:/Users/郑曾波/Projects/revenue-forecast-w16-root-acceptance` 绑定同一 HEAD 611b1d62。实际反例只运行该隔离候选，作者和主仓未运行、未写入。候选 8 项被审文件 SHA 在运行前后一致。

## 第一轮实质 findings

### F1 / P1：同名 restated 被直接升级为“同口径可比”，没有业务边界或可比披露依据

证据：`scripts/research/revenue_basis.py:62-70` 的可选契约没有业务边界、可比组或重述桥字段；`:381-411` 仅比较 `operations`、`statement_status`，二者相等就返回 comparable。`tests/test_w16_revenue_basis_cli.py:237-245` 的 `diag_bridged` 只把两个记录都设为 restated，没有明确桥或同组披露证据。

独立反例：完整有效 RF 输入的 FY2024=140、FY2025=150 均只声明 total/restated/fiscal_year/source_ids，不给边界/组/桥。真实 forecast CLI exit 0，报告写 `FY2024→FY2025：同口径可比；同比 7.1%`。两个独立重述版本或不同业务边界完全可能同为 restated；枚举相等不证明比较口径相同。

影响：B03 的业务边界与 B06 的“明确有桥”未实现；当前测试把缺失的前提写成正确结果。最小修复应在共享 owner 区分“字段同名”与“已有来源支持同一可比组/业务边界”，信息缺失保留 unknown/not_declared，不能写已可比。

### F2 / P1：组件显式声明冲突仍静默复算，总额桥缺关系与边界约束

证据：`revenue_basis.py:145-183` 解析组件时未限定可接受键；`:228-277` 只校验组件 exact-value claim 的数值/FY/文档单位及加总，未验证组件间、组件与父记录的 statement/业务边界，也没有明确总分关系的来源 claim。

独立反例：父记录 total/restated=150；continuing=100 声明 restated/after-disposal；discontinued=50 声明 as_reported/before-disposal。分别有合法 FY2025、USD million、exact_value 来源 claim；组件冲突同时写入结构与 claim 摘录。真实 forecast CLI exit 0，输出原样保留两个冲突字段，仍复算成功并写“同口径可比”。因此这不是单纯缺元数据；收到的显式冲突被忽略。

最小修复：可选组件元数据支持后对齐，或对未支持的显式键清晰报错；不得忽略。总分关系采用既有 policy_support/rationale_support claim，绑定相同 FY/单位/业务边界/列报组。只有该关系成立才执行 Decimal 复算；不能以“两个数恰好相加”等价替代关系证据。

### F3 / P1 / ROOT 接口：公开回测仍消费已明确不可比历史，CAGR 与 MASE/RMSSE 输出失真

证据：`scripts/revenue_backtest.py:516-554` 直接从 history 数值求差分、尺度和 CAGR；`:657` 由公开 `evaluate_snapshot` 调用并写入结果。未调用 revenue_basis owner，也不输出口径状态或禁用原因。

独立完整链：同份混合 as_reported/restated 输入的 forecast CLI 正确写“不可比”；随后真实 `revenue_backtest.py create`、`evaluate` 均 exit 0，仍发布：

- `company_year_results.2026.historical_cagr_forecast=160.71428571428572`；2027=172.1938775510204。
- `benchmark_diagnostics.mase=0.8250000000000028`、rmsse=0.8867073925484126、historical_cagr_mae=1.4540816326530575，无口径降级说明。

判断：作者未越过卡片文件写范围而列 interface_request 是正确的责任划分；**ROOT 此次应修复该消费接口后再接收闭环**。这是当前公开结果里的确定错误，不宜仅排到后续并声称 B03 全通过。最小修复是复用同一 owner 的全序列比较状态：明确不可比时停用 CAGR 基准及使用该差分的 MASE/RMSSE，并给原因；flat-base 及不依赖历史比较的误差继续。纯 legacy 保持原数值兼容，同时状态写未声明。无需改纯数值 calculate_cagr 或引入新的审批机制。

### F4 / P2 / 契约补全：预测锚点被固定解释为 total，无法表达来源本身以持续经营收入列报

证据：`revenue_basis.py:280-293` 无条件要求基年 operations=total；未比较 `reported_total_revenue_parameter_id` 所指参数的实际口径。独立反例把历史基年和该参数均显式声明 continuing、值相同，CLI 仍 exit 2，要求改声明 total 或移出序列。

限定：施工卡“把 continuing 错误替代已知 total”应拒绝的测试本身正确，本 finding 不要求放松该拒绝。缺口是无法区分该错误与“报表报告收入本来就是 continuing”。不能把真实 continuing 值改标签 total 来通过校验。

建议：给 reported_total 参数增加同一 owner 解释的可选 revenue_basis，按双方明确 operations/期间/边界/列报组对齐；明确不一致给数据错误，明确一致才允许 continuing 基数。参数名 reported_total 仍指公司报告收入这个数值锚，不应据名字自行推断是否包含终止经营。旧输入均无该元数据时继续旧路径；缺项只标未知，不新增全局旧输入阻断。

## B01–B08 接收判断

| ID | ROOT 第一轮判断 | 理由 |
|---|---|---|
| B01 | PASS（静态缺口与实测） | 真实历史/报告/回测路径缺口清楚，无同义 DU5 重建 |
| B02 | PASS（已实现部分契约） | 可选元数据、原始 quantity/标准化值、source/claim 复用、legacy 保留成立；不足归 B03/B04 |
| B03 | FAIL | F1/F2 业务边界未处理；F3 公开派生比较仍盲算；F4 基数实际口径尚不能对齐 |
| B04 | FAIL | Decimal/容差、FY/单位数值对齐成立；F2 明确关系与边界/列报组缺失；没有实际重述桥 |
| B05 | PARTIAL | validate_document→run_forecast→CLI→报告与输出绑定成立；actual reported total 值读取正确，`segments.py:423-425` 确认不是调整后基数。F3/F4 实际消费口径未闭合 |
| B06 | PARTIAL | 9 CLI 案例真实，但“有桥”只是双 restated，未覆盖业务边界/组件冲突与公开回测；零基数覆盖，负历史基数已有契约拒绝但无专属 CLI 断言 |
| B07 | AUTHOR_EVIDENCE_PRESENT | 三份本地原件的 locator/单位/期间记录及 going-concern 反例存在；本次未重做原件内容审计，不能代签来源真实性或真实公司 RF |
| B08 | PASS（静态） | 共享 owner、DU5 公共 lookup、无公司/页码特判；未发现新增 legacy 全局阻断。回归与 gate 通过为作者绑定收据，本次未重复全量 |

## 建议的最小可选 basis 契约

沿用 `rf-revenue-basis/1` 与现有 operations/statement_status/period_kind/input_quantity，不建第二数据库。可在 record 与 reported_total 参数的 revenue_basis 复用以下可选字段，名称由 ROOT 最终定：

```json
{
  "operations": "continuing",
  "statement_status": "restated",
  "period_kind": "fiscal_year",
  "business_boundary_id": "issuer-consolidated-ex-disposed-businesses",
  "comparison_group_id": "filing-2025-comparative-presentation",
  "basis_claim_ids": ["existing_policy_or_rationale_claim"]
}
```

group 表示来源明确把所提供的值列为同一比较组，boundary 表示同一业务集合；ID 是引用与一致性键，不能由相同字符串自动升级来源质量。claim 继续使用现有 source/locator/period/source-clock 责任链，target 绑定各历史记录或 reported_total 参数，不新增 claim target 类别或许可层。数值仍用既有 exact_value claim。

规则：无字段保持旧路径；仅有 operations/status 不足时输出 not_declared/unknown；同 boundary+同有来源支持的 group 才能确认可比。两条 restated 但不同 group、不同 boundary 应不可比。不同 statement_status 不能自动换算；要比较，输入须给来源已重述/已调到同组的数值及桥/比较披露证据，不在引擎凭标签造调整。组件可继承父口径的前提是有明确总分关系 claim；显式组件字段必须一致，不认识的显式字段不得静默吞掉。

reported_total 参数与历史基数只在显式口径一致时断言“口径对齐”；数值相等与口径一致分别报告。all-legacy 数值兼容，不添加人工许可或全局阻断。

## 独立执行与最小验收命令

只运行一次独立反例链，未重复作者 595 项 gate。稳定 pre-W16 完整输入构造器被复用；未复用 W16 的 _basis/_add_component_claims/CLI runner。反例、预期与组件冲突由审查者独立生成。

实际命令（exit 0 是运行器完成，**不是产品语义 PASS**）：

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
& 'C:/Miniconda/python.exe' 'C:/Users/郑曾波/Projects/company-wiki/.planning/w16-w17-root-acceptance/review-w16/reproduce_w16.py' --candidate 'C:/Users/郑曾波/Projects/revenue-forecast-w16-root-acceptance' --scratch 'C:/Users/郑曾波/Projects/company-wiki/.planning/w16-w17-root-acceptance/review-w16'
```

逐 CLI 原文、退出码、时间、合成 input/forecast/snapshot/actual/evaluation SHA 和文件清单：`.planning/w16-w17-root-acceptance/review-w16/counterexamples-2764ea16b7/receipt.json`。共 7 次 CLI（含 --help），候选源码 8 项 SHA 前后一致，14 个产物合计 610,496 bytes（不含 receipt 本身），全部限于自有 scratch。TMP/TEMP、registry 限在该根，禁止 pycache；子进程环境屏蔽常见模型凭证；模型/下载 0。

ROOT 修复后最小验收建议：一次重跑同样关键链（以新契约补正正例），要求无组双 restated 不再标可比；显式组件冲突拒绝/不能复算；mixed 回测 CAGR/尺度诊断停用且有原因；有来源同组重述、真实对齐 continuing 基数通过；legacy 基数不变。随后只跑受改动的 W16/DU5/历史与 backtest 定向回归，例如：

```powershell
python -m pytest -q -p no:cacheprovider tests/test_w16_revenue_basis.py tests/test_w16_revenue_basis_cli.py tests/test_input_quantity_conversion.py tests/test_du5_root_unit_boundaries.py tests/test_backtest.py
```

本命令为建议，当前未执行。ROOT 新增覆盖实际新契约的测试后应纳入同一次集中回归；无剩余具体风险时不再扩展全量。

## 后续复核

待 ROOT 修复候选，并提供最终 commit/diff。保留 F1–F4 与原始 receipt，追加逐项修复、最终文件 SHA 和定点复测结果；未修前接收状态保持 REQUEST_CHANGES。
