# R7 ROOT残留根修独立审查

结论：**PASS_ENGINEERING_SELECTED_SCOPE**。已核ROOT最终16文件（RF7＋FF7＋CWP2）以及明确追加的public material2文件，共18个最终SHA；执行前后和清理后不变，RF4份既有assurance WIP逐SHA不变。本人PhaseC2文件未审，仍由其他作者独立检查。

## 真问题及本轮闭合

首轮发现真实P2：去掉8KB许可后，ET `_provider_usage` 对大而深的坏可选JSON未捕获RecursionError。独立实际复现：12,000空白＋3,000层非法usage数组，共18,100B，在旧冻结transport `6eec5596…` 抛RecursionError；实际caller在transport已返回后、不在异常保护内解析usage，会打断主要状态。不能恢复大小/深度帽解决。

ROOT随后tests-first修为捕获UnicodeError/ValueError/RecursionError，保持None/None/False未知用量。原delivery记录仍保留，审查按 `final_delivery_files_sha256` 签新版；transport最终 `8fd24051d403665599a3fa2f3be3f16cb997e504d84e23ae40409b8fb96c9855`。独立复原相同深JSON、超Python整数转换的坏counter均诚实unknown；合法大收据仍为已知2次/300B，错request/schema/Falsecomplete/boolcounter不伪complete。P2已关闭，旧结果未改写成历史通过。

## 公有接口与正确性

- **真实FF生产DTO→RF公有消费**：通过正式 `ff_v2_envelope.error_envelope` 和local_preparation_observation生成大DTO，再由独占回放桩流给真实 `filing_fetch_client.py --result-envelope` 子进程。没有mock RF解析器。三条链分别证明：>128KiB完整附注保留，FF生产端坏附注剔除，以及RF遇未知外层附注schema剔除；主source_blocked、upstream_cause、calls7/downloads0均保留，local_io_usage未知仍None，不以诊断宣称原文或provider成功。此处是公有DTO/消费契约，不冒充真实采集/provider全流程。
- **循环、别名与未来owner**：FF与RF都接受重复别名、未知内层owner schema，JSON副本与原对象隔离；真循环拒绝。未知外层sidecar只剔附注，不抹主因。未把None/False改成完整或零。
- **原生RF研究/回测**：带700段额外原语言Unicode的长摘录完整进入typed builder及原生run_forecast，改SHA拒绝；17驱动/13证据可完整建模，归因强重算闭合，增加.017权重仍拒；长actual excerpt回测保留，错币种仍拒。source_clock仅去长度，不删来源SHA、时点和pathless要求。
- **真实流预算**：本次改变是解析器/诊断表示限制，FF/RF实际进程收集/超时、来源与采集预算不被删除。观察到的“7GiB/900s”等只是原owner附注，不由下游重复执行或当许可。
- **CI调度**：实际调用main、只替换执行器记录调度：daily保持原35项；CI22项集合精确等于原fast minus13个已被全Unit覆盖的Unit节点，Contract/Integration无损。显式full模式保Unit一次与原余下Contract。没有新job/flag、安装或隐式部署。
- **public material**：默认512rows/groups、4MiB、4096units帽和only-lower clamp删除；显式619rows/700额度保完整文本SHA，真work1仍拒，原文篡改仍拒。默认work200k及显式调用者实际额度保留，不截分母，也不冒充此库已有内建生产caller。

## 实际有界验证

本审查新8例 **8P / 2.04s**；另加1个原生RF合成组合 **1P / 0.85s**。这是两次定点运行，未重复111/65/77/全Unit/整仓。所有探针源码、原始日志/XML、初次反例和最终18SHA均保存在同名JSON。

原manifest16旧字节历史保留，最终ROOT报告SHA `ff49fb55ab25602a0a9389fdd4ec5d87ea395ce0574c63cec879e762f9968aab`；附加material报告SHA `872e8705bacc9279cfc71b5354b0ffa64ccbe2a94d2a426d818dc0fa06e8975c`。原先RF新夹具/过窄错误消息失败的历史不删除；没有靠改产品正确性让它们变绿。

专属 `tmp/rr7-415b6d` 初始absent，精确校验路径与无reparse后恢复absent；原件/模型/下载/外部付费均0，未写源、测试、Git、主PWF或RF4WIP。只签这次工程边界，不签新真实H1、摘要、缓存恢复或RF经济/公司采用。无待根修P1/P2；ROOT可进入正常提交和完整CI发布节点。
