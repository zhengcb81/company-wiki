# 自动架构检查配置

此目录只保留 `architecture.json`，供显式 `scripts/architecture_gate.py` 调用；它不是发布授权或人工签收文件。规则变化可与实现一起提交，用有关测试验证，不需要独立 Reviewer、Human Owner、lock 或 Gate Runner receipt。

规则只检查当前批次接现有配置加载器/有限runtime、来源层不导入下游研究实现。已取消旧proposal人工批准规则、冻结ingest/scheduler必须接线及全scripts零文件写入等过期约束。详细行为由各层测试负责，不用正则代替预算/恢复/来源验证。

日常检查由 `.pre-commit-config.yaml`、`.githooks/pre-push`、`tools/pre_push_gate.py` 和 `.github/workflows/ci.yml` 定义。commit 不跑行为测试；push 与 CI 共享短 smoke；大型集成/真实资料测试在实施节点运行。

旧 acceptance/lock、known_bad、work_units 和 full-pytest 控制文件没有运行调用者，已移除；原文在 Git 历史。不把历史测试夹具的 gold expected 变成人工权限边界。source_catalog 的职责/导入检查、原件 SHA、来源身份/时间、引用回放、预算和恢复校验保留。
