# D4-05 — FF 进程诊断不再否决已完成结果

状态：**已备妥，尚未派发。** 完成 D4-05（P2）。只写 filing-fetch 共用子进程传输实现与相邻真实子进程测试。

## 唯一目标

stderr 是可选诊断；stderr 超过 64KiB 时不得把 stdout 已完整交付的成功 JSON 改判为 `OutputLimitExceeded/upstream_error`。stdout 业务 payload 与 stderr 日志的容量/用途分开表达，不相互扣额度。

## 写域

只允许 `scripts/ff_process_transport.py` 及 `tests/test_process_business_exit.py` 或清楚命名的一个局部 FF process contract test。若现有 FF client 需要接收统一 native outcome，限改紧邻 FF caller 并证明同一错误 owner。禁止改 CWP、ET、公司来源、FF 接口 JSON schema/预算配置/用户 API、CI workflow、其它仓。

## 先写行为测试

1. 真实独立 child 写出并 flush 一份合法完整 stdout JSON，再写 65,537B stderr，正常 native 业务结果仍返回；日志保留策略有界且不影响业务状态。
2. native payload 错误、stdout 不完整/超出调用者实际 payload 预算、stdin 未完成和 deadline 到期仍如实失败；owned process tree 仍及时退出。
3. stderr 高字节但 stdout 为业务 `not_found` 时仍返回 `not_found`，不把它改成 child 错误；FF 原 ET acquisition usage/unknown cost 语义不变。
4. 在 Windows 和 POSIX 按本仓运行环境用受影响的小测试覆盖子进程关闭语义。没有必要改远端 CI 全量矩阵或增加每次提交的多仓测试。

## 通过标准与独审

保留实际 deadline、请求者原 payload/resource 上限、完整 stdin/JSON 语义和 bounded shutdown；修的是纯诊断超限否决路径，不许变成无限缓存。独立 agent 审 `ff_process_transport` 所有六个消费者与资源/退出语义，问题全修后交 ROOT。交付 `handoff.md` 报基线、commit、具体测试、独审、临时文件恢复及已证明的边界。

