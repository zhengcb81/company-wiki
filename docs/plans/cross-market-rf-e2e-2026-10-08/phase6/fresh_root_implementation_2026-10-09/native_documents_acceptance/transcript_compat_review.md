# W05 transcript 兼容修复独立 major 审查

结论：核心兼容修复通过其责任验证，但发现同模块既有缓存合同绑定缺口，整体暂不验收。MAIN 已认可先补 RED、修统一缓存责任；本审查不改代码。

## 审查版本和范围

- 源码/test commit：`87cdf733f3951f43416300304da84dac5d26d3c2`；PWF 收尾：`7de4fabb9eb4f7c82a9da03397169099f2e3f0fe`。
- Worktree：`C:/Users/郑曾波/.codex/worktrees/fresh-capture-20261009/company-wiki`。
- source diff 仅 narrative_formats / narrative_evidence / narrative_retrieval；另外3个测试文件和该施工卡 PWF。未改 PDF/PPTX 解析实现、原始资料、安装配置、CI 或共享计划。
- 独立集中责任集21 PASS / 2.60s：关键3旧 FAIL、新13个兼容/篡改合同、原文 SHA/伪 locator 两项、实际 HTML/HTM/PPTX 运输3项。没有再跑全 suite。
- 三个实现文件审查前后 SHA 相同。确切 argv、源 SHA、控验字段、输出和清理见 `transcript_compat_review_receipt.json`。

## 必须分清的原因

1. **一个真实兼容 bug**：旧0.1.0被受 PDF 版本影响的两份版本名单错误拒绝。统一 transcript_parser_contract 明确0.1.0/0.1.1使用 legacy、0.2.0使用 natural；generation、parse、replay共用，未知版本具名拒绝。
2. **两处 fixture 声明错误**：旧 retrieval fixture 实际生成0.2.0，却把合同标成共享 PDF0.1.1；它们本来应该被真实 guard 拒绝。修 fixture 跟随实际 parser_component；没有移除 metadata mismatch/text SHA 等断言。
3. **新增 HTML 派发缺口**：自然官方 transcript HTML 可以提取，但该 selected-bundle resolver 原来只认 TXT。修复通过已有 extractor/material.verify 取原语言正文，并仍核原始 HTML SHA/identity和选择集；不接受包内物理路径。
4. **独立 PPTX 夹具问题**：全格式1.0.0断言与既有 PPTX1.1.0不符。作者在未改的 base7762bfd 上复现相同 FAIL并留证明；此次只用实际分别声明的 PPTX/HTML constants 校正测试，所有真实 transport/read/replay/locator/cleanup检查保留，未改 parser guard。

## 独立语义和守卫控制

- 旧0.1.0/0.1.1和当前0.2.0对明确 Full Conference Call Transcript 的正文、management role和旧 paragraph/chars locator正常重放。
- 正常两 speaker 的 natural layout：0.1.0/0.1.1仍返回 transcript_start_missing、无 units；0.2.0实际输出2 units、无错误。旧语义未被新算法重解释。
- fresh resolver 对未知版本、supported声明/row不一致、错误package text SHA、伪文字且同步伪 SHA、伪locator、原文 SHA变化均拒绝。
- 合成官方HTML index → query → resolve保留业务原话并排除footer；body line locator从真实HTML extraction生成。
- 独立初稿用了只有一个 speaker 的 natural 文本，既有 body_start 要求 natural至少两turn以排除导航 false positive，故无body是正确拒绝。该初稿保留并注明为 review fixture预期错误，不算产品bug。显示代码随后访问不存在的 NarrativeUnit.text只用于日志而失败，在创建TEMP/真实replay前已修显示字段，未变生产源码。

## W05-CACHE-R1 [P2] 缓存未绑定消费合同，重复调用可跳过错误版本检查

`NarrativeEvidenceResolver` 构造器保留输入 record的可变引用；`_replayed`缓存只绑定 source ID、raw path和raw SHA。parser/selector/options/selected-set等消费合同检查位于 `_replay_record`，命中缓存后不再执行。

独立 RED：先用0.2.0合法包完成同一resolver的resolve，再只将共享 `record.replay_contract.parser_version`改成不支持的9.9.9（evidence row仍0.2.0、raw/hit不变），再次resolve仍成功，没有异常；fresh resolver对同样的破坏会正常拒绝。这不是0.1.0↔0.1.1同时修改两端一致合同的合法旧算法重放，也不是自然body夹具问题。

### 可复现的最小 RED

```python
raw.write_bytes(LEGACY.encode())
bundle, _, _, _ = transcript_bundle(raw, version='0.2.0')
hit = NarrativeEvidenceSearch(bundle).search('expanded overseas')[0]
resolver = NarrativeEvidenceResolver(bundle, raw_paths_by_source_id={hit.source_id: raw})
resolver.resolve(hit)
bundle['sources'][0]['replay_contract']['parser_version'] = '9.9.9'
with pytest.raises(NarrativeEvidenceResolveError):
    resolver.resolve(hit)
```

统一修输入 ownership/cache binding：可选择消费时冻结合法bundle内部snapshot，外部随后变更不再改变已消费输入；或让缓存绑定完整实际消费契约/相关输入，并对变化重新验证。两方案都应写清接口语义，覆盖合法重复resolve、非法版本/错声明/selector或options变化，不能只把9.9.9硬编码成例外。避免新增重复全文parse或身份/人工许可门。若选择冻结输入，控验应证明实际内部snapshot仍是原合法合同，而非误称变更后的非法输入已被验收。

## 真实 MSFT 只读独立复验

另亲跑同一工作树已冻结的replay_real_msft.py，--raw指向保留原件，--output仅指向新review receipt。273,436bytes，SHA `bdc90bf78dbf55ec3f1d789f1f76ebd2e97c7aab51dcc24a262f5d512fb47656`；481 extracted lines、正文90–414、515 units；41 selected/verified/indexed/replayed spans/groups，models查询4个hit全部resolve。parser0.2.0。独立child1.955s。

原件SHA/mtime unchanged=true，TEMPTMP恢复、TEMP根不存在；external/provider/model/cost均0。真实复验没有变更合同，不能冲抵缓存变更 RED，也不证明整家公司 M3或StockWiki catalog消费。

## 交接和清理

FAIL与初稿证据均保留；请原作者先将缓存问题写成RED再根修，MAIN统一并线。源码未变，所有独占TEMP恢复/不存在；本审查无原件/生产配置/代码/旧执行/共享PWF修改，未安装、提交、推送。修后只需一次集中缓存合同复审，不扩小节点审查。
