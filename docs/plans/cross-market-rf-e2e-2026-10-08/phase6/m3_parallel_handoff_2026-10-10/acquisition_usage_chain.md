# M3-USAGE：三仓下载用量与原因完整传递

## 可以立即接管

唯一总执行PWF在本卡 CWP工作树 .planning/m3-acquisition-usage-20261010/；其FF/RF子仓同名 .planning 只记录子仓步骤。启动/切仓时将 PWF_PLAN_ROOT 指向对应卡内工作树绝对路径，PLAN_ID=m3-acquisition-usage-20261010。CWP三文件从旧 W06 docs 目录复制为 seed，只补缺失；FF/RF补自己的三文件，不碰已有其他计划。随后只维护这些选中PWF，旧 W06 docs记录只读保留。


这是一张大卡，由一个 harness 负责三仓顺序链。工作目录分别：

- C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/company-wiki，base 3c791e3c2a16c12627cc25d0bd8681cc9458e48b。
- C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/filing-fetch，base 41ba0150c9c634f6021c9346744cada391ec2c4c。
- C:/Users/郑曾波/.codex/worktrees/m3-acquisition-usage-20261010/revenue-forecast，base 0c248d9a07a2dd7a2c756946d88507479d5e9d15。

三仓 branch 都是 codex/m3-acquisition-usage-20261010。前内置 agent terminal errored，无源码修改；CWP工作树只有自己 W06 前期PWF，FF/RF clean。复用这些工作树，不再创建完整克隆。主 RF assurance/output 和主 FF FMP key 的未提交内容不是本线的，禁止改、搬或提交。

## 任务目的与必读

让成功、失败、复用都能沿 CWP→FF→RF 看见真实已观察的下载开销与业务结果。不能“原件有8MB，就认为网络只用了8MB”；metadata请求、压缩、失败尝试和未知费用都要诚实记录。

主文档根 C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/。必读本目录 INTERFACES.md、HANDOFF_TEMPLATE.md、handoff.schema.json；phase6/m3_root_remediation_2026-10-09/work_packages/W06.md；现有 W06 PWF；各工作树现有维护规范及 current producer/client contracts。先 CodeGraph consumer map，再读定位源码。Dayu 是纯外部项目，零代码修改。

## 排他边界

按 INTERFACES.md M3-USAGE 的三仓文件列表。禁止碰 JSON/schema/metadata/canonicalwriter、AUTO模型和存储、RF drivers/contracts/schema_compatibility/revenue_report、assurance/output、installed skills、所有 key/config/raw。source_catalog/cli.py 总入口留MAIN；只交 source_operation 的DTO及CLI最小接线patch，不与 JSON 线争公共入口。

本线测试只用专属 test_m3_acquisition_usage* 和已列现有失败用量责任测试；不编辑其他卡测试/公共 model fixture。不增加身份验证、格式白名单、授权receipt/TTL、人审或另一个账本。

## 开始前必须固定的合同

现 acquisition_usage 1.0 是严格 response_bytes + cost_usd，并不支持直接加入 fee=null/request count。现 acquisition-failure/1 是 operation 范围。先发 INTERFACE_CHANGE.md：实际字段、完整/下界/未知状态、success/failure/reuse样例、原版本兼容、CWP→FF→RF消费者路径。

新增观察可用明确 observation sibling 或显式新版本；不能让旧字段 silently 变义。response_bytes=已观察响应正文wire bytes，不含TCP/TLS/headers，不等于解压entity/原件大小。费用cap0、初始counter0、provider内部无回执都不证明最终费用0。遇到 post-send timeout 保留 unknown 或下界；旧7未知模型+1旧FF未知采集不回填。

## 实施步骤

1. 自己 PWF 记录各repo HEAD/status、精确 write set、consumer map 与旧错误通道接受证据；旧 limited causes 已修，不重做整套错误系统。
2. 先构造本机 bounded loopback provider 的 RED：metadata GET两次、body GET一次，gzip wire小于解压entity；当前success不能完整投影usage。既有预算负责累积，不能把最后一次adapter invocation当全operation。
3. CWP producer 产生同一operation的 success/failure/reuse安全DTO；已知HTTPstatus/content-type/content-encoding有限投影，不泄漏任意headers、URLquery、路径、credential或stderr。未知值明确null/unknown。预算/清理异常不能抹掉原primary原因与usage。
4. CWP GREEN后 FF 保真投影 source_candidate/缺失/失败及原businessstatus；RF client→source_preparation继续传递；不重新校验一套MIME/公司身份，不从磁盘补“网络账”。
5. 用实际子进程 CWP CLI→FF CLI→RF public client/preparation 跑完整离线链；生产provider映射换为TEMP loopback配置，禁止隐式dotenv读取。CLI总入口的 MAIN patch可应用在自己的专属临时集成副本做实验，但不混入本线commit，不改另一工作树。
6. 第二市场/格式、reuse零GET、pre-launch失败、mid-body截断/timeout、未知费用、metadata错误、cleanup secondary error逐控制。恢复TEMP到初始状态。
7. 按CWP→FF→RF次序分别正常commit/push自己的分支并核exactCI；提供 runtime文件SHA闭包供MAIN定点安装，不自己复制技能整仓/合主线。

## 测试包与接受标准

| 类别 | 必测 |
|---|---|
| Unit | 既有usage严格兼容、有限新DTO、null与0不同、不同operation/call不能混、header无secret/path |
| Integration | 多metadata+body累计实际wire，success/失败同语义、FF/RF保真，不取raw bytes推测 |
| Public E2E | CWP CLI→FF CLI→RF client/preparation，至少两不同source/市场控制；stdout/argv/exit全部保存 |
| Recovery | reuse0新GET、不覆盖旧unknown；post-send timeout不标免费；清理失败保留primary cause；旧失败receipt能读 |

具体命令按实际runner：CWP python -X utf8 -B -m pytest -q 本卡明确unit/integration文件；FF python -X utf8 -B -m unittest discover -s tests -p test_failure_usage_continuity.py，再跑新test_m3_acquisition_usage*.py；RF现有source_failure_observations和新增专属文件。注意unittest -p和pytest都需保存实际匹配到的文件/collected，不存在文件不是产品RED。

0公网provider/模型/费用；loopback必须只允许自身地址，跨仓子进程用实际working tree/PYTHONPATH，不能误调已安装技能。scratch64MiB/persistent32MiB/final2MiB或既有更小界；原件小夹具、测试结束初始目录逐SHA恢复，额外原件全部清除。大日常回归不塞commit hook，只保留已有normal hooks和受改责任测试/一次大联调。

## 交接

自己的 CWP工作树 .planning/m3-acquisition-usage-20261010/ 下保存 HANDOFF.md、handoff.json、INTERFACE_CHANGE.md、RED/GREEN原始日志和 restore receipt；FF/RF自己独立 .planning/m3-acquisition-usage-20261010 记录，不写它们其他 PWF。

报告每仓完整base/head/branch、changedfiles与runtimeSHA、公共真实样例、实际观测计数及unknown、费用0的证据、MAIN总CLI patch/安装列表。工程责任绿不恢复115B旧SEC版本差异/旧收费账；不宣称新真实SEC/ET公网大节点已运行。全链最终由 MAIN 集成并在真实公司大节点核对。
