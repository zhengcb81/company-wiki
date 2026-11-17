# CWP 缓存回放失败在诊断中丢失

责任仓 `company-wiki`。发现方为 Phase C 工程验收。适用范围是原生恢复断言的记录顺序。状态和最终验证见[实施进度](../progress.md)。

**预期**　同一次运行以下三项各自保留已经测到的结果。公开 locator 回放、同 run 重启、跨 run 缓存恢复。后一个阶段失败时仍能看到前一阶段成功。没有进入的阶段保持未知。

**实际与根因**　之前只有两次恢复断言都通过才把两个 `zero_POST` 标为真。多一次 POST 会先抛出断言，失败本身和已通过的兄弟检查都可能消失。未通过的定位读取也在写入原生 state 前被断言截断。程序整体失败可见，具体哪个检查已经发生无法由可选反馈可靠还原。

**修复位置**　Phase C 在各自原生 CLI 返回后测量 POST，并在各自断言之前保存。公开读取保留此次原生退出和回放处置，原有字节验证和失败结果继续生效。反馈从同一回执映射。类似合法对照是有意构造的负例，以及根本没有执行的恢复步骤。修理入口为[本仓技能](../../../../skills/repair-company-wiki-issue/SKILL.md)。

**复现与消费者**　运行 `python -m pytest -q tests/integration/test_feedback_native_failures.py`，使用隔离本地环回及原生选择器。单独的控制端测试见 `tests/unit/test_feedback_loop.py` 与 `tests/integration/test_feedback_loop_cli.py`。这张卡的验收以原生收据的三个故障定位为界，P1 全新业务摘要及 RF 的消费验收单列。
