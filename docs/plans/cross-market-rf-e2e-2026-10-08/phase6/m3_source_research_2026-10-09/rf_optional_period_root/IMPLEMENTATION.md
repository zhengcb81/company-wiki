# RF可选期次：请求约束与已解析期次分层

状态：开始隔离TDD；基线RF43635e51；不改三家封存executor。CN-fetch纯调用与真实两年H1的原生链已证明：请求省略可选fiscal_period时，FF/CWP已唯一解析H1并实读原件，RF却把None当“只能接受来源None”错误拒绝。不是用户没填必填项。

## 接口与职责

- FF/CWP负责根据公司、document_kind、年份、as-of与可选期次解析候选，歧义必须在解析层返回，不能RF自己挑一个H1或H2。
- RF只把显式fiscal_period当精确约束；省略/None表示不额外限制唯一候选的已解析期次，记录实际值而不改写源metadata。年度既有唯一FY/None兼容不变，不能接Q/H年报；非年度不默认H1/Q1，也不把来源unknown补成请求值。
- 交接字段仍须是None或非空字符串；不能以省略请求为理由接收bool/list/dict等多值或畸形期次。显式H1/H2/Qn/FY不匹配保持现具名fiscal_period_mismatch；错误公司/类型/年份/as-of/hash、location-free API检查保持现责任，不新增许可、重扫目录或手工签收。

## 施工顺序与写集

1. MAIN复用clean且已入main的TEMP/rf-fresh-dag-20261009，从43635e51建codex/m3-optional-period-20261009；记录RF主线owner三个assurance日志与output，不触碰；先仅现tests/test_source_preparation.py增加省略/显式None→唯一H1/H2与Q2、有resolved期次的非财务source正例，明确H1→H2/Q1→Q2/年报Q1、错年错kind与畸形字段负例。RED必须是产品约束错，不是mock字段缺失或测试环境错。
2. scripts/source_preparation.py依上述可选语义根修，不按公司/年份特判，不给FF/CWP另一套period分类表。年度旧兼容维持；正式sources/source_manifest仍保留实际源期次、未知与公开日。
3. 集中RF源准备/complete-result/deadline/三仓真实CLI责任tests，不放进commit长流程。真实CN FY25/26 H1各一次省略期次reuse_only，通过本隔离RF→当前FF→CWP只读原件；不下载/收费/改生产metadata；记录request/capture/SourceRef/SHA/download0与H1结果，测试output仅自有TEMP且恢复。
4. 正常sourcecommit/push，保持precommit快静态/已有prepush边界，不旁路hook。集中大节点核对后并main/精确CI；定点同步单一runtime文件到实际RF技能安装物理根，先旧SHA/保留配置与output，原executor不改，下一attempt使用新版本。

## 验收

两实际半年度同SHA、真实零GET/模型/费用且省略请求可读；原显式错误期次/年份/类型/损坏字节负控仍拒绝，SourceCapture实际H1记录而不凭请求制造；owner WIP SHA、production config、原件、封存execution与原64矩阵不漂移。这个工程节点不表示两份H1摘要截断或研究假设已接受。

记录实际UTC：2026-10-09T21:21:10.933368+00:00

## 2026-10-09 21:34 UTC：发布与定点安装完成

main0c248d9a正常push：194PASS/29.47秒，精确quality CI37993474331 SUCCESS/42秒。CN-process封存后同步 source_preparation.py 到.agents/.codex两物理根，.claude为前者junction；539其他文件SHA不变。第一次写前断言因候选CRLF hash与主线LF hash不同拒绝、零修改，已核验完整LF字节等于主线Gitblob后采用canonical SHA839af5a1…；不是放宽内容验真。见installed-source-preparation.json/main-ci.json。原M3两旧误拒不重写，当前真实两H1复用证明另列，不替代新研究。
