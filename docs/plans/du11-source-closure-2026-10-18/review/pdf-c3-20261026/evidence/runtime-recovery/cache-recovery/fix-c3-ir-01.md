# C3-IR-01 窄幅修复交接

状态：**已修复，等待原独审 agent 复验**。

## 根因与修复

`reading_candidate_manifest` 把 JSON 解码成功等同于字典对象，selector 0.9 的 base publication 因而在 batch 后续校验前泄漏 `AttributeError`。修复仅在该 owner 的 `json.loads` 后增加两行 dict 形状校验，抛既有 `ValueError("BATCH_REUSE_MANIFEST_INVALID")`，让 batch 现有逻辑标准化成 `BATCH_FROZEN_BINDING_INVALID`。没有扩大异常吞噬范围。

## 先测后修

- 新增永久测试，覆盖 `[]`、`null`、`true`、`0`、字符串 5 类非对象 JSON；每类检查 owner 异常及 batch 标准化。
- RED：**5 failed，25 deselected，2.32 秒**，全部因 `.get` 引起 AttributeError。见 `fix-c3-ir-01/red.log/xml`。
- GREEN：完整短恢复套件 **30 passed，1.72 秒**。保留原 25 项全部断言。见 `fix-c3-ir-01/green.log/xml`。
- 唯一提示为禁用插件自动载入后的 asyncio_mode 未知配置，本组没有异步测试。

## 最终文件绑定

| 文件 | 字节 SHA-256 | LF SHA-256 |
|---|---|---|
| `src/company_wiki/automation/narrative_generation.py` | `720924613789251e0cc6433ba961fc710342969ebcbc276ea641f0a98edbea0c` | `64e9ddd7c63f5fa6b92abd3f15d8e2a8d430880fbdb70481604d763586edf1ff` |
| `tests/unit/test_narrative_batch_recovery.py` | `db8228d73d61b9d1bda5d77a5bb123724a8cb7e9db569d3e6f6d5b908ad77ced` | `97afb46df5004f5c401031477c10baab0328e54589db58237b8007c6aee97034` |

## 范围与清理

仅修改上述 owner 与测试。没有改 batch/PWF/其他修复，没有模型调用、下载、生产配置或原件写入。自有 TEMP 已做绝对路径边界核验并删除，测试已终态退出。详细机器可读记录、日志 SHA 见 `fix-c3-ir-01.json`。原独审应在这些 SHA 上复验后关闭 C3-IR-01。
