# G5：三个可同时启动的独立施工包

**当前状态：complete，MAIN已验收、并线并推送（2026-10-07）。** 不重新开工；原卡冻结输入、写集和工作树命令仅为施工历史。实际交付/当前测试、兼容接线、真实安装和未做范围见[MAIN验收](../g5_main_acceptance_2026-10-07.md)。下文原ready/未创建/paused说明不覆盖本结论，三个交接工作树保留。

## 1. 任务与工作目录

| 卡 | 项目与实际任务 | 唯一新工作目录 | 冻结已提交输入 |
|---|---|---|---|
| [G5-CWP-CHECKS](g5_cwp_legacy_checks_retirement.md) | company-wiki：六个旧工程/批处理CLI薄退休、迁有价值测试helper与反例；G2-07剩余 | `C:/Users/郑曾波/Projects/_g5/cwp` | CWP `5d0ad75504a9815febc1bddbe76ae2f667c3e74a` |
| [G5-SID-RUNTIME](g5_sid_browserless_bounded_provider.md) | StockInfoDLSimple：API provider与browser解耦，身份查询也进同预算；G4真实运行补漏 | `C:/Users/郑曾波/Projects/_g5/sid` | SID `0cb3c1f0b4a5784757971265b2b20a7a0b4c5104`；消费冻CWP df7d7ba |
| [G5-RF-INSTALL](g5_rf_selective_installation.md) | revenue-forecast：既有installer增加指定文件/仅差异写/零写plan/准确partial与幂等恢复，三tmp安装测试及实际24条差异交接 | `C:/Users/郑曾波/Projects/_g5/rf` | RF `ab7a7a4434bbb4c52a5bd2a6cd6ed710d7151eee` |

RF最适合较弱模型，范围窄、真实差异已数清；另外两卡可较大幅度重构专属部分，但以公开合同/反例验收。不是重派G3包装/G4发现/旧审计卡。

## 2. 互不重叠的所有权

- CWP外线：六旧scripts、只涉及六名字的writer_policy、旧control、自己测试。整个`src/company_wiki/**`、public CLI/acquisition、配置/源码指纹/hook/CI和总PWF禁写。
- SID外线：provider/CLI/HTTP预算与新纯身份/过滤模块、有关测试；legacy downloader/browser/mapping/logger/models/owner资料禁写。仅在自身新树写，不改任何CWP配置。
- RF外线：仅`tools/sync_installations.py`及指定仓内tests、自己交接；runtime scripts/config/reference/SKILL、owner日志/home安装禁写。
- MAIN：未完G2-12的CWP获取/公共CLI/FF、公共指纹/工程清单/生产配置、实际用户安装、生产metadata/final、总PWF和所有合入/推实际主线。主线若恢复不写三外线owned files，必要公共接线等交付。
- Dayu/IQS零写；其他项目不随卡升级。G3/G4完成，不重新开工；外线原交接树不清理。

目录互不包含，根本项目也不同；没有“两个harness同时编辑同一个文件”的安排。主仓既有dirty只读记录/核SHA，不复制到新基线，不reset/clean。短路径避免之前长worker路径导致prepush在pytest前拒绝；发卡不新增长度资格/目录签收。

## 3. 不等待的接口约定

| 线 | 输入/可复用接口 | 完成时输出给MAIN | MAIN集中接线 |
|---|---|---|---|
| CWP | 当前writer_policy退休exit78；现hermetic/source质量反例 | stdlib六薄stub、迁移helper、retirement_map、准确超白名单caller表 | 工程清单/当前指导/指纹如确有依赖，同次修；保留source层责任 |
| SID | wire1.0/adapter1.3.0、exact/latest/fetch、ProviderAcquisitionBudget与冻CWP JsonCommandAdapter | browserless正常CLI/身份+公告共享budget、依赖/HTTP出口表、真实离线计量 | CWP当前消费/无cache输入；继续G2-12 ensure/入库/并发复用 |
| RF | G3既定runtime闭包/旧installer API；三真实安装只读diff | --file/--plan/--json；plan/result各/1、差异/partial事实；3×8定点清单 | RF并线/精确CI后仅24差异更新home、保护config/output并核真实入口 |

SourceRef/SourceExport v2、NarrativeRef、FF intent/ET TXT、原语言/模型配置不变。外线只用冻结已提交依赖，可以现在全部开工；不把MAIN未提交代码复制进测试。provider/installer/旧工程壳三个输出可分开接收，不构造互相等待环。

## 4. 各线自己的PWF与共同交接字段

单一计划目录分别为 `<各工作树>/.planning/g5-cwp-checks|g5-sid-runtime|g5-rf-install/`，即实际ID的单个目录。每个shell单独设 `PLAN_ID=<本ID>`、`PWF_PLAN_ROOT=<本工作树>`，resolver返回该目录。不要在原CWP总计划创建自己的task_plan，也不要为hook补第二份docs镜像。

每卡写自己的三PWF、HANDOFF/handoff.json/main_wiring和指定专用表；共享导航/收据由MAIN更新。handoff schema统一`g5-handoff/1`，必需fields见每卡；其中所有路径相对自身repo或明确absolute，不能混淆其它卡项目。只交实际实现commit与可解析branch/tip；不循环生成自指SHA、人工签字或expiry。metadata/source/hash/usage是事实，测试绿色不是新的人工许可。

交接须分别写：实际行为GREEN；真实literal CLI的离线GREEN/具体HTTP替换边界；live/paid/not_run；原仓dirty保护与临时恢复；MAIN未接部分。遇到超白名单caller，提供准确文件/符号/修改建议及可复现反例，不代MAIN写文件，也不把它作人工阻塞。

## 5. 审查与测试频率

开发TDD只跑实际红灯所属责任。每卡完工一个集中unit+集成/真实CLI离线节点；MAIN接收后只补公共接线/当前合同、大节点验收和正常精确代码CI。没有逐函数/逐文件/每小节点人工复核，数字coverage/固定pass/来源体量不成为门。

每个测试资料在各自新短owned根，先建父目录/记录初态，结束等进程/HTTP/DB退出后finally核abs路径/归属删除自身新资料，恢复absent。不完整恢复备份，不在生产造坏资料；原件删除0，付费/真实外网0，用户LLM配置不变。

正常commit，可推自己的codex分支；不代MAIN合实际执行分支/部署home/改生产。prepush报错先定位真实依赖/路径，不能skip hook或加更多长测试。MAIN先验收可独立交付，再按相关公共caller一次接入；G2最高优先级保持，R2→R3→R4→R5不被新卡替换。

## 6. MAIN当前单一继续点

目标paused；等待用户明确恢复时，MAIN继续完整G2-12/FF/公共接线，不写本批外线owned范围。用户报告各卡done时按精确实际Git/PWF接收并正常并线/推远端；无需等待其它两卡done。本次制卡结束即可交付三个harness。
