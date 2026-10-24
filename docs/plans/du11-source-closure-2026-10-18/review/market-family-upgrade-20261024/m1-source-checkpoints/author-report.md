# M1 源侧检查点新版gold 作者交接

## 交付范围

4份 `du-gold/1` JSON位于 `gold/`，可直接由现有 `load_gold` / `load_gold_dir` / `evaluate` 消费，无新oracle，不修改原gold、原manifest或evaluator。

**作者包完成，等待另一独立reviewer验收；本作者不自签最终接受。**

4份原样本已用于诊断，全部 `scope=development`，`support_set_frozen_before_output=false`；不是fresh holdout，也未声称在最初候选输出前冻结。

|样本|事实数|原件锚点|引用字符数|旧冻结baseline对新版gold结果|
|---|---|---|---|---|
|du5-cn-proya-q1|10→10|38|1152|PARTIAL|
|du5-hk-kingsoft-interim|13→16|42|2214|FAIL|
|du5-cn-gbits-call|12→13|31|869|FAIL|
|du5-us-msft-ex991|12→12|28|3218|FAIL|

旧47项ID和importance全部保留，同样本所有旧错误反例全部保留（无关的采购单位反例从period-meta迁至采购事实）。新增4项：HK两项完整经营驱动、一项原period-meta误引的采购合同阶段；吉比特另一回合的买量依赖降低意向。

## 关键语义修订

- 互补片段只作一个AND支持集：期次/单位/表头+数值、基本与稀释、业务scope、IFRS/FX条件、指引时点与新定义。没有用只表名、只旧分部列表、折旧代capex等不足OR。
- 保留原数值重要性/负例，HK纯精确财务金额与CN季报同归correctness_if_emitted；US GAAP/币种汇率属disposition_context。相反，HK经营解释/展望/业务结构、MSFT座席定义与收入展望明确required_business；不以减少分母换绿。
- 吉比特匿名speaker仅用原“说话人1/2”，role=unknown；同回合联合支持要求require_same_scope，跨明确标记的09:24/09:41/09:42比较回合不伪造单回合，保留中间“它不像”否定连接。不会把匿名speaker自动当有姓名/已核公司高管。
- ASR原“会不会”、Oa/买了、2000多用户、利息负债均保留；不填万、不强修ROI/减了、不强释退款或预计负债、也不强断不会回升。原ID保留追踪，新增双向错误确定性反例。
- 元数据的采购630000错误OR已拆出；采购合同原话与全节千元说明共同保留，禁止只看正文“元”字抹去全节单位。没有把承诺当收入/完成履约。

## 作者QA（不代替独立审查）

1. 4份原件SHA读前/读后与旧gold SHA一致；139个新gold锚点均用现有 `verify_gold_anchors` 对真实原件核验。
2. 现 `load_gold_dir` 加载4份成功；每份引用字符数小于8192。所有must_preserve均为完整支持包中真实原文，不使用编辑性斜线/省略号。
3. `author-compatibility.json`：51个完整源引用正支持、151条错误断言、85个联合锚点缺失反例，经现有DU-BENCH evaluator检查通过。它们是显式synthetic source-quote fixture；不冒充产品输出/模型或真实采集。
4. 旧冻结baseline在新gold下仍为PARTIAL/FAIL/FAIL/FAIL；未因gold责任校准宣称产品已通过。

## 独立reviewer下一步

- 先读 `revision_manifest.json`，逐旧事实字段old/new/reason和新增事实检查；再以 `source-bindings.json` 定位原件只读核查。不能只看作者正反例通过。
- 重点复核：HK财务条件责任与经营required覆盖、复式支持的期间/单位/主体/币种是否充分；匿名声源与ASR不确定性是否保守且未遗漏业务；MSFT历史/指引/新旧定义是否完整。
- 独立检查本包未改旧gold/原件；核当前gold SHA与manifest一致。修订意见交ROOT，不把作者QA重命名为独审。
- 生产0.9真正选材、模型task-local闭包、正式摘要、RF采用尚未由本包验证。

## 复现命令

在company-wiki根目录，用已配置Python执行，设置 `PYTHONDONTWRITEBYTECODE=1` 与 `PYTHONPATH` 为仓库根：

```powershell
python -X utf8 docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024/m1-source-checkpoints/build_author_package.py
python -X utf8 docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024/m1-source-checkpoints/verify_author_package.py
```

第一条只会重建本作者目录内gold/manifest/作者结果，读取原件与旧gold而不修改；第二条只写作者fixture报告。作者完成独审交接冻结后不要再重建，以免审查SHA失效。

来源路径仅 `source-bindings.json` 中保存定位与SHA，不复制原件，无密钥、模型调用、下载或生产写入。

## 独审反馈后作者第2版修复（仍待独立复审）

- 买断确认对比补真实09:41“说话人1 它不像”AND，连同09:24/09:42，保留匿名role unknown，拒绝省略否定连接。
- Azure完整新定义补Healthcare/LifeSciences从Azure移往Industry solutions；保留GitHub/developer/Security Copilot移往M365的另一分支。
- 总公司旧July29收入区间与Adjusted Total Company No change联合，不用“机械调整”泛句推导总额不变。
- 对全部51事实共因复核否定/限定/旧新口径；bookings、RPO与座席定义额外带FY27来源版本，避免只修个别词。
- `revisions/author-v1/`保留被改两份先前作者gold；`author-revision-2.json`记录作者v1→v2逐字段变动/理由及四组复核范围；`revision_manifest.json`仍保留原冻结gold→最新版完整差异。

最终作者QA：4份load/现evaluate、139锚点原件核验、51事实源正支持、151错误断言与85缺联合锚点反例通过。仍不是独审接受；等待独立reviewer重新绑定最新SHA。
