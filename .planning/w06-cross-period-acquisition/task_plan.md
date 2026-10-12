# ROOT：缺期资料获取与已验入库事实的单一责任层

PLAN_ID=w06-cross-period-acquisition；owner=ROOT。起点CWP mastere2e19ea2（生产来源代码与8862372f相同）、FF main08ec85b、ET c91f5f54。保持原件/生产配置/密钥/其他owner WIP；无真实HTTP/LLM费用。先完成本文实施细则和行为RED，再改代码。

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
- [x] 独立根因报告已冻结于 root-cause-review/；新工区/函数写集已授权，来源资格设计与真实RED由专属作者执行。
- [x] 公共writer行为RED（6FAIL/1正控）已留证；CN/HK/US年度跨期、HK季度和半年度跨期、同期间复用与未知声明均覆盖。

正控：相同期间零下载；冷启动一次下载；新期下载后再次零下载；latest_as_of仍按已有provider元数据规则；已存在目标坏SHA/错误类型/身份冲突与未知publication如实拒绝，不转为重复下载。未验scan侧车不得因伪造capture/acquisition标签成为可信scope。测试全用独立tmp和真实小PDF/HTML/TXT，没有生产配置。

### B：统一实现与一次集中工程节点

- [x] canonical_writer统一绑定既有request/candidate/receipt并自动保存已验事实；canonical_scope区分MATCH/NOT_RELEVANT/UNKNOWN，没有第二事实库或人工许可。
- [x] local_reconcile在旧原文解析、身份查询和retired恢复前排除可信非目标；历史提升只认绑定真实成功journal，不提升未知发表日或scan标签。
- [x] 原预算/锁保留，来源注册/事实/reactivation同事务；复用先SourceReader验真实SHA再写成功journal；pathless local_preparation保留具体原因。
- [x] 一次191PASS/50.947秒；非作者13PASS/5.13秒与SEC原生加强1PASS/1.67秒。12文件及43作者证据SHA不变，独立scratch全部恢复。

### C：原矩阵回放与正常发布

- [x] W06-FF工具通过非作者范围验收后，用原41case/原期望/同180s批次上限对新ROOT代码回放；报告实际模块路径/HEAD/SHA和新attempt。不得覆盖旧19/21/1失败。
- [x] primary可用后，确认ET真实supervisor→worker HTTP测试seam→FF→CWP原语言TXT入库→第二次零下载→fresh SourceRef实读。错quarter/symbol、cutoff/unknown publication、坏SHA/MIME、402、费用未知和已调用失败均独立分类。
- [x] 一次大节点非作者复核；正常commit/main并线/push、精确SHA远端CI、必要的安装定点同步。不把离线合同绿当真实外网/经济模型认证。
- [x] 更新母W06当前状态，关闭本包后返回W04→G2→G4→G5。

## 恢复与空间

只创建unique自有scratch，基线不存在就恢复不存在，基线已有文件/空目录均保留。最终关闭全部SQLite/子进程并恢复配置、raw及输出目录。原始失败证据用小JSON/日志或压缩bundle保存，禁止完整数据湖副本和备份恢复演练。secret只允许stat，不读/hash/继承；测试环境用合成HOME/TEMP/假凭证，网络拒绝。

Next Step：本包接收/FF及ET并线发布/安装完成；回母W04共因修复→G2→G4→G5。W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，FF精确CI38170433893状态成功；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。

## 2026-10-11 W07-FF-PERF ROOT 最终接收

W07-FF-PERF已完成ROOT接收：原41场景全PASS/99.9624s、零oracle findings、26最终原文证明，原30/180秒上限与case/期望不减；225集中绿、ET53绿。FF main/origin/main64b4d29、ET main/origin/main d0ac42c6已正常发布，FF精确CI38170433893状态成功；ET没有配置workflow。两运行文件×两物理FF技能副本同步、各5实际安装后边界绿；三仓配置体检绿，非选文件元数据和原WIP保持。Audit已接收安装；RF工具已发布8dc26710/精确CI成功，整卡仍缺五组组合覆盖。W04已本地并线7a0b702a但正常push18FAIL，远端仍5c07f47c；ROOT后续W04共因→G2→G4→G5。目标工具当前paused，本次仅完成用户授权的接收，0付费调用。

共因修复：Windows长路径重复编译/重复准备与proof饥饿由作者统一解决；ROOT补独占attempt缓存、proof失败不可覆盖/完整worker证明、子进程reap、异常清理和seed完整序列。ROOT自己的逻辑别名数过约束有反例修复；首轮28/13记录保持，最终原41重跑全绿。两轮原始证据仅490060-byte ZIP，隔离重放oracle零发现、自动恢复。长矩阵手动大节点；轻量测试走同一正常push/CI，未新增人工门禁。

证据入口：company-wiki/.planning/w07-ff-perf-reception/publication.json、acceptance.json、offline-evidence.zip、replay_evidence.py。工程绿不认证真实供应商可达、来源真值或研究质量。预算母账保持413778tokens/334463µUSD+2764FXhold，累计$20/200万tokens。
