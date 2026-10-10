# M3-JSON：官方多公司 JSON 原文、公司投影与公开读取

## 开工与责任

唯一执行PWF：工作树 .planning/m3-official-json-20261010/。启动时设置 PWF_PLAN_ROOT 为本卡工作树绝对路径、PLAN_ID=m3-official-json-20261010。先把已有 docs/plans/cross-market-rf-e2e-2026-10-08/phase6/m3_root_implementation_2026-10-10/W02/ 的三文件作为历史 seed 复制到自己的新 .planning 目录；只补缺失文件，不覆盖已存在计划。此后只维护这个已选PWF，旧 W02 目录只读保留，不回落根计划。


可以立即开工。只在 C:/Users/郑曾波/.codex/worktrees/m3-official-json-20261010/company-wiki 工作，branch codex/m3-official-json-20261010，base 3c791e3c2a16c12627cc25d0bd8681cc9458e48b。原内置 agent 已 terminal errored，实查没有源码更改；只留下 docs/plans/cross-market-rf-e2e-2026-10-08/phase6/m3_root_implementation_2026-10-10/W02/ 的计划，接管并保留它，不清理全工作树。

本卡是较大来源系统改造：通用结构 parser、显式 raw subject、公司投影、公共 import/project/read/export、恢复与兼容。目标是“一份真实原页，多家公司各自准确消费”，不是把分页 JSON 拼成 TXT。

## 必读依据（绝对主文档根）

C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/

- phase6/m3_parallel_handoff_2026-10-10/INTERFACES.md、HANDOFF_TEMPLATE.md、handoff.schema.json。
- phase6/m3_root_remediation_2026-10-09/work_packages/W02.md 与 INTERFACES.md；不要写冻结包。
- phase6/m3_source_research_2026-10-09/official_json_source_root/DATA_CONTRACT.md、JSON_EVIDENCE_INDEX.json。完整阅读，不能只读摘要。两 SHA 分别 2d80afeeac0946f91e18dccc6008eab734dcb1d727aac6f2dbe2870e7b4f08b3 / 4969a5239e15b71f2e8d83e3107dd7a9f80ab78b9673b710a2158906b35285fc。
- 工作树 AGENTS.md、现有 source_contract strict versions、writer/importer/reader；结构查询先 CodeGraph，指向主项目索引，已定位文件再读实际源码。

## 已确认的反例

封存 run：C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/m3-20261009T184946-cn-688012。86 页共668749 bytes、257条记录，目标公司24条，原页不是单一公司。raw 页只读。

- 原 JSON importer 把 JSON 按单电话会 content 校验，拒绝这些合法分页页；只修 admission 仍会卡在单 issuer 保存和 AUTO transcript 路由。
- latest-form-01 的 /datas/0/records/2 是2508409清溢，2508385中微真正位于 latest-form-18 的同 pointer。此错误是必须保留的定位反例。
- precollect-form-10 的 /datas/0/records/1、ID36395 的 answer 非空；累计约800个反应台不能被改为年度销量。回答人和首次公开时间未知不能补造。

## 排他写集

按 INTERFACES.md 的 M3-JSON 集合修改。禁止改 acquisition_*、download_budget、bounded_http、source_operation、source_catalog/cli.py、FF/RF、所有 automation 公共文件及生产配置。AUTO 接线交 MAIN 具体 DTO+最小 patch/红测，不自行另起批次入口或队列。普通业务筛选 W03 后续另做，不在本卡接管其文件。

## 施工顺序

1. 读取旧 W02 PWF，记录实际 worktree/HEAD/status、初始原件/config/测试根 SHA。先写完整 consumer map 与接口例，更新自己的 PWF；不等待用户小节点签收。
2. TDD 通用 JSON 结构 parser：RFC6901 pointer、token 原 byte range/hash 与解码字符串 locator 分开；严格 UTF-8/escape/surrogate、duplicate keys、finite 数字、深度/节点/字节/时间限额。注册声明 layout adapter，不能按公司名、ticker、页号硬编码。
3. TDD 新 raw subject/manifest、projection DTO/版本：single_issuer、multi_issuer_event、unattributed 都不得伪造 owner。共享位置由现存 storage 层在配置根内决定；未知归属允许保存原件但不成为目标公司确认的业务证据。SourceRef2.0继续绑定整页 raw，projection hash另有其含义。
4. 实现既有 official_source_cli import 的新明确 request version，project/read/export；母页改 bytes、pointer错、跨 issuer、错误版本/失配 proof 拒绝业务消费而保留 raw。不能只交 pure parser。
5. Q/A及非连续语义组：问题不能当公司确认、主持致辞不冒管理层回答，unknown actor保持unknown；不同字段时间含义和historical as-of不混淆。原页complete、分页complete、issuer complete分别报告。
6. 恢复、重复 import、多issuer projection、同SHA复用、缺页/ID冲突/total变化与空间失败控制。复用现有 staging/journal/AUTO/outbox，不增加DB、许可档或第二任务库。
7. 输出 MAIN 共享接线包（AUTO新类别/route/replay/generation、请求字段兼容和测试）。提交自己授权文件，正常 branch push，记录精确CI；不合主线、不安装技能。

## 自己的测试包

新建本卡专属 test_m3_official_json*，目标覆盖矩阵：

| 层 | 必须证明 |
|---|---|
| 单元/合同 | pointer、raw slice/hash、中文/emoji/escapes、重复键/NaN/孤surrogate/限额；两声明布局和第二issuer；旧电话会content合同不变 |
| 集成 | 公共 import→原文 exact read→两issuer project→versioned export→span replay；一份raw两投影，错误issuer/篡改母页拒绝 |
| 恢复/预算 | 进程失去响应后恢复、重复导入/投影幂等、缺页/冲突诚实partial；磁盘预算失败不发布半个结果 |
| 冻结真实页 | 86页SHA不变、257记录定位、目标24条及36395答复，旧错误页不能通过；不能把其它公司/未答问题当公司答复 |
| 兼容 | 旧 SourceRef2.0/manifest1/strict export2.0、TXT/FMP电话会正常；未知layout留 raw并typed unsupported |

责任测试创建后运行：python -X utf8 -B -m pytest -q tests/unit/test_m3_official_json*.py tests/contract/test_m3_official_json*.py tests/integration/test_m3_official_json*.py。Windows shell不展开时先用 pytest 目录加专属标记/明确文件列表，保存实际argv；不存在的文件和0 collected不算产品RED。

真实公共 CLI 依 DATA_CONTRACT §6 参数运行，config/catalog/AUTO/work 全在独占 TEMP。只需要最小四个冻结页副本，其他82页只读验证；禁止复制整库。断外网、使用现有loopback model fixture仅做接线协议测试，token/付费0。TEMP初始不含的下载/派生文件测试结束删除，初始文件逐SHA恢复。

## 接收与交接

保存原生 RED、GREEN、changed Ruff/实际受改类型检查和公共链 stdout/stderr/exit；不要把新增hook变成每个小节点全套重测。最终一个工程节点完成本卡测试，MAIN另做共享AUTO+三仓真实大节点。

HANDOFF 路径为自己的 .planning/m3-official-json-20261010/ 下 HANDOFF.md、handoff.json、INTERFACE_CHANGE.md、raw测试日志。采用同目录统一 schema，分别列 source_public_api 和 main_auto_integration 状态；后者待MAIN时不能把 full_feature 标complete。不调用供应商、不增模型费、不跑收入预测、不改原件/生产配置、不越界投资研究。未知server companyfilter/时区/历史答复时刻单列，不猜参数发公网。
