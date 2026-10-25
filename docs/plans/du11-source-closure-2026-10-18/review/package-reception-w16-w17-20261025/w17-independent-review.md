# W17 ROOT 独立接收审查

**结论：REQUEST_CHANGES。** 作者交付的工程测试与独审记录齐全，但 ROOT 的隔离候选实跑复现了 5 类未覆盖问题；当前不能按 O01–O08 全通过接收。

- 作者 HEAD / 隔离候选 HEAD：`7c71c8111f14a3aae6a1df274eeffb81c01939b7`；原独审代码 `faa1f3e`；完整差异范围 `bb41d9b..HEAD`，37 个文件。
- 仅在 ROOT 指定候选执行 CLI；未改作者工区、主仓或候选代码，未 checkout、安装、建索引、下载或调用模型。
- 本报告仅审工程观察和报告契约，不签来源真值、摘要语义或公司 RF。

## 实质 findings

### ROOT-W17-F1 [P1] 可选载体没有当前scope关联，外部run被标为current

- 位置：`skills/revenue-forecast-audit/scripts/coverage_observations.py`，行 269, 274, 810, 816, 913, 921。
- 实测：真实HTML bundle source_ref=f0e62960…；selection/model-view source=7f1431d6…；source review为annual14旧selection；status-index run_id=w15-portable-run，而CLI run_id=root-w17-review。仅attempt-1相同就得到rf binding=current；六维observed、无诊断；外部applies_to被填为CLI run/attempt和HTML bundle版本。RF逐行use仍unknown/null，本finding不声称已观察到真实RF采用。
- 影响：报告误将无关来源/运行的声明并到当前摘要/采用上下文，SHA只证明读到哪份字节，并不证明适用关系。
- 最小修复：复用现有source_ref/subject_binding、sourceRef、source_id、selectionSHA/selection_sha256、reviewed_scope、run_id/review_attempt及row source/document身份。各载体保留自身scope/version；无法关联者照常展示原始声明，current binding为unknown/unrelated并诊断，不能覆写为当前attempt。不新增身份库/许可或拒整import。
- 对应要求：O02, O05, O08。状态：OPEN。

### ROOT-W17-F2 [P2] selection-check未知schema仍被解释成扫描/选择/几何声明

- 位置：`skills/revenue-forecast-audit/scripts/coverage_observations.py`，行 913, 916。
- 实测：schema_version=unrelated-format/99且source_id=OTHER的selection文件，其reading_context.unread.native_scan=complete被直接消费；CLI exit0，source_scan observed，无coverage_input_schema_mismatch。
- 影响：违反按真实版本解释公开字段的边界，同名字段可以污染当前观察。
- 最小修复：像其余三类可选输入一样识别selection schema；未识别版本只保留原始载体身份/SHA和诊断，不参与已知语义facet；有效bundle观察继续输出。
- 对应要求：O01, O02, O06。状态：OPEN。

### ROOT-W17-F3 [P2] 空span列表与omitted超分母缺少计数冲突诊断

- 位置：`skills/revenue-forecast-audit/scripts/coverage_observations.py`，行 242, 260, 413, 440。
- 实测：明确evidence_spans=[]且selected_count=5时candidate_selection observed且无诊断；candidate_count=12且omitted_candidate_count=999同样observed无诊断。
- 影响：O03要求的矛盾/超界在常见零列表和omitted分母边界上被静默放过，raw中的0还被truthiness当缺失。
- 最小修复：区分缺字段与明确空列表；存在列表时包含0也比对declared；对omitted与其已声明candidate分母做范围诊断。只保留原值+conflict，不修数据、不推断必需事实遗漏、不阻断导入。
- 对应要求：O03, O07。状态：OPEN。

### ROOT-W17-F4 [P2] bbox:null被当作可用几何

- 位置：`skills/revenue-forecast-audit/scripts/coverage_observations.py`，行 489, 490, 532, 539。
- 实测：五个span的page/char均null且bbox:null，输出spans_with_bbox=5、geometry_availability=available、by_carrier.bundle=true。
- 影响：只有键存在并没有几何锚，报告制造了不存在的几何可用性。
- 最小修复：只把实际非空且合法的bbox锚计入可用几何；null保持不可用/unknown（按现有坐标声明规则），文字可读性独立保留。
- 对应要求：O04。状态：OPEN。

### ROOT-W17-F5 [P2] 非object model-view使整个有效导入崩溃

- 位置：`skills/revenue-forecast-audit/scripts/coverage_observations.py`，行 714, 719, 752, 755。
- 实测：--model-view JSON为[]时schema分支本欲记录mismatch，但line753再次document.get抛AttributeError；CLI exit1、无报告。
- 影响：可选报告输入的形态错误阻断其余有效维度，违反报告型不阻断要求。
- 最小修复：在已读载体进入观察owner时统一保留原始形态并安全识别对象；形态/schema错误只记录本载体诊断和unknown，不抛出AttributeError，不新增许可。
- 对应要求：O06, O07。状态：OPEN。

## O01–O08

| ID | 结果 | 证据与缺口 |
|---|---|---|
| O01 | FAIL | 真实pointer/字段注册表主体存在；native缺字段通常unknown。但selection-check不做版本识别，未知schema照样解释（F2）。 |
| O02 | FAIL | 共享owner和六维结构已接线，SHA/pointer可追；外部scope/version被当前CLI/bundle覆写且未关联（F1/F2）。 |
| O03 | FAIL | legacy原值及未知解释保留；已覆盖负数/bool/selected>candidate；空列表和omitted超分母未诊断（F3）。 |
| O04 | FAIL | 金标不升级摘要、v5 tasks不折算claims、claims not_reviewed成立；null bbox错误宣称几何available（F4）。 |
| O05 | FAIL | prepared/read/use按原值分别展示；旧attempt可unknown。但相同attempt字符串、错误run与无关source仍binding=current（F1）。 |
| O06 | FAIL | 无overall_pass，无任务库/许可，复用bounded读取；非object可选model-view却使整import崩溃（F5）。 |
| O07 | PARTIAL | 作者/作者独审全链和737测试收据保留；ROOT不重复全量，独立6次真实CLI导入发现上述新反例。修复后需受影响回归和一条完整链。 |
| O08 | PARTIAL | 冻结载体输入7/7字节SHA与收据匹配，fixture明确synthetic。真实回放却混用不同来源/selection/运行并误标当前scope（F1）；HTML stub产物只证明公开契约形态，不是公司事实或生产模型响应。 |

## 实际字节与出处

- handoff 声明的 6 项产品/测试/文档实际 SHA 全部匹配；两份产品代码、两份测试与 `faa1f3e` 一致。reference 随后有已披露的文案增补。37 项变更的实际文件 SHA 均记在 JSON；3 份 JSON 与 Git blob 只有 CRLF/LF 差别。
- 7 项冻结输入在 CLI 后再次逐字节核 SHA 全部匹配。字节存在与身份关联分别核验，不能用 SHA 匹配代替 scope 匹配。
- HTML bundle 是 `pool-w03-official-flow` 的 120 字节 HTML/stub-model 公开契约产物；annual14 selection/model-view 和独立 source review 是另一 source/selection；W15 status-index 是示例运行。本回放可证明解析这些公开形状，不能证明当前公司摘要/真实模型响应/RF采用。
- 原始作者初审与复审未改写。737 全量与相关套件是作者/作者独审收据，本审查按 ROOT 指令未重复全量。

## ROOT 最小验收建议

1. 共用 observation owner 做报告型 scope association。保留每个载体自己的 source/run/attempt/version；不能绑定者展示自身声明并给相关维度 unknown/unrelated/diagnostic。复用已有 ID、SHA 和指针，不新建身份库、许可 JSON 或强制执行 gate。
2. selection-check 未知 schema、可选 model-view 非 object：保留读到的原始载体 SHA/形态，只限制对应观察；有效 bundle 的导入与其他维度照常完成。
3. 明确空列表与计数超界、null bbox 做局部诊断；不能将缺字段填 false/PASS，也不能推成必需事实遗漏。
4. 修复后只复跑这 6 个反例、对应受影响测试及一条完整 import→source/output packet→附独立 review→compare CLI 链。ROOT 负责产品修改；本 reviewer 复核最终文件 SHA 和行为，不重跑已通过的全量。

## 独立执行记录

- Scratch / 完整命令与输出收据：`C:\Users\郑曾波\Projects\company-wiki\.planning\w16-w17-root-acceptance\review-w17\reception-b504f94dcc/receipt.json`。
- `explicit-empty-selection`、`omitted-over-candidate`、`unknown-selection-schema`、`null-bbox-with-readable-text`、`cross-run-real-artifacts` 均 exit 0，分别复现缺失诊断/误归属；`malformed-model-json-array` exit 1，复现 AttributeError。
- subprocess 局部 TMP/TEMP、`PYTHONDONTWRITEBYTECODE=1`；保留失败证据。网络/下载/模型调用均 0。
- CodeGraph 在 Audit 主仓未初始化，本次明确不建作者索引；按指定文件有界读取。Git status 被沙箱 cwd 权限拦住，未把它描述成 clean。
- 当前主机已有 quick_validate.py（`.codex/skills/.system/skill-creator/scripts/quick_validate.py`）；旧 NOT_EXECUTED 收据保留，ROOT 可做一次结构检查。

## 进度

- 已完成：中央卡、COMMON、适用 AGENTS、作者 handoff/final 独审、产品/测试/fixture 与交付差异审查、文件 SHA、真实输入出处、隔离 CLI 反例。
- 下一步：等待 ROOT 修复候选后，补写本报告的最终复审节；当前 5 项 OPEN。
