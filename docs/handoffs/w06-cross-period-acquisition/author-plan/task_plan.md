# ROOT：缺期资料获取与已验入库事实的单一责任层

PLAN_ID=w06-cross-period-acquisition；owner=ROOT。起点CWP master057f2f8d（代码与8862372f相同）、FF main08ec85b、ET c91f5f54。保持原件/生产配置/密钥/其他owner WIP；无真实HTTP/LLM费用。先完成本文实施细则和行为RED，再改代码。

## 已有证据与目标

W06矩阵41项19PASS/21FAIL/1PARTIAL，132.54秒。九份三市场2024财报经真实CWP ensure/CanonicalSourceWriter入库；同期间复用正确，缺2025/2026时adapter未启动。最小8秒复现和完整metadata见母W06 evidence/root-ff-matrix-acceptance/fix/cross-period-repro.json、offline-evidence.zip。无手填assertion；actual steady assertion/source_fact_patch为NULL。旧HOME、未验sidecar、fixture同SHA碰撞均不是这个缺陷的证明。

已确认路径：resolver正确排除旧期 → local_reconcile重新纳入同实体/同kind全部来源 → 仅从source-fact assertion取事实、未使用已验canonical acquisition → NULL patch触local_metadata_incomplete →异常分支targeted=True → blocks_download=True → coordinator MISSING，供应商未调用。多数ET场景是primary前置失败，不是ET内部失败。

目标是一次入库验证后由所属来源层负责事实资格，消费者按SourceRef使用；可信非目标旧期资料不阻断当前缺期下载。保留目标来源真实SHA/类型/期间/as-of、预算、原件不可变及恢复责任。不能为fixture制造assertion、按公司/年份特判、删失败向量或把失败标skip。

## 写集与接口

ROOT新独立工作树 cwp-acquisition-scope-root，从最新master创建；作者W06工具目录与PWF不改。允许CWP来源目录内的canonical入库事实读取/相关性/local_reconcile/ensure诊断及对应测试。FF生产仅在真实证据证明上游诊断丢失时定点修消费映射；ET/Dayu/IQS/StockWiki零写。

既有 SourceRef/SourceExport v2字段、原件SHA和对象身份保持。复用既有acquisition request/candidate/receipt与验证函数，不创建第二事实库、许可文件、私有根、签收、epoch/canary或人工放行。

纯来源事实解析须区分：可信canonical capture / 既有已验source-fact evidence / 仅scan声明 / 冲突或缺失。canonical声明必须绑定现有版本hash/size/MIME，并内部一致地表达request/candidate/receipt身份、类型、期次和发表日；只看文件名、存在一个acquisition字典或capture_ready标签不够。原验证函数可复用，不能复制散落的身份正则。真实原文回开仍由SourceVersionReader负责。

## 三个大节点

### A：根因与行为RED

- [x] 封存当前真实8秒复现、41矩阵和actual NULL patch；独立只读定位共因。
- [ ] 独立根因报告收尾，选择最小共用责任层方案；实现前记录具体函数写集。
- [ ] 公共真实writer→prepare/ensure反例：CN/HK/US年度旧2024→新2025；同年Q2→Q3；已验来源没有人工source-fact assertion也应按原入库事实识别非目标。

正控：相同期间零下载；冷启动一次下载；新期下载后再次零下载；latest_as_of仍按已有provider元数据规则；已存在目标坏SHA/错误类型/身份冲突与未知publication如实拒绝，不转为重复下载。未验scan侧车不得因伪造capture/acquisition标签成为可信scope。测试全用独立tmp和真实小PDF/HTML/TXT，没有生产配置。

### B：统一实现与一次集中工程节点

- [ ] 复用 canonical_writer.py 的已验request/candidate/receipt，在一个共用纯边界解析已验来源事实；避免通过增加人工assertion补洞。
- [ ] local_reconcile.py 先判断可信scope相关性，非目标不进入目标修复/阻断；未知声明仍走原文事实修复。相关来源的事实资格沿既有责任层复用，不重新解析无关旧期资料。
- [ ] AcquisitionCoordinator保持发现/下载/入库预算和锁；ensure与FF诊断保留具体失败层与原因，不能只有笼统not_found或推断供应商调用。
- [ ] RED转绿后一次集中受影响单元/集成；覆盖退休/恢复、篡改、schema兼容、scope冲突与真实byte读取。只为具体剩余风险扩测，不能添加逐小节点审查。

### C：原矩阵回放与正常发布

- [ ] W06-FF工具通过非作者范围验收后，用原41case/原期望/同180s批次上限对新ROOT代码回放；报告实际模块路径/HEAD/SHA和新attempt。不得覆盖旧19/21/1失败。
- [ ] primary可用后，确认ET真实supervisor→worker HTTP测试seam→FF→CWP原语言TXT入库→第二次零下载→fresh SourceRef实读。错quarter/symbol、cutoff/unknown publication、坏SHA/MIME、402、费用未知和已调用失败均独立分类。
- [ ] 一次大节点非作者复核；正常commit/main并线/push、精确SHA远端CI、必要的安装定点同步。不把离线合同绿当真实外网/经济模型认证。
- [ ] 更新母W06当前状态，关闭本包后返回W04→G2→G4→G5。

## 恢复与空间

只创建unique自有scratch，基线不存在就恢复不存在，基线已有文件/空目录均保留。最终关闭全部SQLite/子进程并恢复配置、raw及输出目录。原始失败证据用小JSON/日志或压缩bundle保存，禁止完整数据湖副本和备份恢复演练。secret只允许stat，不读/hash/继承；测试环境用合成HOME/TEMP/假凭证，网络拒绝。

Next Step：接收独立根因报告，写固定行为RED并冻结失败，然后实施共用scope责任层。整个母PWF未完成。

## 作者实施细则（2026-10-11；隔离 TREE；实现前决定）

1. 新 canonical_scope.py 是本来源层事实/相关性边界：SourceScope、ScopeRelation（MATCH/NOT_RELEVANT/UNKNOWN）、qualified_source_scope、scope_relatedness；合法 steady source-facts 绑定 document/source/SHA，正常 canonical provider 入库与原文 DEI 的 evidence locator 分开。仅 scan acquisition JSON 永不资格升级。
2. writer 验过 request/candidate/receipt/实际字节后，在现有有限单组 registration 的 coalesced 事务内通过内部 on_registered 回调写既有 source-facts projection；同连接构建，提交后才 query_ref。_prepare_source_fact_write 增同连接读 port。provider 声明不得覆盖现有相反事实；重入/物理去重不重复原件或改首份 sidecar。无新表、schema、许可、手填 assertion。
3. 历史成功 acquisition journal 仅资格升级 request_id 哈希绑定的显式 scope；重算 attempt_id/request_id，版本 SHA/provider/accession/URL/candidate ID 一致。一个 local 操作最多读一次有界 journal，不升级旧 journal 未绑定的 publication/title/candidate period。无可靠旧记录为 UNKNOWN。旧 path 不是可信条件，根迁移仍按版本定位。
4. local_reconcile 在源责任层判断 relevance 后，可信非目标不调用字节/事实恢复、不重查 identity master、不恢复 retired。目标继续完整 SHA/MIME/as-of/status 和 SEC 实际 DEI。UNKNOWN 不视为可下载的空湖；给具体诊断。已有正常 source-facts 的非 SEC 目标身份按已验事实使用，不读另一身份库。
5. AcquisitionResult.local_preparation 为有限 pathless 诊断（status/reason/blocks_download/具名原因）；操作 DTO 同步可选字段。缺期 not_found 与本地 blocked/unavailable 区分；预算的 provider_started=false 沿既有 observation 保持，不推断已调用。
6. TDD A 文件 tests/contract/test_canonical_acquisition_scope.py：public service cold→same期reuse0→跨年度三市场、同年Q2→Q3、半年度旧2024→2025，各真实小 PDF/独立湖；旧原件 SHA 保持、新期再次reuse0。先跑前五行为 RED（不是缺模块假 RED）。然后加 scope unit 与 scan 假来源、历史 request 改写、目标篡改、未知 publication、retired、原子失败与 dedup 冲突控制。
7. B 一次集中执行本新增+canonical writer+local relevance/discovery+operation v2+scope responsibility+latest acquisition+acquisition usage 相关测试与 lint；发现具体失败才补范围，不跑3314或41matrix/LLM。C 留 ROOT 原41矩阵、FF消费接口与非作者最终验收。

环境：最小子进程 env，假 HOME/TEMP，dotenv disabled，pytest 网络 guard；unique 短 scratch 全合成并结束恢复不存在。已发现默认 sandbox 外部 git status 异常，escalated 同命令正常；一次测试路径不存在已更正，是探索输入错误不是代码缺陷。原件、配置、密钥、母 PWF、FF/ET/Dayu/IQS/Port工具均不写。

Next Step：运行 public writer 行为 RED 并封存，然后按本决定实现。无 commit/install/merge/push；最终 freeze SHA+handoff 后 STOP ROOT。

## 节点状态更新
A已完成（原根因+真实行为RED+实际unit/control RED）；B已完成（common source qualification、writer自动facts、target实读、诊断+191PASS/lint）。C仍待ROOT矩阵与非作者总验收/正常发布。原复选事项由此当前记录覆盖，不能把C或母计划宣称完成。
## B 作者实现已完成；C 留 ROOT

- 正式 public-behavior-red：6 FAIL / 1 PASS，3.697s。跨年度三市场、HK Q2→Q3/半年期均先实际入库/同期期复用通过，然后新期 missing；具体 local blocker 投影误 not_found。
- control-red：3 FAIL，1.894s，固定 unverified authority 误 MATCH、公共 writer HTML伪PDF未拒绝、失败重采提前 reactivation。
- 最终 final-affected：191 PASS，50.947s；source unit、public synthetic integration、CLI usage 集成、既有 SEC DEI/预算/锁/原子恢复/retired/截点合同集中绿。ruff --no-cache 与 git diff --check 绿。
- 12 产品文件（10 source 模块+2新增tests）已 product-freeze.json SHA封存，最后只读 lint/diff 前后保持。未 commit/install/merge/push。
- 各次 unique cs-* scratch 均恢复不存在；原件全在独立合成 tmp，不触生产资料/配置/密钥，真实 HTTP/LLM/费用0。
- 前3次测试接线错误保留记录、不作产品 RED；fresh catalog历史负控与 unknown date拒绝语义调整有据，旧失败证据未覆盖。一次 PowerShell CRLF anchor 缺失在写前中止，无产品改动，已按文件换行更正。

Next Step（ROOT）：按本 handoff/freeze核对12文件并独立接受，再用原41case/原期望/原180s上限统一回放。验证 FF处理新的 local_preparation blocked/unavailable，ET supervisorTXT真实离线 seam、fresh SourceRef实读、第二次零下载。通过后 ROOT集中提交/并线/push/安装定点同步、更新母12PWF；本作者 STOP，不扩测3314/不跑LLM。
