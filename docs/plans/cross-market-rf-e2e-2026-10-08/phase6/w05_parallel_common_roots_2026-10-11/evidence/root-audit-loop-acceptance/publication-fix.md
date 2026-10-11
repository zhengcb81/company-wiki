# 发布期间发现的计划资料分类共因

Audit 本体已验收、正常合入 main `321d4c165575e81add3b4aa1ee9ba0a047ca6082`、两套物理技能各24文件MATCH；不因 CWP 发布问题撤回已证明的功能。

CWP 接收 commit `c9dd5124d89144f1350d12de04e6cbeb943f593f` 已正常生成，但第一次 push 尚未上传：原selector只排除`docs/plans/`，把`.planning/`一次性验收Python脚本当未知依赖，误触发全部Unit；Git发布器180秒超时。确认PID/parent/creation/独立basetemp后，只取消自身pytest42572，父finally清理`cwpp-e9b1w3ej`，实读为absent。其他进程/原件未动，不把取消测试记为产品失败或测试PASS。

## 系统修复与实证

- 两套已定义的PWF目录责任相同，selector先排除`docs/plans/`与`.planning/`；不按文件扩展名猜是否运行源码。
- CI push/PR路径过滤同样增加`.planning/**`；runtime源码、测试、配置、未知目录保持原检查。不移除断言，不跳过正常钩子，不改测试超时。
- TDD：原规则5FAIL/53PASS；修复58PASS（pytest1.37s，命令4.32s）。资料probe/conftest、混合runtime、未知相似目录、配置、跨提交/ref范围、临时归属均在同一集中范围验证，scratch恢复absent，pytest短路径回退也自动清理。
- Ruff及diff检查PASS。正常下一次push含测试选择器/CI自身改动，应执行一次全Unit+既有smoke；后续纯PWF资料提交只执行原小smoke，GitHub不启动全CI。

`gate-red.*`、`gate-green.*`及取消记录为原证据。Audit无remote，不创建远端；CWP正常提交/推送/精确远端验真结果随后封存，不冒称第一次成功。没有新增项目HTTP/provider/LLM费用。
