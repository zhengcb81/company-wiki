# W05-RF-FLOW ROOT 隔离修复交接

## 交付状态

**READY_FOR_ROOT_REVIEW；未 commit／未 push／未安装／未并入 canonical。**

- 产品树：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root`
- 分支：`codex/root-w05-rf-flow-20261011`
- HEAD：`1b616622763ece6549676f2a74f596e6c65244af`
- MERGE_HEAD：`f1a782a478d255b9b4b8f531e7a3961134e257ba`
- 原 worker 的两提交：`7b22bca8d6aa87f643780100832daec2836ed558`、`f1a782a478d255b9b4b8f531e7a3961134e257ba`。
- 原交付通过正常 `merge --no-commit --no-ff` 纳入；工程修复未提交。原 worker 仍 clean，未写 canonical RF。
- canonical 原有 dirty 仍为 `assurance/runs/daily_alert.jsonl`、`weekly_alert.jsonl`、`weekly_manifest.json` 和 untracked `output/`，不属于本线。

## 系统根因与责任

1. **时间语义与消费标签脱离**：原实现只检查外层 `period_flow`，`annual` 派生别名可掩盖部分期间。现在统一检查 dated derived 及存在 dated ancestry 的 annual wrapper，跟随实际非零公式输入的窗口；所有年度消费者继续共用 annual_consumption 规则。
2. **解释字符串被当作豁免**：原函数遇到任意 rationale 就返回，导致跨年搬运和 H1+其Q2 被接受。现在解释只说明真实范围缺口、独立业务或残差扣减，不能豁免实际日期包含关系或相同来源/同语义正向重复。
3. **别名与定义改写丢失源谱系**：重复检查沿 formula 的 leaf identity／definition／时间／系数符号执行，修改 derived 中间项或结果的 definition 无法绕开。零系数/未使用输入不能补全年覆盖；point stock/rate 单独不能冒充 recognized flow。
4. **旧 mixed-recognition 的验证责任顺序错误**：此问题在 main 已存在，不归咎 W05 新日期特性。增长驱动 DAG 遍历在结构验证之前访问 carry-in 字段，产生 KeyError。完整的原 recognition validator 移入统一 contracts owner 并在已有元数据的 DAG 索引前运行；旧结构草稿缺省 recognition 仍保留原语义，实际 forecast 仍要求其存在，不制造默认 carry-in。
5. **实金额币种标注错误**：C1 周围全套 synthetic fixture 改成 CNY million，封存原数仍为 1.29190208 CNY million。通用数学单测数值只是 synthetic；不再把相同数值写成真实 USD 事实。
6. **测试宿主布局被误当契约**：原 leaf sparse checkout 缺 compatibility 9 tracked 文件，不能据此声称 main 无代码。ROOT 全检出后，另外发现旧测试还假定物理 sibling 三仓。现在纯 manifest/hash 单测无物理仓要求；Git ancestry／canonical doc 集成用显式根；unit fixtures 用自身临时文档及9个真实 tiny Git commits 验证实际正反例。

### 不支持模式与诚实边界

公式支持 additive/subtractive temporal lineage 与 scalar/rate/price 缩放；两个 flow amount 的乘积、以 flow 为分母、破坏 flow 单位的幂不视为时间合成。应使用既有显式假设/native model，不假装能推断业务意义。

原始 reported fact 的真正经济定义、子公司是否已包含于集团、独立来源是否重写同一事实，是 source/input 与经济审查的责任。原 leaf ID 和 definition 谱系防止 derived 改名洗白；hash/自由文本本身不能证明业务集合互斥，也不能识别整套自洽伪造。未引入人工签收、身份库或许可。

## 测试与证据

### RED 保留

- `root-business-red.log`：三项实际时间反例及旧 mixed KeyError，**4 failed / 1 passed**；已通过的零系数保护不冒充 RED。
- `root-stock-red.log`：stock 写为 revenue 的正式反例，**1 failed / 8 deselected**；后续断言未改。
- `final-engineering-before-optional-recognition.log`、`final-node-before-optional-recognition.json`：集中节点曾因2个 legacy draft 的遗漏 recognition 验证回归失败；修验证职责，无改断言换绿。
- 初期 mypy 类型失败也保留 `public-types.log`；已用真实 isinstance 分支修复 collect-all shape，不用 waiver/cast/default 掩盖。

### 最终集中节点

- `final-engineering.log`／`final-node.json`：现有 `tools/pre_push_gate.py` **ruff PASS、mypy 11 source files PASS、356 passed +36 subtests，33.20s**；完整入口38.043s。
- 可移植兼容+3.9 field/engine 节点：**52 passed +7 subtests，3.90s**。该组与 daily 有部分重叠，不将数目相加宣称唯一用例数。
- 原设计的 120+33／ROOT 根因套件先前集中为 **137+33 PASS**，`centralized-green.log`；后续 stock 测试已包含最终 daily。
- native template／两个 validate-only→forecast→Markdown／snapshot→strong reader→重hash日期和币种篡改／完整 forecast JSON 确定性均 PASS。
- 真三仓的 manifest 声明、Git ancestry、canonical doc 在 `final-checkpoints.json` 显式根校验 PASS；这些现场记录不是 CI 固定 golden。
- 模板说明最后补充不得用解释豁免重叠；仅文案变化，`template-doc-checkpoint.json` 单次 native generator PASS，未再扩大整套测试。
- `final-supplemental-lint.log` 对兼容代码和 E2E generator／reader 与模板变更 PASS。
- **0 provider calls、0 LLM calls、$0**。

### 快速检查责任

唯一修改注册点是 `tools/pre_push_gate.py` 的既有 `SMOKE_TESTS`。新增三组 W05 dated suites、ROOT temporal lineage、已有 mixed recognition。没有另造 gate，没有恢复每 commit 全库测试。原模板/来源真值仍由经济与 source 审查负责。

## 写集、空间和还原

- `root-product-inventory.json`：相对于原交付 **17个已存在文件修改 +12个新文件 =29个文件**，包含当前 bytes/SHA；它们完整当前文件合计 **776,804 bytes**，不是所有字节都新增。
- 12个新文件：recognition owner、ROOT regression、ROOT-reception 和 frozen 的8个小产物+manifest。产品交接 `docs/handoffs/w05-rf-flow/ROOT-reception.md` 明确区分原历史 worker receipt 与 ROOT 修复。
- frozen 8项文件约469 KiB，以最终 `e2e/frozen/manifest.json` 为精确 bytes/SHA。旧 manifest 在 `frozen-manifest-before-template-doc-fix.json` 留证；最后改变的只有生成模板说明。
- 本线没有复制任何 PDF／raw binary，没有将 ignored `artifacts/` 或旧用户 output 目录收入提交。
- 自有 `e2e-scratch` 和 `template-doc-scratch` 均 initial ABSENT→final ABSENT；正式 E2E before-cleanup byte 清单在 `final-node.json`。
- ROOT 完整 worktree 的49,387 tracked 文件仅为避免稀疏检出假缺失，属于既有 checkout；本线不扫描/归档全部文件。ROOT 并线后可按自有工作树规则清理，保留提交和小证据。

## ROOT 收尾接口

1. 对 `root-product-inventory.json` 指定写集作独立代码审查。重点再看 derived annual、definition alias、stock typed precondition、rationale 日期不可豁免；经济范围真值另属后续公司审查。
2. 正常完成 pending merge、执行已有 hooks、commit/push；保留本次旧 FAIL 与 ROOT receipt，不将原 worker SHA 声明误当修复后文件校验。
3. ROOT 决定安装副本同步和 canonical 整合；本线不写安装路径或共享 PWF。根据精确明细整合，保护 canonical dirty 的其他所有者。
4. 主线代码质量 PASS 不代表真实公司收入预测已过经济验收，也不代表整个 PWF 已完成。
