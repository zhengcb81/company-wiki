# RF 精确CI失败根因与窄修复

已原样仅运行一次 `tools/pre_push_gate.py --ci`：Ruff通过、mypy15源通过，行为 **1F698P1skip36subtests /65.59s**，总71.164s。全部三阶段stdout/stderr、argv/退出码和JUnit完整保留同名JSON；没有依赖工具截尾信息猜测。外部网络/模型禁用、dotenv禁用，没有读密钥值。

唯一失败是 `test_malformed_availability_is_a_bounded_contract_refusal[oversize_locator]`，它仍要求2049字符locator因长度失败，而R7已明确取消2048字许可。不是产品重大缺陷。只将该参数迁为单独合法长locator正例：6400字符完整availability proof保留，原artifact SHA/输入不变；其余真正坏schema/类型/路径/绑定反控保留。

补丁首次因原CRLF匹配断言停在写入前，随后目标未生成导致0收集；错误日志原样保留。修正换行处理后，只测长locator及原wrongSHA/asof四反控，**5P0.27s＋单文件Ruff绿**，没重复整组。

最终仅RF `tests/test_r1_narrative_availability.py` 改动，SHA见JSON。81个RF scripts/CLI runtime逐SHA不变，4份RF WIP不变。ROOT负责独审、正常提交推送和精确远端CI，本报告不冒远端已绿。临时资料归档后恢复自有目录absent。
