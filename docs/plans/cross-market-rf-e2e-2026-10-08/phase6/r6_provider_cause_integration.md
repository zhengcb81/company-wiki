# MAIN：有证明的采集失败诊断接线

状态：待实施；R6-FF-CAUSE分包已交付。本节点是现有失败信息的透明传播，不新增许可/签收/身份审查。

## 实查责任链

`JsonCommandAdapter._run`已有AdapterProcessError.error_code/retryable/adapter_version/acquisition_usage/acquisition_usage_complete；失败用量缺完整性时已有禁止自动重试。`SourceAcquisitionService._ensure`记录journal后原异常重抛，未消除原因。信息丢失点是source_catalog CLI→error_taxonomy.structured_error：目前仅发catalog类error_type+文本，机器adapter原因和实际用量没有发布。FF.ff_provider_cause只读已发布原因，provider_started/usage_complete保持null属正确未知，不能改成假零。

## 接口与实施

1. 先在当前producer责任层写RED：已校验的结构失败原因、完整用量、下界checkpoint、无checkpoint、任意code/敏感正文、不能启动和超时分别覆盖；额外字段缺省不改变旧catalog Busy/Locked/Timeout消费者行为。
2. 在CWP失败边界增加可选版本化acquisition_failure诊断，既有四字段保持兼容。原因采用实际adapter已使用的闭集code，未知变adapter_process_failed/unknown；不外发error消息、stderr、物理路径、URL query或密钥。用量沿用预算账的原schema，不建第二费用账。
3. `provider_started`是外部市场/电话会adapter确有执行证据，不是CWP CLI自身启动：验证过的adapter结果/usage checkpoint能证明true；生产工具在启动前失败才能证明false。外层OSError可能发生在子进程执行后，不能仅按异常类型推断false；超时没有checkpoint仍为null。需要补证明时由CWP自己的有界transport记录，Dayu源码零写。
4. `usage_complete`仅依据已验证完整回执为true、强杀/下界为false、不可知为null；actual response_bytes/cost按已有预算校验，非负整数/合法decimal，不把下界当最终费用，不因unknown自动重试。unknown不等于0美元/0HTTP。
5. FF一次解析stderr，优先消费新增机器诊断并保持filing-upstream-cause/1固定六字段兼容；现有catalog争用重试策略不变。真正未知原因/用量依旧null，没有文本关键词猜测或新身份合同。RF消费FF同一公开失败对象，不跨目录扫描，不改研究数据。
6. 使用独立临时源库跑真实FF→CWP CLI→fake provider的集中失败/正例链，包括入库前和入库后失败、预算截止、stdout/stderr超限、异常重试是否受用量限制；保留原件保护与TMP恢复断言。一次大节点验证后提交各仓主线、同步必要运行文件并查看CI。真实供应商权限/404单列，不再购套餐或切模型。

## 验收和边界

- 每个已发表原因可回到实际producer机器事件；不由英文报错推断市场身份、公开日、费用或启动。
- generic/catalog既有合同仍通过，新增diagnostic不会改变成功原件SourceRef/下载次数。
- 已知失败可定位；未知仍明确未知。原件、生产配置、owner WIP与Dayu不改。
- 只在整个接线节点审查/测试；不能给每个内部函数添加人工批准、approval expiry或合同hash。
- 输出本节点进度、集中测试命令/结果、临时根恢复与精确发布SHA到总PWF；无额外外包分派。
