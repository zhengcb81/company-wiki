# M1 新版源侧 gold 独立审查

## 结论

**PASS，范围仅为作者 revision 2 的四份源侧 gold 及其可回放交接。** 51 项事实已逐项实读原件并审查充分性；最终 139 个来源锚点均通过原件核验。独立测试 **102 passed / 2.99s**。本结论不表示生产选材、正式摘要、缓存恢复、整体准确率或 RF 已通过。

审查 ROOT HEAD：`a83863894fe5db5ad8a2afa39a7a994eb1f35b10`。ROOT 同时实施 M2，本次未调用产品选择器，不审查或代签并行产品修改。最终 16 个作者交付文件、benchmark 验证代码、旧 gold、原件在末轮测试前后保持相同字节；完整 SHA 在 `final-bindings-and-cleanup.json`。四份最终 gold：

|样本|最终 SHA-256|
|---|---|
|Gbits|831299c7393e4978f77b8811f31005df74310b27191d84192d6a332b7a4bb14a|
|Proya|e2aeaf5c9344f82e7be802e612e1b7eed5f369c647dec4c0acc95788f75cc7b8|
|Kingsoft|1d3e2d29436ba92758500039d75d9d24a1fdd84b9fefc9f0bb539e495a9d2604|
|MSFT|abc0f51255a55f1da13cf07e8d627e8606468e7cd677d30744679ab191718231|

`revision_manifest.json`：`d68b55bf8da6eed73eeb8c9e5bbb1b24dd3a54b8f31a0dec92b6a0413babad08`。

## 实读与语义检查

- Proya：原 PDF physical 1/2/3/5/6/8/12，10 项。直接核对跨页表头、Q1 与期末/上年末、人民币元与元/股、归母/扣非、正现金净额与负同比、股本货币额与回购股数。P1/P2 另渲染视觉检查。
- Kingsoft：原 PDF physical 5/9/11/12/13/14/15/41/45/50/64/66/67，16 项。核对千元/百万元、人民币/美元列、US GAAP 与 IFRS 对账、便捷汇率限制、毛利额上升但率下降、AI/行业扩张与 CDN 缩减抵销、不同云业务增长原因、采购协议承诺与履约阶段。P12/P66 另渲染视觉检查。
- Gbits：实读 DOCX 完整对话，13 项。匿名 speaker 只能证明 discourse 角色，不能验证公司高管/分析师身份；保留“会不会”“Oa/买了”“2000多用户”“利息负债”的 ASR 不确定性。企稳/更新/降低买量依赖均区分意向与结果；省略比较否定会改变收入确认关系。
- MSFT：实读完整 HTML，12 项。核对 FY27 新旧分部/指标、商业 bookings/RPO 定义、期末付费座席范围、旧 July 29 指引与机械改列、恒汇率/FX、美元 billion 与 million、FY26 重述表及前瞻限定。封面仅月年，不能由文件名补具体日期。

51 项单独的原件位置、语义理由、责任和最终 verdict 在 `fact-semantic-ledger.json`。PDF 页码是 physical 1-based；DOCX P 与 HTML S 是此次阅读的 0-based 段落/stripped-string 参考号，不冒充产品 SourceRef。

全部最终事实只有一个 AND 支持集，故无待靠 OR 猜测的充分性。不是只对 139 个字符串勾选：已核其主体、时期、列头、单位、条件、比较对象、否定、版本和共同支持关系。

## 独审发现并已修复的三项问题

|问题|原件证据与根因|最终处理|
|---|---|---|
|电话会比较否定丢失|09:24 与 09:42 之间有 speaker1 09:41“它不像”；缺它时后句反而像在说同样递延|三个回合 AND，保留“它不像”；不伪造同一回合，role 仍 unknown|
|Azure 新定义不完整|GitHub/developer/Security 移出之外，Healthcare and Life Sciences cloud 也移至 Industry solutions cloud|完整范围进入同一支持句及 must_preserve；保留 CC、FX、FY27Q1 和旧指引时点|
|当前总额缺少旧新连接|89.85–90.95 billion 在旧 July 29 列；泛称机械调整不足以独立证明该总额不变|加入 Adjusted Outlook 的 Total Company No change 联合锚点|

作者保留了两份 v1 gold；独立将上述三项探针对这些旧字节执行，**三项均 EXPECTED_RED**，见 `v1-sufficiency-red.json`。同一探针对最终 v2 通过。作者还从同类版本问题给 bookings/RPO/seat 补 FY27 原文标题；独审确认标题和定义同属实际 FY27 页面语义。

无剩余阻断项；没有替作者编辑 gold。

## 责任迁移与历史可回放

旧 47 个 ID 和 importance 全部保留，旧错误反例逐样本保留；采购单位反例由 period-meta 移至新增采购事实。原 gold 和原 DU5 manifest 字节未改。独立按 `revision_manifest.json` 的 old/new 字段从原 gold 重建出最终 raw JSON；另从作者 v1 按 revision-2 重建全部最终 fact 字段，均一致。

Kingsoft 的 required 数确实由 8 降至 7，critical required 由 6 降至 2，不能把它隐瞒成原分母不变或直接比较一个“改善率”。迁移的四项是精确财务数、两项是会计/单位元数据；毛利率经营解释和重大投资计划仍 required，又提升下半年业务展望、经营分部结构，并新增 AI/行业/CDN 完整驱动、按业务分别归因、IDC 合同阶段。四个精确数仍保留 critical 及所有错误断言检查。未将真正经营机制移出责任以换绿。

四份都是已诊断的 **development**，`support_set_frozen_before_output=false`，不是 fresh holdout。独审先完成原件语义判断，再回放旧观察；没有用当前产品 selected 反向改造 gold。同一旧观察对旧/新 gold 仍是：Proya PARTIAL/PARTIAL，其余三份 FAIL/FAIL，见 `frozen-replay.json`，没有假称产品已改善。

## 独立执行与边界

复现：仓根设置 `PYTHONPATH` 为仓根、`PYTHONDONTWRITEBYTECODE=1`，执行：

```powershell
python -m pytest docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024/m1-independent/test_semantic_review.py -p no:cacheprovider --override-ini addopts='' --junitxml=docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024/m1-independent/independent-tests.xml -q
```

102 项包括：真实 SHA/全部原件锚点、旧 ID/importance/反例、逐字段回放、最终交付绑定、51 项现有 evaluator 可消费正夹具、三项修复探针、ASR/匿名角色、HK 经营责任、10 个关键 AND 缺件、13 个风险错误断言、错页/错 SHA、同 discourse 跨 scope 拼接、context 不可替代 required business、四份旧观察双版本回放。只使用现有 `load_gold`、`evaluate`、`verify_gold_anchors` 等接口。

正夹具是明确标识的 **offline source-quote fixture**，不冒充真实生产选择结果；字面反例被捕获也不代表通用语义蕴含已自动解决。51 项充分性是本独立 reviewer 实读裁定。最初本 reviewer 的 1F/88P 是 replay 误将 `load_gold` 的派生/default 字段当作 raw 交付差异；仅修独审测试比较对象为 raw JSON 后通过，没有修改 gold 或降低作者要求。历史日志留存 `initial-tests.xml`。

四张临时渲染图已视觉检查并删除，留 SHA/大小收据；无原件副本、临时图、pycache 残留。未下载、未调用模型、未改产品/原件/作者包/共享 PWF。未执行作者写入型 QA 脚本。正式摘要、RF 端到端、fresh holdout、全部业务覆盖完整性与 M2 生产效果均留给 ROOT 后续验收。
