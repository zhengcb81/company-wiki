# D4-02 — RF 摘要的实际采用端点

状态：**已备妥，尚未派发。** 完成 D4-02（P2）。所有写入只在 revenue-forecast 仓。

## 唯一目标

让摘要从读取到采用使用同一可替换 reader 连接。`consume_narrative_input` 和 `build_auditable_case`、`run_narrative_consumption_e2e` 不再偷偷回落到 `python -m company_wiki...` 默认模块；同一已验证 NarrativeContext 能绑定到 RF claim/parameter/formula，不重复读取/请求。

## 写域

允许修改 `scripts/source_narrative_context.py`、`scripts/company_wiki_narrative_reader.py` 的连接适配（仅确有需要时）、`tools/build_auditable_case.py`、`tools/run_narrative_consumption_e2e.py`、相关 RF tests/fixtures/docs。禁止修改 CWP/FF/StockWiki/ET、RF 配置模型、历史 assurance/runs、ROOT `integration/` 与 runner。

## 先写行为测试

1. 使用不同目录、不同名称、独立 Python 的合成 producer 脚本，不安装/导入 `company_wiki`。显式连接下，read 成功并产生与原 public reader 相同的验证结果。
2. 完整公开采用入口接收这个连接配置并把同一个上下文绑定到 claim/used parameter/formula/report。一个选择只实际 read 一次；不同来源/hash/期次仍被拒绝。
3. 两个公开工具传递相同连接，不只单测 helper。对未指定连接保留原兼容默认行为，但测试须覆盖显式部署，不通过 monkeypatch 整个 reader 隐藏调用链。
4. port 的 stdout、stderr、exit status 和 receipt 都用独立进程验证；无 API/network/原件/付费模型。

## 通过标准

`prepare` → 真实 `consume` → RF 正式校验 → 真实参数/公式采用全链无 CWP checkout/PYTHONPATH；同端点可替换、source binding/source hash/as-of 保持。只跑本卡新增与受影响 RF 快测。

交付前由未参与实现的独立审查 agent 审公开入口覆盖、重复读取、异步/错误传递和 source binding；问题修好后交 ROOT。交付 `handoff.md` 记录基线/commit、接口传递、实际测试、独审、无网络及 ROOT 组合待办。不得改历史 artifacts 或 RF/AUDIT业务 PWF 状态。

