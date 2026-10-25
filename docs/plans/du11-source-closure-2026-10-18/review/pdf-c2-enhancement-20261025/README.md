# PDF-C2 段落按需增强实施与验收

状态：IMPLEMENTED_REAL_RECALL_IMPROVED_FINAL_REVIEW；基线8669e0cd。前置H1/DOCX根修已关闭，不重复整批或旧算法超时实验。

## 实施顺序

1. 复用已冻结三源五页与8条段落检查点，定位两缺组的物理证据/摘要任务边界。先以中性夹具冻结分诊、严格对齐、兄弟事实隔离和最终任务成员的RED。
2. 在PdfReading职责内新增小型paragraph DTO/对齐与分诊；只接受同源/同页/原顺序/唯一完整成员/有效frame和几何/严格字符等价。保留native文本/ID/locator，hint仅瞬态。
3. 将通用membership proof接入现有observation_adapter→continuity→reading packages→summary tasks；外部段落不是独立事实，不提高8unit/4block/2048字符界限。
4. 复用已有进程树/有界传输设施，接入离线、限定页、限定启动/总时长/内存/响应字节的懒加载Docling；有限阅读生命周期复用热实例并显式close。设置、配方与版本由阅读层负责，AUTO/FF/RF不解释SDK或选项。不复制原件/全文MD/页图，不下载模型。
5. 集中中性/集成/真实五页验收：原6条保留、两缺口改善或给出明确未采用原因；直接检查实际summary任务成员。新原件泛化按实际可用来源冻结；不拿工程成功冒充召回提升。
6. 独立agent审源码与收据、修共因；正常提交推送、核精确CI，更新唯一PWF入口。C3正式摘要语义/cache/RF仍单列，不代签。

## 既有证据与约束

选型/详细约束：../pdf-parser-reuse-pilot-20261025/{decision,implementation}.md。四份gzip已保留原SHA与长度，不重复跑研究比较。既有Docling2.96本机模型冷启约84秒、RSS约1.06GB，因此不能把15秒原生layout预算冒充重模型启动预算；资源不足原生回退/partial并留原因。原生默认保持可用，只有明确启用且冻结配方的增强器可以参与。

本节点不写W19/作者工区、RF WIP或Dayu/IQS；原件保留。只在ROOT独占短路径测试并恢复初态。所有新增检查都是数据/资源正确性，没有人工许可、签收JSON或第二任务库。

## 2026-10-25 实施发现及口径修正

- 初审核对真实原文：HK行业云4成员/3物理块确有缺口，首行bullet左缘偏移22.68pt导致旧2.1em几何规则未闭合。字体、scope、role、column均相同，故不放松这些反证。
- IPO刻蚀与MOCVD并非漏内容：原生已有两个各自完整的经营事实和引用。历史同组检查要求把独立事实跨6物理块合并，与4block上限冲突。保留历史6/8指标，增加版本化逐事实检查；不扩上限、不以更换口径冒充新增召回。
- 冻结观测回放已证明HK实际摘要任务从缺失变为完整，三项年报原检查保持；不是LLM正式摘要语义或新盲测。完整原件分诊初版错选前3页，独审识别后已从根因删除第二套业务词典，复用原生物理邻接以排除已可闭合边，再给数字/单位断裂排序。完整HK自然需求现为12/13/17，IPO为219/229/256，不为其已有完整的114页启动重模型。
- 对齐初版中心点准入被独审2pt细条反例推翻，已改为完整native block覆盖＋实测字体四分之一em（2–3pt）有界padding，字符和原序仍须全等。坏JSON各层结构均显式拒绝并保留原生结果。
- recipe事前绑定Python/SDK依赖、权重/config SHA、对齐/调度/worker源码SHA；原生recipe不受未启用SDK影响。实际引擎及回退阶段单列。
- 当前runtime是每次有需求的read一个有界离线子进程，单converter热复用所选多页，退出即释放。**尚非跨文档热池**；不能宣称已经消除每份有需求文档的模型冷启。若后续吞吐需跨文档复用，应在现有有限Worker生命周期内实现并专项验收，不新建守护服务或任务库。

## 可复现实验与当前边界

`verify_real.py --mode frozen --output 唯一名称`读取仓内冻结观测和3份只读原件，先完整原生读取/分诊，再仅在冻结5页做选择/实际summary task与locator核验；非冻结页显式partial。`--mode live --runtime-config 本机配置.json --limit-sources 1`对首份原件的自然需求页真实运行本机离线Docling，未改金标准或限定目标页。测试应把TEMP/TMP指向自己拥有的短临时根，结束恢复初态；不能把沙箱虚拟TEMP权限错误当算法缺陷。失败尝试与最终成功收据分开保留。

部署从阅读owner的`COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG`选择显式本机JSON，schema为`pdf-paragraph-runtime/1`；字段由`ParagraphRuntimeConfig`校验。需要配置既有解释器、既有模型目录、权重与config SHA及全部实际依赖版本；路径只保留本机、不进入recipe或证据。未选择时保持纯原生生产默认，不能宣称全局增强已打开。不自动发现解释器/安装SDK/下载模型。

C3正式LLM摘要、语义审查、缓存恢复及RF消费仍为独立未完成节点；本轮段落/task召回不能代签。

## 验收结果（先读本节）

| 检查 | 结果与证据 |
|---|---|
| 中性、契约及生产阅读回归 | `final-focused-receipt.json`：229 PASS，28.34秒测试时间；最后实际观察接缝的`final-execution-recovery-receipt.json`：36 PASS；计数重叠不相加 |
| 三原件五页对照 | `final-frozen-v4.json(.gz)`：先对整份原件自然分诊，再只在冻结5页进行显式partial选择。原同组口径6/8→7/8，保持未过的IPO跨独立业务同组项false；逐事实v2为8/9→9/9 |
| 真实离线增强 | `live-hk-calibration-v5.json(.gz)`：整份HK原件自然选择12/13/17页，1个converter热复用3页，接受3组、拒绝128组，81.1026秒，保持120秒上限；原生的HK行业云任务缺口真实补齐 |
| 内存根因 | Windows Job硬限是提交内存；早期1.06GB是RSS，不可混用。2GiB实际导致首需求页转换失败；显式4GiB成功，实测Job提交峰值3,327,328,256B（约3.10GiB）。默认校准为4GiB，用户显式低限仍遵守并回退，绝不自动突破 |
| 精确引用与恢复 | 独审`final-source-replay.json`：29/19/15条span逐原文/坐标回放无失败，所有task member/support/text/locator一致，hint不持久；过程不导入Docling/不收费。正式Store缓存发布/C3语义并未因此完成 |
| 实际状态不丢 | `reading_execution`白名单进入既有coverage→reading_context，保存成功/未运行/回退、实际引擎与阶段；严格wire冻结/JSON恢复保留值，原始gap详细信息不持久 |
| 原件与配置 | 运行前后SHA相同，临时根恢复不存在，0下载、0模型下载、0付费LLM调用、0原件副本 |

失败尝试保留各JSON收据及原因，不将它们改成成功。最终冻结回放与live是真实任务材料检查；不是全文无遗漏、typed业务表已恢复、正式LLM摘要质量或新盲测通过。部分IPO/年报自然需求页不在旧冻结外部观测中，frozen回放明确报告无可对齐结果并保持原生，不能说这些页做了新Docling推理。
