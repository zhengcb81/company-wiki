# W21-PDF-RUNTIME：PDF增强运行时冷启动、隔离与真实入口验收

状态：DISPATCHED / AUTHOR_IN_PROGRESS。用户已确认发出；2026-10-30只读观察作者HEAD为5a33d923、progress文档尚有在途改动，卡上指定路径尚无最终handoff，不能代签验收或重复开包。这是本轮唯一新包，直接解决主线已知SDK阻点，不是重新做PDF选材或已完成W20。

- 工作目录：`C:/Users/郑曾波/Projects/company-wiki-w21-pdf-runtime`
- 分支：`codex/w21-pdf-runtime-20261029`
- 冻结基线：`bb5d09c056ca36bba8061d761b5469d87aa6e5e0`
- PLAN_ID：`w21-pdf-runtime-2026-10-29`，PWF_PLAN_ROOT：`docs/plans`
- 本卡/PWF：工区`docs/plans/w21-pdf-runtime-2026-10-29/`
- 交付：工区`delivery/w21-pdf-runtime/handoff.md`和`.json`。
- ROOT主工区只读：`C:/Users/郑曾波/Projects/company-wiki`。ROOT拥有来源语义A/B、真实摘要/缓存/FF-RF及最终集成。

## 已调查的事实

现有共享PDF阅读门面内部按需增强，`ParagraphEnhancement`位于`src/company_wiki/source_catalog/narrative_pdf_enhancement.py`，子进程是`_paragraph_worker.py`，依赖指纹是`narrative_pdf_environment.py`。上层只用既有PdfReading/来源接口，不能知道SDK选项或物理模型目录。

ROOT已有一个保留的标准隔离env：`C:/Users/郑曾波/Projects/company-wiki/.planning/c3-20261028/pdf-sdk-isolated/`。请先只读其`handoff.md/json`、`selected-manifest.json`、`deployment.json`、`light-check.json`（实际文件名以目录为准）、`runtime-isolated.json`及cold收据/脚本。其Python是`env/Scripts/python.exe`。选定104发行包与426个全局可见包隔离，36,121文件使用hardlink，1,233,549,343为共享逻辑字节，标准scaffold新增517,241B；不得再次拷SDK/model或把逻辑字节写成实际新增磁盘。

现environment metadata SHA为`c84a984ccb3a56dffbfd0d4538f14ce4a27de44dec4981527a2b0c4a545cdf44`。模型artifacts路径、模型/config SHA及精确版本在runtime-isolated.json中，必须读取配置，不拍脑袋。旧no-document cold只跑了一次30秒界，18.81秒时torch→dill打开标准`os.devnull`/Windows NUL的r+b被**探针自己的写盘guard误拦**，不是用户权限不足，也不证明缺包或SDK就绪。旧失败和single-cold-attempt marker原样保留，不能删marker重发旧命令或改旧结果为绿。

轻量证明用了-I并清理Python环境，但生产`ParagraphEnhancement.enhance`当前从`dict(os.environ, ...)`继承父环境，实际worker可能受PYTHONPATH/PYTHONHOME/用户site干扰。本包要解决实际启动路径，不能仅交一个在干净shell成功的旁路demo。全局技能MIC拒写已另修，不重开那项，不改ACL/MIC。

## 独占改动边界

仅可改：

1. `src/company_wiki/source_catalog/narrative_pdf_enhancement.py`中的运行时启动、child环境准备及其recipe依赖绑定；保持现有增强/对齐调用和公共门面不变。
2. `_paragraph_worker.py`的启动/依赖导入/资源与故障观测；不改变解析内容、模型选项、段落成员身份/offset/页码/角色或checkpoint含义。
3. `narrative_pdf_environment.py`仅实际隔离/依赖观察的必要兼容修复；若无缺陷不强改。最多新增一个同前缀`narrative_pdf_runtime_env.py`私有共享helper，若新增必须进入既有recipe身份，不能藏当前执行变化。
4. 相关`tests/unit/test_pdf_runtime_environment.py`、`test_pdf_paragraph_runtime.py`、`test_pdf_paragraph_reading_integration.py`及新增`test_w21_pdf_runtime_*.py`；本卡PWF/delivery；必要小型`tools/pdf_runtime_probe/`探针与fixture。

禁止修改：ROOT正在施工的`operating_states/`、`assertion_roles`、`narrative_business_*`、`narrative_operating_relations`、`narrative_support_use`、`narrative_reading`；PDF策略/候选/triage/geometry/planner/表格/原文对齐算法；通用`_bounded_process.py`/`_process_tree.py`；LLM/worker调度、预算、配置、writer/reader/cache_store、其他仓、全局技能、Dayu/IQS/Dashboard和ROOT共享PWF。若共用过程层确有缺陷，交最小反例给ROOT，不跨范围补。

物理工区已不同，允许写的文件也与ROOT不同；ROOT本阶段不修改这三份runtime owner文件、不同时跑增强SDK实测。你不需要等ROOT A/B签收才做A/B/C。上游ROOT source文件变化不是要求你保持全仓旧SHA的许可门；你绑定自己的已提交基线即可。最终集成由ROOT承担。

## 实施与测试

### A 调查、冻结边界（不用额外审批）

先核HEAD/branch/status、AGENTS和既有runtime/recipe/历史publication测试；读准确源码和本机compact证据。工区是稀疏工程checkout，不含companies、历史.planning或SDK；不要关闭sparse或全量恢复。ROOT预置四个本卡计划文件是已知seed，可纳入A提交。Windows伪执行位已仅在本工区设core.filemode=false，共享设置/ROOT原mode WIP未改。若结构检索确需CodeGraph可初始化本工区，不复制ROOT历史索引。

分清：probe false positive、解释器启动/搜索路径、SDK导入/constructor、模型转换、段落对齐/内容召回是不同证明。列出现有覆盖与缺口，冻结少量正反例和实际参数。

### B 先RED，再在运行时单一owner修共因

- 给guard标准discard device做单元正反例：允许真正os.devnull设备，普通文件/相似文件名/路径不能借它放行；不加生产人工门禁。探针新revision留新收据，旧失败不改、不重置marker。audit hook只说明Python可观测范围，不能声称完整native系统调用拦截。
- 用生产真实launch owner验证child搜索路径隔离：父级注入虚假PYTHONPATH/PYTHONHOME/用户site、同名轻量毒化包；child只用配置解释器及显式第一方代码，不读注入包，不更改parent环境。使用假sentinel而非真实密钥，不打印完整父环境。无SDK的轻量子进程测试先跑，不能靠每次昂贵SDK试启动排错。
- 精确runtime/model/config版本和SHA依配置；不装/升级系统包、不改全局环境、不编辑hardlink文件（会改真实SDK源）、不改模型权重、不扫整机找artifact。不引入新DB/调度/权限/canary/授权JSON/新供应商。历史wheel RECORD中6个INSTALLER 4B/pip对5B/conda差异是既知provenance诊断，不能重造全局阻断；明确runtime文件差异才定位。
- 子进程已有绝对deadline、进程树回收、部分页checkpoint和native fallback继续复用，不能续期重试。正常失败/超时/超输出/配置错误/未完成分别诚实，不能把fallback当enhanced或成功当内容正确。
- 配方身份反映真实新增启动实现；已完成旧publication按其冻结recipe继续可读，正在执行/恢复用当前真实配置，不借旧指纹命中新行为。不扩大到上层cache实现。

### C 少量真实入口E2E＋独审＋清理

1. 轻量隔离/错误路径先通过，再做新revision受界no-document冷启动观察；调用已存在env，不重建/复制1.23GB运行时。fresh process不等于操作系统文件缓存cold，不清系统缓存。cold probe30秒；生产总界120秒、3页、4GiB committed memory、CPU4、64MiB input/2MiB output按已配置值不抬。
2. 在独立TMP生成一个小的synthetic PDF，经既有真实PdfReading/ParagraphEnhancement→真实worker→离线SDK→现有响应/对齐入口走一次；原文text/hash和native fallback保留，真实child阶段、模型/环境摘要、时间/峰值/转换器数、completed/pending/实际accepted可复核。最多有限代表页，不跑ROOT整份HK批次，不读取未曝光Berkshire/华利或新公司。不得拿单mock converter冒充真实SDK或拿engine success签业务召回；对齐未成功就明确范围。
3. 故障恢复用轻量/已有checkpoint测试核超时或损坏尾记录，已完成页不伪丢、不补成功；一个实际E2E足够，不追求矩阵数量。不反复跑同配方超时；先查明根因再必要复验，不能提高限额凑绿。
4. 每次测试前记录独立资料根不存在/sentinel，全部输出只在本卡owned TMP。结束回收自己child、删除新增PDF/缓存/DB/输出、恢复初态；不恢复完整备份演练。已有env、model、root原件与旧receipt只读，测试后核相关SHA不变。只交小收据/压缩日志，不提交env、逐页图/大MD或per-file库存。
5. **交接前调用真正独立agent全面检查原卡、差分、已知风险、实际测试与清理，全部范围内问题修好并复审再交。** 保留初审/修复/最终报告，不能作者换名自签或只勾通过。只在这一个大节点审查，不为每个函数要ROOT签收。纯INFO不妨碍进展；不能把本范围缺陷移到ROOT followup伪完成。真正跨层缺口如实交具体接口需求和PARTIAL。

## 输出接口与交接

本包保持原PdfReading公共门面与schema，source refs/页码/原文角色不变。允许的新增观测仅在既有recipe/diagnostic机制或本卡测试报告；上层不用知道SDK设置、环境路径、模型选择或冷启动阶段。ROOT继续业务用途判断与真实摘要，二者通过现有parsed structure/reading_execution/recipe对接。

交`delivery/w21-pdf-runtime/handoff.md/json`，至少写：card_id、实际workdir/branch、base_commit、implementation_commits、最终tested/reviewed commit与有关file SHA、逐需求的implemented/tested/PARTIAL、实际命令/耗时/案例数量/范围、冷启动/真SDK与合成入口各证明了什么、配置/资源和磁盘共享/新增字节、故障与清理收据、独立agent初审/修复/终审路径及OPEN、兼容局限、是否已推远端。未知就是null/NOT_RUN，不编0或PASS，不生成另一条发布授权链。

进展正常commit，已配置origin则推本分支；不自行并master/main、不全局安装、不改ROOT计划。交付后STOP等ROOT验收。ROOT将把通过的补丁与最新A/B并线，使用其新的recipe完成真实HK摘要/缓存/RF；本卡不替ROOT签后面的真实内容。
