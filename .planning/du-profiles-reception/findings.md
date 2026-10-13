# Findings

- combine 当前按 role 保留第一个 entry，导致 HK offering 英文/繁体别名消失。
- _stratified_probes 先添加全部 heading，前 200 headings 能吃满预算，尾部正文无机会；character 按已排序先来先得也可饥饿。
- SEC_FORMS 检出 S-1/F-1/8-K/6-K，但 decision 只有三种周期表单，后者丢容器或被 results_release 整体取代。
- kind=attachment 无 URI 也误标外链未读，真实 Exhibit 正文无 child 范围。
- revision 被读取却丢弃，摘要标记与修訂仍无独立输出轴。
- 保持 DU/1 confidence 低预算降级，并通过 reason 分别保留强类型与覆盖缺口，不能假装全文已读。
- worktree 默认沙箱 Git 错误由 require_escalated 正常只读解决，未修改仓库 config。


## Implemented design decisions

- Role order and first normalized alias spelling are stable; duplicate aliases normalize NFKC/case/whitespace. Later generic-to-specific blocks explicitly override priority; no role/market aliases discarded.
- Fixed default 200 units/64,000 characters/16 children retained. Cover + span headings + ordinary-body lanes share unit budget; text allowance is distributed before any long front unit consumes all characters. Prefixes carry internal text_clipped provenance so clipping cannot turn prose into a self-identifying title.
- Original source_id/SHA/locator remain passed through; no second source validation or identity authorization added. Budget hit retains frozen confidence low/unknown; strong COVER_HEADING reason remains separate from ROUTE_PROBE_LIMIT.
- SEC forms use earliest printed own label rather than dictionary form priority. Thus an 8-K containing a full 10-K retains the outer container; metadata-only current report is not erased by its attachment's three-month period. S-1/F-1 denotes registration offering, not an asserted IPO.
- Inline Exhibit ranges require every member observed without clipping and no known opaque/deferred page within the range; unknown pageless partial scan also cannot assert complete. Reference prose / external links / standalone empty markers do not become read bodies.
- Additional lifecycle modifiers preserve full/summary/unknown extent separately from original/amended/supplement/unknown revision. A mere internal Summary chapter or cited amended filing does not change the parent. Missing revision stays unknown; registration/approval stage is not treated as amendment.
- Mypy exposed five previous profiles type inconsistencies (invariant reason-list types and boolean helper returning alias string); corrected inside this package without changing formal wire keys.

## Remaining boundaries

ROOT must wire aliases, child ranges and lifecycle into actual shared engine/summary/cache. This lane does not claim production selection/LLM meaning or DU2 strategy coverage is accepted. 8-K/6-K containers keep generic profile/family unknown with sec regime and current-report subtype under DU/1. Unknown docs remain generic_read; no final skip or deletion.
Old QA child markers remain under the existing DU/1 behavior and structure/ROOT closure; this lane changes inline attachments only. Explicit Exhibit boundaries are required; no inferred external source, format parser, table reconstruction or new pipeline.
