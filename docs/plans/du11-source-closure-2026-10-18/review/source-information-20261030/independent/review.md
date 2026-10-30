# 来源语义根修独立终审

结论：**PASS，工程审查范围内 OPEN=0**。签署对象是 HEAD `d6d3a5a038456d1d010a6c6aebde83b852833d7d` 上本轮 7 个运行文件与 3 个测试文件的工作区字节。10 文件实际 raw/LF SHA-256 全量列于 `review.json`、`hashes-final-r4.json`；测试前冻结并在签署时逐一复核一致。

最终独立 **25 passed / 0 failed / 0 skipped，pytest 1.95 秒，命令 4.23 秒**。范围包括会计／抽象与嵌入问题负例、命题否认、中英文未知参数、已知产品、需求因果及否认因果、金融软件／表格兼容、未闭合参数、原文 refs、缓存零工作增量、实际 native reading 选材和既有已知参与方 contact。日志/XML 为 `independent-final-r4-strengthened.log/xml`。未重跑全仓，ROOT 领域测试和 mypy 不计入独立数量。

关闭了六类实际问题：会计名义对象获制造 proof；嵌入疑问依赖外层动词白名单；“并非因为”被当成正向因果；陌生中文／小写名称丢失；抽象效益获制造 proof；“公司否认已经生产…”被当成发行人正向实际生产。ROOT 后续发现的 known-party contact 回归已恢复原有效分支，独立新增对照通过。混合关系既有测试保留原财务背景，并增加显式财务断言；typed/untyped 与不得捐赠 proof 的断言仍在，不能要求嵌入“是否”产生实际关系。

原 14 例中未知名称的 support 预期作了明确三态迁移：最终要求 `unknown_argument=True`、`relation_bindings=False`、`independent_payload=None`、`use=unresolved`、source relevance 保留，并实际进入阅读选材。它不再把未知实体自动授为产品／独立业务资格。旧输入、失败探针和中间 XML/log 全保留；已知产品与闭合业务因果仍必须 support，不能靠丢弃有用原文通过。

静态核对新增扫描先收费、每 scope unknown sidecar 只登记一次、partial 状态不能授 complete unknown 观察、缓存复用同一母预算；没有第二余额或任务库。公开 relation wire 与原文位置映射未改；财务名义身份复用统一 owner，未扩大旧 table-wide 会计 veto，真实金融软件及对应表格仍可用。

历史执行不累加：初轮 14 项 10F/4P（3.18 秒，随后调整自有 lazy 准备顺序）；调整后同 14 项 10F/4P（2.14 秒）；首轮修后 14P（1.44 秒）；扩展 18 项 4F/14P（1.63 秒）；三态中间版 24P（1.91 秒）；最终兼容版 25P（1.75 秒）；增强问题 actual 反控后同版 25P（1.95 秒）。另有 40 个保存的短 owner 输入，仅作探针。一次补充探针在 ROOT 写入时 import 暂态失败，0 输入完成，不计通过或产品缺陷。

本终审不代签 QA 闭合支持视图、真实全金标、正式摘要、缓存恢复、FF/RF 采用、W21、holdout 或公司循环。ROOT 曾报告宽域 3184P/11skip/3F，之后修复不由本短包冒充完整领域重验；真实保存 parsed 20 spans 仍 partial。

清理：只写此独审目录；保留脚本／探针／日志／XML 作为复现证据。Python `-B`、pytest `no:cacheprovider`，此目录无缓存子目录。未修改产品、作者测试、共享 PWF、配置、其他仓或 hook；`git diff -- config` 为空，原 hook 仍是 0/0 内容变更的既有 mode WIP。未读取 PDF 原件、密钥或 SDK；0 模型调用，0 下载。
