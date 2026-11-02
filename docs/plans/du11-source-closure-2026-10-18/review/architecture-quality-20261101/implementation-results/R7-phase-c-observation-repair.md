# R7 PhaseC 成功结果观察边界根修

已冻结，等待ROOT独立审查。对应最终工具扫查 **R7-SWEEP-T01**，只改 `phase_c_runner.py` 与新增一个专属unit测试；未改产品src、配置、CI/hooks、主PWF或Git。

## 真根因与改变

旧观察器在native batch已成功、用量和结果已持久化后，仍仅解压前128KiB+1，并用兼容常量重新否决合法大结果。观察器的任何异常还会把该成功实验统一改FAIL，跳过后续缓存和公共读取。

现在以64KiB**内存缓冲块**完整流式解压、SHA256和byte count，严格增量UTF-8校验；没有固定总表示大小，也没有提高原cap。原生SHA与所有匹配event的SHA/实际字节数继续一致校验，真实坏压缩、缺文件/I/O、非法编码、缺报告/错误协议仍明确诊断，不返回假的匹配成功。

真实调用缝由 `record_successful_model_observation` 接管观测：它只读现有native结果、事件与已保存capture，不调用owner、付费或恢复。事件读取/观察异常只记录 `model_observation.status=INCOMPLETE`、实际native exit/batch status、安全errortype/reason；保留原receipt和usage，不泄露异常正文。后续原有public read、同run恢复、跨run缓存/consumer链继续。其余成功时，整体结果为 **OBSERVATION_INCOMPLETE**，不会冒充acceptance PASS，也不把native成功称FAIL。真正业务、原文、会计、清理失败原逻辑保留。

## 测试与历史

- tests-first：8例实际 **3RED / 5P，37.45s**。精确证伪大结果旧cap、非法UTF8误通过、真实临时run中observer OSError把completed改FAIL。
- 修后纯capture/事件控制 **9P / 3.33s**：合法大结果、完整流式读取、SHA/event字节与哈希、坏gzip/缺文件、UTF8、坏事件及native receipt/usage不变。
- 只复原先前失败的实际run，加10个原有capture/v4/fidelity控制，合 **11P / 48.36s**。真实单版本临时lake+loopback假模型收到1次请求；注入observer故障后，native仍completed，用量相同，public read与同run/跨runcache零新增POST通过；整体诚实为OBSERVATION_INCOMPLETE。
- 两文件Ruff通过。未重复RED整组、全Unit/113/167或真实H1。上述是分开运行，不伪造一次合并20P。

实际使用全是合成gzip、合成HTML、临时wiki/DB和本地假HTTP；测试里的native tokens/cost是合成记账值，真实外部模型费用为0。

## 冻版与交接

- `tools/document_understanding_benchmark/phase_c_runner.py` SHA `3ff59fa819996698041f68e340bf1a7a73961fddba76af026c234ccf5862e589`
- `tests/unit/test_phase_c_success_observation_boundaries.py` SHA `04ca6971cdd6ff7a24016fba31b5c2096f4ea4b4205d5670453dd6beba5633a0`

原RED、全部JUnit/log、新测试源码与真实临时native结果摘要都内嵌同名JSON。自有 `tmp/pc7-a4825e` 初始absent，所有原生临时lake先由测试清理；核精确绝对目录且无重解析点后，恢复整个自有目录absent。ROOT负责集中独审、Git/PWF和发布；作者停止写源码，不自审签收，不代签真实摘要/缓存/RF或H1新版本验收。
