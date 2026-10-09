# Findings

公开GitHub REST已读取38个CWP/15个RF/9个FF相邻run：CWP3次、FF2次失败，RF没有失败。完整job logs新请求403；公开annotations、Git exact blob、新独立复现及已有PWF实读记录分别标明来源。调查基线CWP7073bde5，工作树原先干净。

| 真实run / head | 已证实根因 | 已发布直接修复 |
|---|---|---|
| CWP37822907874 /335df5d3 | pyproject声明httpx但CI requirements缺项；旧实读日志证实openai3.26.1传递依赖改httpx2。本机已装包掩盖缺项；新REST确有collect error | 7071e035显式声明+parity test |
| CWP37847182377 /bf8f0e82 | head是末尾docs，push含前序1a58职责改造；4unit仍要求已取消metadata/permission许可，旧21FAIL/78PASS、新REST具体cases对应 | 2e54b5df依据职责更新断言，保留真实SHA损坏拒绝 |
| CWP37883563191 /a901b67f | 无generation旧builder错误冻结成不完整/3，恢复有真实兼容缺陷；PPTX parser1.1而旧全格式预期1.0/旧patch入口。旧16FAIL/35PASS、新REST和d11 diff相符 | d11db2a2合法/2与完整/3区别，坏/3不降级；三版恢复与每格式契约保留 |
| FF37832787908 /3945efb | 独立exact测试正常OS复现_provider_usage复杂度15>10（1FAIL/1PASS）；旧418行为PASS/5SKIP/78subtests | 697af966按计数/身份拆责任，原ratchet2PASS |
| FF37861936346 /afbef65 | 独立exact复现_valid_acquisition_usage14>10、_acquisition_evidence11（1FAIL/1PASS）；旧419行为PASS/4SKIP/78subtests | e9b0d08统一分数为维护诊断，保留行为/类型契约 |

**为何pre-commit没有阻止：**三仓hooks实际有效，无旁路证据。commit刻意仅静态检查，避免每次数分钟；CWP push只有13smoke，CI完整unit，遗漏上述6unit文件；FF push不跑pytest，CI另列26文件。共同根因是职责/覆盖入口漂移，最新CI绿色只证明直接修复。

## 防漏检实现，待精确远端验收

- CWP push读取所有ref的remote-old→local-new并集，不看HEAD^；rename/delete两端包括。缺对象/新branch/配置/runner变更回退完整unit；AST相对/传递/fixture/字面module，未知动态consumer保守纳入，别名/相对动态/路径执行有反例。无缓存库/许可记录。CI保留完整unit。一般叙述模块变更实测仍选117文件，不虚报所有push数秒，不承诺静态分析穷尽动态行为。
- direct runtime声明共用静态检查供commit/unit，仅声明文件触发，不受本机已装包影响；Python3.10用条件tomli测试依赖，CI3.12不新增包。
- JUnit collect traceback仅抽异常类，避免unknown_error而不输出正文。push失败保留首个node；child剥离Git hook仓库上下文，避免临时Git测试被父.git污染。
- FF397ec0ee已验收并fast-forward main：原26文件+runner自测=27，CI/push共用一次pytest。正常OS549PASS/4既有条件SKIP/78subtests，59.70秒，commit静态不变。Windows/3.13和Linux/3.12、当前本机runtime与CI兼容pin仍有差别，不能用本地替代精确远端结果。
- 新集中53PASS/1.17秒；独立审查别名/动态consumer4RED→GREEN、JUnit1RED→GREEN；另增Git child context测试随正常push集中验收。基线全unit2299PASS/128.21秒。sandbox假失败不当作CI代码根因。

证据：runs/jobs JSON、hook_audit、historical_repro、historical_selection、selector_review、local_validation。成功全量XML仅保留hash/小摘要并移除362090B冗余输出，测试夹具owned TEMP，原件零修改。
