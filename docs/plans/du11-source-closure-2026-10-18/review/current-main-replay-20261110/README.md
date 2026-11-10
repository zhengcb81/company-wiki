# 主线复验与整改

## 已实施

来源入库校验、CN 封面元数据读取和 PDF 语言采样统一调用 parser_adapters 的公开接口。原生 SDK 和文件句柄留在解析实现内，预算检查和取消异常继续传递给调用方。三个消费模块都有禁止直接导入 PDF SDK 的回归。

source-case 观察器此前只对 SHM 放宽 mtime，原件、DB、WAL 和观察器自身仍可能因同字节时间戳变化失败。当前统一以存在性、大小与 SHA 判断内容，mtime 保留诊断。缺少内容证明、变大小、变 SHA 和消失的文件都有反控。

基准工具此前先加载全部 gold，再处理 --sample。因此无关样本的历史重复版本会阻止指定样本运行。当前加载器在请求作用域内验证唯一性与 schema，显式缺失的样本逐个报告。完整集合调用仍会报告集合自身的重复记录。

历史 us-10k gold 已原样迁到 local-flow-cross-market-20261025 证据目录，SHA 为 4dd0875a81b82508cf02f874e80df6d712da2ee756a26f44feee5f5f7e28a2a8，原 precheck 跟随迁移。四个回归失败来自 Windows 默认 GBK 读取 UTF-8 收据，测试现显式使用 UTF-8。官方来源集成测试的两个旧入口观察点也已迁到当前 owner。

## 两份半年报各自记录

| 样本 | 原文 SHA | 当前观察 |
|---|---|---|
| cn-h1 | 182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe | 0.9 读取器 10/10 业务事实、7/7 critical，210 页，112 spans。整体 PARTIAL，保留未处理内容和未做语义审查的状态 |
| r4-cn-h1-real | d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f | 正式 Reader 两次均 9/12，三项缺口均已解析到原始单位但未入选。第二次 74 spans、67 native members、199 页，工作量 15,994,242 / 16,000,000，exhausted=true |

第一份旧 0.8 基准入口为 1/10。不同版本与第二份来源分别记录。冻结当前 0.9 实现的完整检查结果在 cn-h1-09.json，运行前后源码摘要及原文保持一致，parse 3.401 秒、select 52.181 秒，0 模型、0 下载。

第二份正式 Reader 复验为 26.683 秒与 40.320 秒，原件、DB、runtime 和 observer 均保持一致，0 模型、0 下载，临时目录恢复为初始不存在。完整临时收据已按测试恢复要求清除，本文保留实际命令输出的关键指标。旧候选的 101/102 成员计数与当前预算耗尽产生的 67 成员分开核对。

## 当前问题与实施顺序

1. 优先完成 Dashboard P3 的 owner 端口接线。旧 stream 候选仍直接调用 Reader 私有候选方法，自建预算并在两次读取间重置，还包含固定字节帽及 POSIX 阻塞 flock。先将类型化流式能力归入公开 Reader，再由 CLI 消费。取消、配置上限、同句柄验真、两个同 SHA 副本与根迁移均应进入边界测试。canonical 候选中的来源浏览私有调用和直接 PDF SDK 调用也须迁到公开端口后发布。
2. R4 来源选材按单一工作账户做阶段/调用耗时分诊。先找反复解析、反复语义扫描和数据重复投影，增加去公司化回归并在原预算内修复。保留三个已解析但遗漏的原始 unit ID，见 task_plan 和现存 cases.json。
3. 完成 T4 父链和 SEM-QUAL-01 的实际模型输入及解码反控，集中独审后继续真实摘要、缓存恢复、RF 实际采用。
4. 继续逐项核销 M3、source-facts、W04 semantics、R1 observation 和 Dashboard 的候选工区。按用途收敛现有差异，发布已接受功能。

## 验证

- gold 请求作用域新增测试先得到 2 failed，随后修复通过。
- 门禁、边界、限定、gold 和 PDF 端口定向组合 147 passed。后续补充语言采样和内容变化反控的最终组合 123 passed。两个组合有重叠。
- 受影响官方来源与本地复用集成 10 passed，当前 LLM 配置范围 25 passed。
- 独立 agent 审查通过，另跑 42 项离线测试，并用独立探针核对真实内容变化、缺证明和中途取消关闭句柄。语言采样增量复核通过。
- 初次扩展集成集合运行遇到退休入口和观察点失败。定位后用受影响子集验证，原长集合已终止。其余集成用例继续按后续大节点范围执行。

## 本地核销

W04 config 旧工区的 3 个修改文件、22 个未跟踪文件及 binary patch 已归档到 workspace-reconciliation-20261110/w04-config-author-package，并逐文件核 SHA。当前 Config.load(validation_scope="llm") 和正式 configured CLI 已覆盖其职责，25 项现行测试通过。已移除旧工区和已并入的本地分支。

两个重复本地别名已移除，commit 继续由 codex/d00-return5-cwp-audit 与 codex/dashboard-cwp-return4-d00-fix 引用。原始公司文档保留。

七份历史失败 push 原日志共 15,896,545 bytes，已进行 gzip 原样往返核对并保留于 retired-push-logs，共 1,430,555 bytes，原未跟踪日志已移除。另清除四个已结束测试的进程控制文件，共 17 bytes。原始日志路径和 SHA 映射见该目录 manifest.json。

## 发布与测试恢复

源码和本轮PWF已在729a787641fccdad490f81b34e10669b16385e53进入master并推送。Ruff/mypy与18项push smoke通过。25份当前配置测试的llm.yaml临时夹具共10,344bytes已核对为自有测试产物并清理，目录恢复初始不存在。远端CI记录42912332126目前in_progress。

## 远端 CI 增量根修

CI42912332126的Unit tests有2F，位于test_source_fact_entity_projection的query/resolve参数例。实际失败在错误公司名加正确证券代码时仍被接收。SecurityMasterStore把精确代码误当成任意名字的重命名依据。现将精确代码消歧限制在真实alias成员或等价市场代码内，保留已证明跨市场关系与原样名字查询。新增contract先1F，修后59项相关回归通过。该缺陷归身份owner，发布修复后继续核验远端结果。

身份增量独审通过。独立22个关键回归通过，4.64秒，复核同名/共享别名、零填充代码、已证明跨市场关系与wrong-directory反控。

## R4 工作量分诊

在源码28e18043c上以只读execute运行，观察root WorkBudget.charge，保持16M账户与原规则。24.865秒，仍9/12、74 spans、账户耗尽，源码和原件稳定。SourceOperatingSession.fact统一业务扫描预扣记9,051,854单位、1,388次调用，占全部账户约56.6%。该费用按READING_BUSINESS_SCAN_PASSES乘文本长度预扣，下层语法和purpose也有独立实际计费。下一步核对预估是否重复覆盖下层计费，再按真实执行的owner归账。观察没有改变计费规则或额度，完整统计在r4-work-profile.json。

## 2026-11-10 22:31 UTC 最终发布结果

身份修复源码28e18043ccad06495a0843760ea46c79e0d2222c已推送，远端CI42914407976 completed/success。首轮42912332126两例失败继续保留，相关59项与独立22项通过，第二次push smoke18项5.58秒。下一步按P3公开owner接口优先，再用已有R4工作量收据改进统一预扣与实际计费关系。
