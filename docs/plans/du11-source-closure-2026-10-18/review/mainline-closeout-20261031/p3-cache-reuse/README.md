# W12有界来源缓存共因：当前材料证明代替重复付费

当前实现及真实有界验收已独审PASS，无主要OPEN；正常commit/push/新精确CI随后记录。不代签全文召回、生成式自然语言摘要或完整公司买方研究。

## 实证与根修

两次真实H1调用的base/full generation和actual model attemptSHA完全相同、已有2个可见artifact。源工作预算停止导致dependency trace partial，原快速检查将“unavailable”视为cache miss，未读候选便再次付费。旧两次真实请求、未知费用和partial结果原样保留，不把已曝光失败当通过。

Source-select现在提供同一只读服务端口，Worker与缓存重选共用原文/解析/语言/证据验证核心；不创建假job/lease，不新增任务库。raw和official projection共用ReadingReuseVerifier：完整dependency保留快速路径；无法快速证明时，每源最多一次canonical当前重选，以既有完整material SHA、evidence SHA及sent-policy验证当前实际材料，再走public原文/locator/旧artifact验真。材料实变才能成为新生成理由；重选失败/超时不是付费许可。若已观察到当前材料，后续fast声明不能覆盖它。旧partial/未读/原generation/付费lineage不改，不跨run转移旧费用。

## 验证

- 新端口合同测试先4F；真实独立max_tokens=1请求RED为budget_exhausted/MODEL_BUDGET_DENIED，0POST/预留，证明旧路径不能发现已有缓存。
- 六短域137P/7.58s；最后7项cache unit3.01s；宿主候选真实性/显式v5 Worker16P/19.03s。测试范围有重叠，不相加冒独立数量。最初非宿主/较长temp的候选初始化5F留原日志，宿主短root通过；未当产品业务RED或修改断言取绿。ruff及mypy408源文件通过。
- 真实GREEN：新run r1-w12-h1-cache-green1-20261101、refresh=false、max_tokens=1，返回旧exact narrative-91d5a6412b364914988805598f62fb9f /54ccb82a5e14db1a427dc66e485d58298b55f0e186e44c5e7bcc050ea8a0e895/473666B，0新增reservation/POST/费用。旧rows/timestamps/usage日志/两artifact字节、母账1955397tokens/760197microUSD及unknown8+prior7均不变。12.2436s含真正当前选材/验原件/locator，不能称零解析；native新增持久142B，无新摘要body。
- 独审纯内存从两旧bundle重建actual model attempt e45bd06ce12ed100433ec30305dcc2652cbb9db2cdddd0e305a5dec086e89f94，真实wire33858B；覆盖title/coverage、角色/质量/locator/text/context、损坏、超时、一次重选和证据优先级。原native caller logical输入是unbound；HTTP适配器内部绑定8192，不能用先bound logical误算ledgerSHA。
- 真实GREEN后只追加证据优先级单行收紧，独立反向SHA与1F→7P确认所测首候选partial/相同材料路径未变；原真实收据不重签。

短域复现（无真实API/原件）：`C:/Miniconda/python.exe -B -X utf8 -m pytest -q tests/unit/test_reading_cache_reselection.py`。完整source E2E需可读原件和隔离catalog的已存在合法artifact；使用正式configured入口与1token测试请求，不用paid补缓存、不恢复整库。真实RED/GREEN/raw receipts及独审seal见manifest。

## 后续主线

W12已真实consume5个source_quote到used参数草稿/下游公式，并实际compute/report/snapshot及联动stress，仍待executor最终封存和四路独审。source112/2767/4224、66source_quotes及needs_review/partial保留；p11 D&M关键段缺失、预测幅度支持限制与作者旧版本引用错误均不能被本cache PASS覆盖。原文与真实P3数据保留待四审；不扩施工包。
