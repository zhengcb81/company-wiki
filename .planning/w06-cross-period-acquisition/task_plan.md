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

Next Step：专属作者在 cwp-acquisition-scope-root 写公共writer行为RED并冻结，再实施共用scope责任层；ROOT接收后重放原矩阵。整个母PWF未完成。
