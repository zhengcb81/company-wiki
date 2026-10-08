# 元数据、历史选择与读取责任集中验收

状态：责任测试通过，待冻结提交后的三市场full/replay。不是全部PWF或新研究验收完成。

## 实际代码变化

1. `MetadataObservation` 共用只读投影，Reader/Resolver/旧envelope使用同一规则。字段冲突变未知，原诊断保留；全明确derived的分类/标题差异只说明推断差异，不冒充发行人声明冲突。公开日、财年、公司/代码等真实请求字段争议仍不能命中对应请求。
2. 精确SourceRef打开只验证实际版本、当前位置、文件字节、类型/大小；不重复要求公开日、财年、完整capture、人工审查。manifest/export v2字段不增加，不创建新事实库。
3. 自动runtime_policy许可停用，现代resolve/ensure/query/read一致steady；旧snapshot仅显式compat。旧valid fingerprint是生成观察，回执报告当前观察，不静默重签或假装指纹未变化。
4. Transport一次取得描述与实际字节，取消前后自取pin、自验pin、全元数据等值与重复ref检查。artifact完整性/真实locator回放/明确expected_source/as-of检查保留。
5. Worker不因标题/声明语言/旧策略指纹变化拒绝同一原件；已完成batch恢复不因当前metadata或可容纳限额变化而重复模型。Frozen intent/membership/execution/预算账篡改仍拒绝，原冻结文件不改。
6. GapPlan把未知/非法日期保留为publication_unknown库存，不冒认已公开、latest或not_published。

## 证据

- 19新真实RED（8.69秒）→19GREEN。
- Worker/Gap补5真实RED（32其他PASS）→75PASS/1旧unknown-date要求，再按新历史资格合同调整该旧断言。
- 已完成实际CLI/Worker修正辅助metadata/宽松限额后恢复1真实RED（6.67秒），实现后账本/模型请求次数/预算不变。
- 读取/导出/策略观察/Transport/Worker恢复集中297项：296PASS/1skip，155.94秒。skip仅未显式提供只读真实TXT，后续固定三市场原件重放覆盖TXT。
- 新声明争议负例、append-only修正、formal质量与恢复40PASS，14.16秒。
- 上游ensure/acquisition/identity/v2/recovery234项：231PASS/3FAIL，60.16秒；其中2旧权限要求更新，1真实derived-kind投影回归共用修复，原resolver断言不改。随后resolver/source-facts/全部新元数据57PASS，9.09秒。
- ruff改动文件及mypy七个责任模块通过；提交时继续原有轻静态检查，无新增逐commit集成或收费测试。

数字间有重叠，不合计为新的唯一用例数量。全部本机/fixtures/loopback、费用0、外部模型0；生产config与原件改动0。外包新子目录和邻仓owner WIP零写。清理报告及冻结E2E在后续补充。

## 保留检查的实际责任

| 检查 | 责任 | 理由 |
|---|---|---|
| SourceRef的source/document/SHA/size/MIME与当前索引 | 字节读取边界 | 防止拿错版本；原始文档不可丢、不可伪装成另一个来源 |
| 注册相对位置/当前根/实际SHA与大小 | 存储读取层 | 实际文件移动或损坏时要重新定位；不能拿错文件或无界读取 |
| 明确请求公司/期次/来源与as-of | 选材层/明确消费者请求 | 防止把另一家公司/另一期间/未来信息作为指定请求的证据，无辅助字段时不增许可 |
| 原件/summary SHA、引用locator回放 | 派生与导出层 | 确保引用真在原件里；标题/网址冲突不代替实际回放 |
| 实际字节/期限/费用限额、并发锁、usage账 | 下载/运行责任层 | 防止资源失控、重复下载/丢账；没有人工合同签收 |
| Frozen membership/intent/执行版本与账本一致 | 可恢复运行层 | 旧费用和任务不能因重启改绑；metadata/current指纹不作为许可 |

## 后续

跨run默认内容复用还有单列施工项，当前只保证同run恢复不重跑。新HTML/PPTX、RF输入语义和FF失败cause分别在已分派线，MAIN接线和两组完整新研究仍须执行。不能把本节点绿记成产品全部完成。


清理：9个具名owned pytest根已恢复不存在，释放207,312,882B；原件删除0、生产配置修改0、三个外包工作树删除0。明示类型/大小等实际当前规则继续生效，未添加日常commit测试。
