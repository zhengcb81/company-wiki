# 局部原文流升级：跨市场／文种独立来源预检

## 结论

**发现真实来源／输入缺口，不能签收内容全绿。** 微软的业务层级局部绑定仍有一项不完整；金山云中报存在遗漏、断句与期间上下文缺口；中微招股书在共享工作量上限内耗尽并停止。本轮没有模型请求，正式摘要语义 **NOT_REVIEWED**，RF 实际采用 **OPEN**。

| 冻结来源 | 实际生产选材／v4 输入 | 工作量 | 本次结论 |
|---|---|---:|---|
| Microsoft FY2025 10-K HTML | 112 span／40,491 字符／50 task | 13,577,692 / 16M，未耗尽 | 原 8 个必需事实：**7 PASS、1 PARTIAL**；不是旧宽松引句 OR 的 8/8 代签。 |
| 金山云 2025 中报 PDF | 112 span／6,522 字符／60 task | 3,644,236 / 16M，未耗尽 | 对裸 compiler material 的完整联合命题：**1 PASS、4 PARTIAL、2 MISSING**。若只看经营正文则 3/2/2，不能用后者代替完整期间／范围验收。 |
| 中微公司 AMEC 招股书 PDF | 429 页／14,025 原生单元；最终 0 span／needs_review | 15,999,740 / 16M，已耗尽 | **NOT_GRADED**：没有正式内容 gold，且按指示停止，未再编译模型输入或重跑。不是 SMIC，也不是鼎龙扫描确认函。 |

## 身份、预算与操作边界

- 实测 HEAD 前后均为 `483cb2a56299cb28ca07bbd349674860baf04430`；375 份 Python 源码及 reading catalog 的完整字节清单见 `start-bindings.json`。成功选材 owner 的 17 份文件与 `06c1a583` 节点一致；期间生产树没有漂移。已有 `.githooks/pre-push` 工作区差异仅记录，未处理。
- 三份原件均由生产配置的只读 `SourceVersionReader.open_version` 验真；SHA 分别为微软 `99d693f6…01d0bbe`、金山云 `4f589193…a41bd36`、中微 `19cdb41e…830be67`。原件未复制，目录库写 Store 未构造；source catalog 配置、DB 和 budget 配置 SHA 前后相同。
- 两份 PDF 的 parse 与 select **使用同一个** `new_document_work_budget` 配置账户；均显式限制最多 112 span，未运行旧 m3 分开重置阶段账户的 helper。微软 HTML 使用既有有限 NormalizationLimits；其前端没有 WorkBudget 参数，`parse_work=0` 只代表该计数未计 HTML 解析工作，不能说解析零成本。
- 微软与金山云分别实际编译一次 `reading-model-input/4`，payload SHA 为 `fa22c2931586b51f56df0b24e43002eb82df2efcd0ee16f8e16f50a072b872f6`、`8247e17e3d527a657c359f79a5c6ab5ac4e85fd5889d6e70888a07bf2adc9ee7`。角色与可见任务取自同一实际 compiler view，不使用旧投影代签。
- 所有 API／模型／下载／原件副本为 0；没有临时目录。独立 harness 最初在解析前因 SourceRef 没有 `to_dict` 启动失败，已只改本目录脚本用 `asdict`，首轮记录保留；该次没有 parse 或 select，不是产品故障。

## 微软：数字与机制大体齐，层级不能靠弱 OR

7 项通过的是 Azure 消费制机制、三个报告分部、2024 年 8 月分部调整与重述、M365 Commercial／Consumer 指标差异、Server 23%／Azure-and-other 34% 的不同口径、375／368 billion RPO 及未来 12 个月约确认 40%。具体完整引句和 task S/C 在 [final-report.json](final-report.json)。

**层级仍 PARTIAL：** 当前 t19（`paragraph:224`）的支持正文为 Intelligent Cloud 的介绍，结尾是 `This segment primarily comprises:`，后面的 Server／Azure 列举子项没有进入该任务。t20 的 Azure 消费制说明、t7 的 Server／Azure 增速本身完整，但自己的 context 中没有 Intelligent Cloud 父级。

原 gold 的 OR 允许仅凭 Intelligent Cloud 介绍通过，强度低于其“IC → Server products/services → Azure and other”的完整命题。本报告同时保留原 OR 观测和更严格的局部关系判断，不改金标，也不从别的 task 只有 IC 一词代签 Azure 归属。建议在 DOM 列表／标题和局部任务依赖 owner 查明共因，用中性父子／兄弟业务反例回归，不能新增 Azure 专用字符串。

## 金山云：七个必需事实逐项结果

| 必需事实 | 当前裸 material | 实际证据／缺口 |
|---|---|---|
| 毛利额改善、利润率下降及原因 | PARTIAL（正文 PASS） | t37 的 `p13/29/chars795–950` 同段保留毛利 +7.4%、15.2%／16.7% 与 AI 服务器、客户前期成本原因；本次裸输入缺可适用的共享六个月期间。 |
| 无重大投资及未来重大资本计划 | PASS | t40 的 `p15/21/chars966–1071` 同时具备 2025-06-30、5% 阈值及两项否定。 |
| 下半年 AI／小米金山生态计划 | MISSING | 原件 p11 的冻结引句存在，但当前选中的 p11 只是研发平台描述，不能代替下半年计划。 |
| 单一经营分部与不列地区分部 | PARTIAL | t59 的 `p50/25` 有单分部及 CODM 依据，缺“中国内地主要收入／资产、因此不列地区分部”的互补定义。 |
| AI／行业云增长与 CDN 抵销 | PARTIAL（正文 PASS） | t28 的 `p9/6/chars89–287` 因果与抵销完整；裸输入期间限定仍不足。 |
| 公有云／行业云各自增长驱动 | PARTIAL | t35 的公有云 +23%／AI 原因完整。**t1 的 p13/9 只到上一年金额 1,245.4 就断开**，缺单位、7.6%、IT 需求与垂直行业方案复制续文，且 `quality_flags=[]`。不能从 t28 的另一口径数字补齐。 |
| 不可取消一年 IDC 采购合同阶段 | MISSING | 原件 p66 的日期、630,000／576,101、协议与剩余承诺存在；当前没有选入。不得把采购承诺当收入或已履约。 |

### 期间只需来源责任层负责一次

本次审查的是 `compile_scoped_model_view.to_model_dict()` 的 **裸 material**。其共享头是 schema／scope／预算、fragment/task defaults、shared fragments 和 tasks，没有经来源 owner 验证的 document-level period／fiscal_period。其他现金流 task 里的六个月表头不能任意借给 t28／t37。

但是，**经来源 owner 验真的共享期间字段或足够明确的共享标题，可以一次限定所有适用任务，不必给每个 task 重复塞 p5 标题**。本次没有建立正式完整 `NarrativeModelRequest`，因此不宣称所有生产完整请求一定缺期次。静态源码可见当前完整请求另加 source.language/title/document_kind 与 reading_strategy；其实际共享信息应在正式来源准备／请求节点核验。1/4/2 是本次裸 material 的联合命题覆盖，期间结论保留这一边界。

## 中微招股书：先定位工作量，不直接加额度

parse 使用 420,052 工作量，得到 429 页、14,025 单元。之后同一账户累计到 15,999,740 / 16M，候选数 8,361，最终没有输出可用选材，状态诚实保留 needs_review。停止行为本身没有伪装通过，但对长招股书的有效产出不足，是需要后续定位的效率／容量问题。

本次没有正式 cn-ipo 内容金标；既有 m3 检查只是历史来源绑定／任务预检，且曾使用独立阶段账户与 160 span，不能与这次直接比较或当内容召回通过。本次不从已选结果倒推 gold，也不将鼎龙确认函冒充中微招股书。

建议单独统计共享账户的实际阶段与调用热点，再决定优化候选规划、复用或可恢复处理。不能只凭本轮总数猜某个阶段慢，也不应直接提高 16M 限额。ROOT 另要求的新有界热点 profile 将独立留证，不修改这三例的结果。

## 干扰检查与金标卫生

五条已有指标定义／实际增长／审计培训正反控全部通过：审计取样、培训用 revenue/includes 不成为经营指标；真实 service revenue 定义保留；paid seats 的实际增长和纯定义没有混淆。

所有 required 原始支持引句均在 SHA 绑定的原件解析单元里找到，**不等于它们已进入实际输入**。两例金标还保留所有条件财务／元数据目标，本次没有模型输出，不能签这些数值的输出正确性。

原 US 金标 RPO 解释中的 7,265 million 与其独立未实现收入目标的 67,265 million 存在旧解释不一致；保持原文件，单独指出，不凭此制造模型错误。HK IDC 正文“元”与全节“千元”展示基准必须联合读取。HTML 的旧 page=1 是虚拟文档定位，不能称为物理 PDF 第 1 页。

## 后续责任与限制

1. CWP 层级／上下文 owner：修复 IC／Server／Azure 局部链，不用宽松 OR 代签。
2. 原生 PDF 断句／任务准入 owner：查行业云断尾和互补定义遗漏，保留主体、单位与完整条件；没有全部闭合时不得把半句当干净事实。
3. 来源期间／预算分配 owner：先核完整请求是否已有共享期间，再处理真实的计划与合同阶段漏选，避免重复身份／期间验证和发行人专用清单。
4. 共享工作规划 owner：单独定位 IPO 15.58M 消耗，保留原限额与停止结果，不重跑原样实验。

本次未跑全量测试、未改产品或旧金标／PWF／外包工区。原始读取和实际任务依据由公共解析与 compiler 产生；这不是每个 span 的独立视觉重渲染检查，也不证明全篇召回、正式摘要、缓存恢复或 RF 通过。
