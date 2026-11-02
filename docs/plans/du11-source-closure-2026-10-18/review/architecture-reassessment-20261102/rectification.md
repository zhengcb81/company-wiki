# 整改效果独立复核（2026-11-02）

范围：只读当前源码与PWF；不修改产品代码，不调用模型、provider、真实catalog，不修改生产配置/原件。当前主线已发布整改的既有完整测试不重复运行。以下只执行新发现路径的隔离小探针，并抽验已修行为和已知语义缺口。

## 结论

**不能写成“之前所有问题已经全部解决”或“过度门禁已清零”。** 已处置项有真实正向效果，但旧清单是有限范围；这次在未覆盖的生产入口发现同类残留。另一方面，来源父链、条件保真以及新摘要/cache/RF实际采用仍是明示未完成事项，不能由工程CI绿替代。

|核对项|当前结论|实际证据|
|---|---|---|
|生成摘要20条配额|已移除，正向抽验成立|调用公开 legacy decode，21份独立完整引用全部保留21条；见probe中的`claims_retained`|
|已有工程整改/跨仓发布|证据有版本范围，不能外推所有caller|上一节点`gate-rejection-followup-20261102/closure.md`、`publication.json`；原41项清单明确Q01/Q02/Q12真实C未完、Q11有理由保留|
|SEM-QUAL-01计划/验收条件升级成actual|仍未修，当前源码复现|原文“公司计划在项目建成后…”及“仍须客户完成验收后方可投产”均引用，claim变“公司已…”。legacy和v7皆draft/needs_review=false，prose/atomic诊断空；不是门禁问题|
|T4真实来源父链|仍未验收，未重跑真实H1|`T4-source-note-parent-plan.md`：group25/28/65继承旧p34局部备注标题；12/12召回不能证明上下文归属正确|
|新版真实摘要/cache/RF采用|仍OPEN|CURRENT_STATUS、HANDOFF、原T4；本轮探针不是这些实际验收|

## 新确认的同族残留：本地输入表示被当成许可

这些入口都不是网络响应无限读取。当前函数在合法JSON进入所属schema/配置owner前，按不可配置的序列化字节数拒绝。空白等价探针用于区分表示门与内容错误；并不声称现实用户已遇到每一个边界。

|生产路径（当前行号）|探针结果|处置建议|
|---|---|---|
|`src/company_wiki/source_catalog/narrative_normalization.py:59`，读65537B/大于65536则`OCR_CONFIG_TOO_LARGE`|合法OCR配置695B通过；只加空白66231B拒绝；解析后的对象完全相同；未启动OCR|与所有本地配置/输入codec一起清理，不新建许可；保配置字段/真实模型身份/实际OCR资源检查|
|`src/company_wiki/source_catalog/source_export_v2_cli.py:45`|合法空ref/span请求66B返回`((),())`；同对象加空白16777282B得到`request exceeds limit`|CLI应调用同一语义owner，不能另设16MiB请求表示许可|
|`src/company_wiki/source_catalog/official_source_cli.py:35`|读取器接收54B合法JSON；同对象65590B得到`request_byte_limit`|这是读取器复现，未运行捕获/下载；保JSON/schema验证，移除独立64KiB序列化门|
|`src/company_wiki/source_catalog/source_query_cli.py:43`|315B合法SourceRequest到达配置owner（替身OSError→reader_unavailable）；同对象65851B被blocked/invalid_request，尚未到配置owner|用公共CLI复现，未打开实际catalog；修复应同时覆盖复用查询链|

实际调用可达性：`narrative_transport.py:362`通过`NarrativeNormalization.from_reader`加载上述OCR配置；`narrative_batch.py:1505`直接`from_project`。三个CLI均为当前公开入口，而非历史脚本。CodeGraph定位后读具体源码；其跨文件caller查询有未解析结果，故未把“no callers found”当作不可达证明。

其他线已发现并由对应独审负责的同族问题：CWP电话会import的16/25MiB等上帽（FF/ET已改不代表CWP接收完成）。不在本报告重复运行昂贵/大数据探针，见boundary报告。

## 需要分类而非一刀切的候选

- `official_source_flow.py:778`仍限制显式capture `max_bytes<=128MiB`、`max_seconds<=300`。这是实际资源参数的不可提高二次常量，**不是已生成结果后置拒绝**。应由资源owner梳理成可配置默认/共享父账户，不应机械删掉实际下载预算。本报告只读确认，未发真实请求。
- `document_understanding/summary_tasks.py:153`对`citation_views`要求1–2。是否两类角色已经在协议中构成真正有限集合，须检查producer的实际角色模型。不能只因见数字就宣称错误。本报告不将它计为已确认缺陷或已修。
- `narrative_contracts.py`仍出现旧MAX_BYTES常量和handler的ContractSizeError捕获，仅凭名字不足以证明active拒绝；需要查实际执行分支。本轮未误报。
- `narrative_summary_assessment.py:26,191,220`有限诊断采样保留总计和`diagnostics_limited`；其64条样本限制不直接拒任务，不能与来源丢失或summary配额等同。

## 第一性原理判断

这里暴露的主要共同原因是**接口责任没有完全归一**：采集方按请求预算成功，下游接收/CLI/持久化又各写一套默认常量。逐个删常量会反复漏下一段。应按一条真实数据路径列“请求→传输→解析→持久化→消费”，每个资源只保唯一记账/限制owner；各adapter只解码、验证实际结构和绑定，观察失败与业务结果分离。对已被同owner验证的不可变对象内部复用；跨进程公开字节入口仍由接收owner验真实字节。

语义缺口的共因不同：`narrative_summary_assessment.py:30–35,99–139`是有限词法诊断，引用完整≠条件保留。应复用来源结构/限定scope表示，统一条件、时间、否定、主体的绑定，明确未知，不能再加公司名或单句regex，也不应新建人工签收语义许可。让CWP输出可追溯材料与限定；现实事实判断和投资结论仍归下游研究。

## 探针与清理

可重放脚本：`rectification_probe.py`。从company-wiki根运行：

```powershell
C:/Miniconda/python.exe -B -X utf8 docs/plans/du11-source-closure-2026-10-18/review/architecture-reassessment-20261102/rectification_probe.py
```

脚本不读取生产config，不写仓库/数据库，不加载模型文件，不联网；仅OCR/official输入测试用系统唯一临时目录，退出自动删除。其他只用内存JSON/BytesIO；query配置owner被显式替换为抛OSError，不伪称业务查询成功。source fixtures由已有测试支持构建。

保存后的脚本实跑exit=0，5.81s；`temporary_directory_removed=true`。输出：OCR `{695,66231,true,OCR_CONFIG_TOO_LARGE}`；official `{54,65590,true,request_byte_limit}`；export `{66,16777282,true,request exceeds limit}`；query compact owner_reached=true/reader_unavailable、padded owner_reached=false/blocked invalid_request；`claims_retained=21`；SEM两decoder均draft/needs_review=false，两个diagnostic列表皆空。这是问题观察结果，不是产品验收PASS。

原始探索中的错误也保留说明：一条批探针在完成export和official两项后，错误访问`SourceRequest.__dataclass_fields__['max_bytes']`产生KeyError；两个已输出结果不受影响，临时目录在错误前已经离开上下文清理。后续query专用探针已移除该假设，公共入口两种结果均成功捕获。本目录重放脚本为纠正版本，不宣称原失败不存在。两次rg在Windows传未展开glob路径报os error123，改用目录+`--glob`读，未影响源码。

建议ROOT按“已确认残留表示门”作为原整改包增量，由CWP owner一并处理；当前工作不做无限全仓扫数值、不扩新产品目标。此报告是复核/规划输入，不是整个项目验收通过。
