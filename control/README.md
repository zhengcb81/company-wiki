# 自动架构检查配置（历史说明）

G5-CWP-CHECKS 起，本目录不再持有运行配置：`architecture.json` 随 `scripts/architecture_gate.py` 整族退休一并删除（全仓唯一代码消费者就是该退休工具的 `--config` 默认值；原文在 Git 历史）。本 README 只保留历史/当前说明。

退休后的六个旧工程门禁与批处理外壳（`semantic_gate` / `architecture_gate` / `clean_env_gate` / `gold_gate` / `test_framework` / `batch_process`）都是纯 stdlib 薄壳：直接调用（含 `--help`、旧参数、`python -S`）报告 `LEGACY_ENGINEERING_TOOL_RETIRED` 并 exit 78，import 与 `main()` 不复制目录、不写收据、不构造模型/Store/下载器。它们不是发布授权或人工签收文件，也没有任何环境开关或 flag 能重新批准旧链。

规则曾经只检查当前批次接现有配置加载器/有限runtime、来源层不导入下游研究实现。已取消旧proposal人工批准规则、冻结ingest/scheduler必须接线及全scripts零文件写入等过期约束，也不再用正则/计数代替预算、恢复与来源验证。详细行为由各层测试负责。

日常检查由 `.pre-commit-config.yaml`、`.githooks/pre-push`、`tools/pre_push_gate.py` 和 `.github/workflows/ci.yml` 定义。commit 不跑行为测试；push 与 CI 共享短 smoke；大型集成/真实资料测试在实施节点运行。

旧 acceptance/lock、known_bad、work_units 和 full-pytest 控制文件没有运行调用者，已移除；原文在 Git 历史。不把历史测试夹具的 gold expected 变成人工权限边界。source_catalog 的职责/导入检查、原件 SHA、来源身份/时间、引用回放、预算和恢复校验保留；环境隔离（API key / dotenv / 外网）迁到 `tests/support/isolated_environment.py` 继续被 hermetic 测试消费；gold evaluator 的真实定位、缺来源、更正、未来公开、重复等反例留在 `tests/contract/test_gold_evaluator.py` 与 `test_gold_mutations.py`。
