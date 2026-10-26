# W19 ROOT接收与共因修复

状态：IN_PROGRESS，2026-10-26。作者CWP `22ab7a41`（产品`43995453`），FF `d396fe7`，两工区干净；ROOT只读接收，不把作者PASS代替当前主线集成通过。卡面与原始证据保留。

## 当前进度与用户分层要求

PDF-C2兼容窄修4c8b4642已发布，精确CI40291031425成功，不再等待。W19仍在ROOT集成，未签收/并线；FF自有短工区`cw-ff19`已接收作者分支但未提交，作者目录不变。

数表服务已改用真实SourceVersionReader引用、canonical writer字节入口、无HTTP的provider协议和统一repository查询；不读取SQL/旁车/暂存路径。PDF既有owner无需重写；在六个AUTO消费者新增针对直接SDK/私有配置绕过的AST回归及允许/禁止片段自测，配合可替换backend、共享预算与真实source/replay的既有行为测试。FF新增独立薄客户端边界测试，不能import HTTP/SQLite/CWP内部实现。测试不是新审批链。

首8项真实RED→GREEN；分层/PDF54项通过、W19+旧writer+分层158项90.70秒通过、FF24项8.52秒通过。之后独审发现A→B→A回退、同秒排序和PIT未来覆盖3个反例，再先RED修在repository：同一catalog中只在内容转换时追加小型版本观察，不复制原件/数值行，重复未变刷新不增观察；schema1.4通过单DDL链兼容1.3并回填已知capture，不捏造旧观察顺序。历史查询仅计当时可知期间，不能保存过去覆盖声明时返回`historical_coverage_unverifiable`/partial，不借后来范围。新27项通过；正常CI已纳入精简公共回归（从同一测试实现引用，未复制oracle），42项34.89秒通过；Linux388源码mypy和Ruff通过。计数有重叠，不能相加成单次总数。

仍待：当前最终代码独审（前一审查agent在完成3反例后capacity失败，由另一独立agent续审）；所有改动完成后一次集中相关回归；官方6项对照、FF真实薄传输→CWP离线三表→直接SourceRef→0HTTP复用/空间/恢复；安装定点同步、主线并线推送/精确CI。没有新外部模型调用或真实下载，原件/生产配置与库不写。C3仍OPEN。

## 隔离与顺序

- ROOT主线`4c8b4642`已发布PDF worker Linux类型窄修；Linux完整379源码mypy通过、独审PASS，精确CI另行观察。原PDF重模型/五页比较不重跑。
- CWP ROOT独占短稀疏工区`company-wiki/cw-w19`，分支`codex/w19-root-integration-20261026`，从`4c8b4642`开始，W19已无冲突暂存合并但未提交。仅该工区实现与测试；作者、生产配置/库/原件不写。初始稀疏检出/index与Windows模式差异已定位，只在自有工区用命令级`core.filemode=false`核对/合并，不改全局配置、不跳过hooks。
- 先CWP数据/公共查询根修与验收，再FF集成/必要薄层修复、安装定点同步及一次跨仓复用；不在当前质量问题未闭合时发布W19主线。不造第二provider、身份库或状态库。

## 已独立发现的共用根因

1. **来源身份没有沿用现有reader DTO。** 手拼SourceRef且`byte_size=None`；作者测试先重新query_ref再读，绕过真实调用缺陷。改为直接使用来源owner给的完整SourceRef，对外返回的引用必须可直接open_version；每源只组装一次，不逐科目重复证明。
2. **两条查询路径的覆盖与版本语义分化。** reuse_only忽略coverage，有记录就complete；PIT仅贴false仍返回未来数据；current_snapshot可能多修订混排。统一既有repository查询/范围覆盖决策，按请求选当前或as-of可知版本，未知范围partial、缺历史时点named gap；reuse_only零网络/零写。不要新加人工门禁。
3. **业务幂等晚于raw持久化，且旧版本引用可变。** 时间戳变化先保存新原件，再把旧版本source重指但保留旧capture。先比较规范业务指纹；未变化复用已有原件/版本，只更新观测；变化保留新快照，旧source/captured_at不可改。规范化失败仍保存可重放原字节。
4. **范围包络复用规则不对称。** from有界/to无界同请求每次1HTTP。将穷尽/请求包络的包含关系集中计算，fetch_if_missing同请求0HTTP；更宽请求按真实覆盖补抓，refresh才明确重查。覆盖不与权限混用。
5. **独立官方财务对照留证不足。** 作者仅2/1/1项且未保留官方SourceRef/SHA。补利润/资产负债/现金流各2项的逐值、币种、单位、期间、合并口径及原定位；优先只读既有原件，确缺时才用既有正规下载工具到独占测试根，结束恢复初态。

## TDD与验收大节点（不加小节点签收）

A. 在隔离工区新增ROOT回归：完整返回引用直接读取；窄/partial采集→宽reuse_only仍partial且0HTTP；真实两个捕获时间/修订的PIT与当前版本隔离；timestamp-only refresh原件数/字节/版本不增长、旧绑定不变；有界from/无界to同请求0HTTP。先保存真实RED和作者证据SHA。

B. 统一查询、覆盖、不可变发布接缝，从根因修复，复用唯一canonical writer与SourceVersionReader。集中运行新回归、W19全97项和迁移/writer旧消费者；完整Linux/Windows源码静态检查。原作者与基线失败如实区分，不改断言换绿。

C. ROOT自建短目录跑FF→CWP→原件/数表→公共查询→直接SourceRef读取→二次0HTTP，增加修订/PIT/覆盖负例；核每表2项官方值、增量空间≤16MiB和重复零增长。请求、字节、时间/费用同一资源对象，保留紧凑收据；测试后恢复不存在，原件/生产配置和库SHA不变。不做完整备份恢复。

最终独审绑定实际新源码及收据，问题闭合后保留作者提交祖先并入主线、正常提交/推送、精确CI与PWF更新。C3正式摘要/cache/RF仍单列；新浪结构化三表不进入叙述切片链。
