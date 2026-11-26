# F4 宿主与 company-wiki 独立终验

2026-11-26，Windows。两个冻结候选在本轮整改范围内通过。执行使用独占目录、合成输入和原业务边界的替身。

## F4 宿主

| 原反例 | 独立复跑 |
|---|---|
| 已排队动作的首次唤醒和冷进程恢复环境不同 | 两次同一原动作唤醒均收到已声明的合成变量，未声明的合成变量两次均未传递。 |
| 独立 `local_host rpc` 对账继承调用者环境 | 公开 reconcile 回传原结果，只看到 registry 已声明的合成变量。 |
| `intake --hosts` 使用非默认 registry 时，owner 补投漏传变量 | 真实显式配置下，owner flush 收到声明变量，未声明变量缺席，drain 无故障诊断。 |
| 兼容 `local_host recover --sidecar --hosts` | 源码初核发现局部导入遮蔽模块级 reader。ROOT 修复后以自身公开 RPC 路由和一个原观察运行，exit 0，状态 expected。 |

复验版本的文件 SHA-256 为 `host.py` `499cf2850a73564a5fa09fd44c76ca7a674e40d343e4d8c6707ba09fcc1ce5d0`，`local_host.py` `cb895b22606bdfaa272b6f420ac686637ce322b57bec285c9e33de45d236e25f`，`intake.py` `0ffa1a4b8782a2cca55a5c42907bee1ba2a3d7f8bb2aa00e169c86bdb1d82fe8`。[三个环境探针](host-ff-probes.py) · [第一轮原失联复验](host-ff-first-pass.md) · [上一轮精确同址测试与 FF 自动补投证据](host-ff-r3.md)

## company-wiki

独立重算 35 条列表路径，排序后以相对路径与工作树 SHA-256 拼接，精确得到 `489f5593cf02c51bd8e5f141aa4407b87d641ec57e1dc6a272f993ea8392301f`。列表排除正在处理的 `read_budget.py`。总控同版 JUnit 显示 14 项通过，0 失败、0 错误、0 跳过。JUnit 文件 SHA-256 为 `db740495817cd44dd6512f5dd53560d2c38069a87a9f0d788f3e3bbed48e2c08`。其节点覆盖真实进程、冷查、坏协议、原文传输字节、诊断路径退化、旧库读取和公开存储边界。

独立从同一源码运行 6 项，全部通过。实际子进程在 AUTO worker 工厂阶段崩溃及被强停后，按原 attempt 从另一进程重查两次得到相同阶段、终态和退出码，匹配唯一原诊断。含折行样本的合成凭据从 stderr、本地日志以及诊断 JSON 中移除。实际 CLI 访问缺库不会建库，访问含 `#` 的真实文件保持数据库字节，坏库报告真实异常种类。业务层只依赖命名存储端口，两个源码边界检查通过。

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
$rc = 'tests/unit/test_cwp_runtime_lifecycle.py'
C:/Miniconda/python.exe -B -m pytest -q -p no:cacheprovider --basetemp .planning/r25/cv4 "${rc}::test_original_preclaim_worker_attempt_can_be_cold_read" "${rc}::test_plan_never_initializes_a_missing_database" "${rc}::test_public_plan_and_corrupt_feedback_flush_keep_database_bytes" tests/unit/test_source_metadata_storage_boundary.py
```

受验源码的发布、正式 Windows SYSTEM 排程和历史极早期中断的采用证据仍按总控交接分别记录。[CWP 冻结候选及原验证范围](../modules/company-wiki.md)
