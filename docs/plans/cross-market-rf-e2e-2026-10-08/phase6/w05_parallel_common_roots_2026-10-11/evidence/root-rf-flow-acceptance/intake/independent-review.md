# W05-RF-FLOW 独立只读接收审查

日期：2026-10-11。结论：**NEEDS_FIXES，不可直接宣告完成或并线验收通过**。
这是源码/期间语义验收，不是公司经济预测质量签收。

## 交付冻结与所有权

- 交付树：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow`。
- 分支：`codex/w05-rf-flow`。实际 HEAD：`f1a782a478d255b9b4b8f531e7a3961134e257ba`。
- 功能提交：`7b22bca8d6aa87f643780100832daec2836ed558`；随后交接提交为上述 HEAD。
- 母卡基线：`1b616622763ece6549676f2a74f596e6c65244af`；是 HEAD 的祖先。
- Git 状态前后均干净。主线仍为同一基线，主线到交付树距离 `0 / 2`。
- canonical RF 的 `assurance/runs/daily_alert.jsonl`、`weekly_alert.jsonl`、`weekly_manifest.json` 和未跟踪 `output/` 是已有运行产物，未改、未暂存、不能搭车提交。
- 文件写集在母卡责任层内；`tests/test_data_contract.py` 是唯一不在明示测试清单的额外测试文件，仅将当前 engine 字符串 4.2.1 改成 4.3.0。必要性已记录，未降低数学断言。
- 未见 CI、配置、gate、安装、FF、CWP 或别人的工程代码变更。
- handoff/manifest 的 87 条文件 SHA/尺寸记录全部 MATCH。`handoff.json.head_commit` 指功能提交，不是随后交接提交；两者职责清楚。

## 独立执行结果

1. 母卡集中套件和新增套件：**120 passed / 33 subtests passed，6.41s**，见 `focused-suite.log`。
2. 自写只读探针：`probe_dated_flow.py`，结果 `counterexamples.json`。
   - 合法 post-control + H2 + 显式 FY 桥：PASS，低情景增加 31.29190208。
   - 小額负 disposal contribution：PASS，FY2026 low 149.6870809792；公司总收入仍非负。
   - 相同冻结输入连续两次完整输出严格相等：PASS。
   - 下列三个反例都错误地通过 `validate_document -> run_forecast -> validate_published_forecast -> validate_forecast_output`。故强 hash 和输出重算不能补救输入语义问题。
3. 仅两个兼容测试的 collection 在 main 能收集 28 项，在交付 leaf 缺两个模块；真正根因见后文，不是 RF 缺已提交代码。
4. main 单项 `test_mixed_rejects_lagged_activity` 确实失败：`forecast/calc.py:158` 直接索引缺失 `carry_in_parameter_ids`，见 `baseline-mixed-recognition.log`。不是本线回归，ROOT 应在总整合时归属处理。

测试没有供应商、模型或下载调用，费用为零。没有改产品、已有原件、主线运行产物或安装目录。

## 需要修复的语义问题

### RF-FLOW-ROOT-01 / P1：把 derived 改标 annual 即绕过期间来源

位置：`scripts/contracts/document.py:533-538` 的 composition 调用只覆盖 derived `period_flow`；`scripts/contracts/annual_consumption.py:116-120` 直接接受 `annual`。

反例：原真实短窗口 `2026-05-31..06-30` 金额 1.29190208，通过 `derived_fact formula=x0`，删除起止日期、改 `time_basis=annual`，不写任何覆盖解释，就被 FY2026 acquisition adjustment 消费。最终 low 收入 151.29190208、强输出读者也 PASS。

根因：年度合法性检查相信外层标签，派生 DAG 的实际来源期间没有传播到 annual 消费边界。不是需要新增身份签收。

建议先固化该反例为 RED；统一派生流量的期间覆盖验证，`annual` 与完整 FY `period_flow` 使用同一个目标窗口规则。有显式全年假设/控制范围说明的桥可表达，直接给 partial `x0` 换标签必须拒绝。对 scalar、ratio、stock 和流量分别处理，不把所有派生数学都误当收入求和；旧 3.9 行为按卡保留。

### RF-FLOW-ROOT-02 / P1：rationale 变成绕过所有日期约束的许可

位置：`scripts/contracts/period_flow.py:195-197` 在任意非空 rationale 时直接返回，发生于 containment 校验之前。

反例：保留两个 FY2026 金额，把 derived 输出改 FY2027 `2027-01-01..12-31`，只填 `explicit composition, fixture`，就能把 31.29190208 声称为 FY2027 已组成的流量；所有输入/输出检查通过。

根因：将说明文字兼作全局数学豁免。卡要求口径解释，但没有授权解释文字改变金额所属期间。

建议先固化 RED；日期合法性、输入金额与目标期间关系在 rationale 存在时仍执行。rationale 只描述范围/缺口和使用假设，不能免除实质校验。真正从上期估计未来收入应以现有 analyst_assumption/scenario_stress 明示估计，不能直接冒 derived historical flow。

### RF-FLOW-ROOT-03 / P1：H1 + 自己的 Q2 可凭文字被重复计入 FY

位置：同上；`tests/test_w05_dated_contribution_composition.py:121-132` 甚至明确断言此错误求和应通过。

反例：同主体、同定义的 H1=55、其 Q2=30，`x0+x1=85`，填 `Q2 is a subset of H1; overlap is intentional`。85 被消费为 FY2026 调整，low 收入 235，强输出读者也 PASS。

根因：用“说出重叠”替代“消除双算”，反例测试从数学上错误定义绿色。

建议将该测试改为真正的业务 RED（保留原交付 FAIL 留证）；不能通过取消检查或加签收解决。区分同口径加法、合法残差减法（如 group minus acquired）及确有不同范围的组成。使用已有公式/参数/证据口径接缝表达，不添加逐公司许可链。不同主体同日收入能合法求和；同主体已含子集不能因解释文字再次相加。

## 交接证据与环境问题

### RF-FLOW-ROOT-04 / P2：封存 CNY 金额进入 USD 夹具

`e2e/build_inputs.py:6-14,44-48` 声称 1.29190208 是封存 CNY million 真实金额，实际 `forecast_document()`/默认 `add_window_parameter` 使 case1 输入及输出成为 `USD million`。输出测试还在第164行断言 USD million。这不是汇率转换，数字被原封不动换了币种。

应让全 case1 采用 CNY million（包括全部基础参数、claims、historical amounts 的一致单位），或把此数彻底声明为 synthetic USD 金额且不冒封存原始金额。推荐 CNY 夹具，以兑现真实实证；无需调用外部金融 API。

### RF-FLOW-ROOT-05 / P2：8 份实际端到端 artifacts 未进入 commit/manifest

`docs/handoffs/w05-rf-flow/e2e/artifacts/` 存在8个文件，合计小于1MiB，SHA 与 `logs/phaseC_artifact_hashes.txt` 一致；`.gitignore:16 artifacts/` 使它们全部被忽略。因此 Git clean 不代表这些交接资料已提交；独立干净 checkout 只有生成器与日志，不能打开 handoff.findings 已引用的 artifact 路径。

ROOT 不要复制原件，修复后保留小型冻结输入/输出及正确 manifest 到一个不会被全局 artifacts/ 吃掉的 evidence 目录，或精确添加这些 bounded fixtures；不整套 force-add 一个目录。原始日志可以保持历史。

### RF-FLOW-ROOT-06 / 环境诊断：DIAG-02 应改为 sparse checkout

main `compatibility/` 九个文件均已 tracked；leaf 的 `core.sparseCheckout=true`，列表只含 `.githooks/.github/references/scripts/tests/tools`。`git ls-files -t compatibility` 全部为 `S`，实际目录未 checkout。原交接将其说成“baseline 仓库缺 compatibility 代码”不准确。

ROOT 创建新整合树时纳入 `compatibility/` 即可恢复导入；不能因此删兼容测试、修改 site-packages 或假称产品修复。依赖相邻 CWP 的旧兼容测试需按其真正职责选择一次总整合检查，不新增每小节点签收。

## ROOT 隔离整合顺序

1. 从当前 RF main 基线新建 ROOT integration 工作树，保留 canonical dirty assurance/output；不改原交付树。
2. 纳入所需 `compatibility/`（该目录已经是 Git 内容）；接入两个已交付 commits，暂不发布。
3. 把前三个反例转成正式断言，保留本目录的原始 FAIL；统一派生期间/annual 消费规则，rationale 只作解释；修正 C1 币种与冻结 E2E 留证。
4. 一次集中复跑120套件及新增反例，保留合法收购桥、非12-31财年、同日/闰年、负贡献与3.9兼容。再运行 native CLI 两夹具端到端及强读者、日期篡改，独立scratch恢复原样。
5. ROOT 处理已确认的 baseline mixed-recognition KeyError 所属问题。不能声称“旧问题”就宣告所有 CI 绿；也不应把 sparse 导入失败当成业务 RED。
6. 一次总接口审查后，正常 commit/merge/push；安装由 ROOT 集中同步、PWF如实标记。原交付版本4.3.0暂未发布，不要同步不合格安装副本。

范围：未并线、未 commit、未安装；不修改母PWF。原始 FAIL 文件 `counterexamples-original.json` 保留。负贡献首探针曾使 FY2027 总收入为负，已如实保留 `counterexamples-before-disposal-fixture-scale.json`；该拒绝是正确产品行为，后续仅把 synthetic 贡献规模缩至1%，证明合法负贡献通路，不是削弱产品断言。
