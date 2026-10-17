# DU11 施工卡最终复核：PASS

FF 接口修订已独立核查，DU11-CARD-01 **RESOLVED**，两卡均 **PASS、零未决项，可立即派发**。普通provider=null查询与显式fmp专用lookup已分开；未知日/受限excluded来源保留诊断与重复抑制，成功reader manifest提供真实provider；A/B/C包含真实固定CLI反控，禁止fake接口，README及launch一致。RF卡未变，沿用此前有效审查。

最终四份卡文件SHA见JSON。未执行源码、测试、模型、网络或密钥读取。以下保留首轮审查记录供追溯，原REQUEST_CHANGES已由上述delta闭合。

---

# DU11 施工卡独立就绪审查

审查员 `/root/du10_et_reception_review`。范围仅 README、两张卡、launch 与当前公开接口是否足以独立开工；未执行施工、测试、模型、网络、密钥读取或代码修改。**结论 REQUEST_CHANGES：RF 卡可开工；FF 卡先修一项接口描述。**

## DU11-CARD-01 — 派发前必须修正：默认中性查询不能走旧 transcript-import lookup envelope

卡片称 `SourceRequest/provider=None` 表示中性查询，但 FF 当前 `_query` 固定发 `company-wiki-transcript-import-lookup-request/1`。CWP 固定基线的 `source_query_cli.py` 遇此 envelope 调 `lookup_transcript_import`，后者明确 `request.provider is None` 即 ValueError；CLI输出 blocked/invalid_request。普通 SourceRequest 确实支持 provider=None，但会走 `query_local`，排除未知公开日。因此当前卡写法不足以保证无需 ROOT 新接口即可启动。

已有公开接口足够完成任务，卡中需具体写清：默认provider省略使用普通 SourceRequest/provider=None；显式fmp可保留旧import lookup。普通query结果 `excluded_candidates` 已含未知公开日来源的 SourceRef+qualification，应保留用于重复抑制，不把未知公开日当历史合格，也不把它误作真缺失后下载。已验证打开时 `source_reader_cli` 的 stderr receipt.manifest 已公开真实provider和published_date，作者可从该原有接口取值，不需改CWP字段或猜供应商。明确合法已知日match、未知日、future排除、歧义、坏字节之间的选择规则和反控；对应更新launch输入说明。

这项是接口施工说明错误；不是要求增加门禁或扩大CWP白名单。修卡后可立刻开工，不必等ROOT生产装配完成。

## 已通过部分

两张卡工作目录均未创建；RF `568fb925`、FF `f1a939e5` 与各自main/origin/main相同。RF、FF各自源码白名单不同仓且ROOT独占CWP生产接线，按卡执行不会争用源码目录。已知主仓WIP保护、分支提交后STOP、ROOT统一并线/安装同步均清楚。

RF缺口真实：当前reading validator接受/1与/2且保留reading_context；group/citation_views、support/context、same-parent和unread/layout字段实际存在。`consume_narrative_input`确实把单span写claim/parameter/formula依赖，却没有带上reading闭合与诊断；`research/input_evidence::_bind_narrative_span`是第二实际入口，卡要求共用根因实现合理。旧/新context与projection字段限制可在RF允许路径中完成，不需改CWP。选择view、trace版本与错误码允许在A冻结，边界足够。

FF `_source_request`、lookup返回provider和companion默认值目前都写死fmp，缺口真实；ff_v2_envelope是字段投影，不把provider限制为fmp，因此无需为虚构枚举扩白名单。

两卡均写明真实行为RED、集中B回归/C隔离E2E、供应商边界、独立agent最终审查、全部问题修复与最终源SHA复核后交接，避免自引用提交循环。tmp恢复、sentinel字节/mtime和原件/密钥/WIP保护齐备，无第二缓存、身份库、来源库、人工审批链。以上已通过部分无需重复全量审查，FF修订后只核接口delta。

四份卡文件SHA见同名JSON；此次只写ROOT自有审查文件，未更改施工卡。
