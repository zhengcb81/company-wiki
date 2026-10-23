# W09 独立验收复现

在母仓根用PowerShell执行：

```powershell
& '.venv/Scripts/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w09-reception-20261023/independent-final/run_independent.py'
& '.venv/Scripts/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w09-reception-20261023/independent-final/verify_artifacts.py'
```

没有隐式conftest。runner显式用--confcutdir排除其他conftest，把候选rf-runtime/scripts与专属guard加入PYTHONPATH；sitecustomize源码另存sitecustomize.py.txt。runner安装禁网和真实read_text/import跟踪并在子进程继承，原文件只读，专属scratch必须初始不存在且结束删除。代码、tests和数据审计脚本均另有逐字节.py.txt副本便于持久保存。复现需保留handoff所列母候选、作者数据和RF main3份WIP；原文PDF/密钥/外网不需要。若这些冻结身份已变化，停止重放旧验收；不要绕过版本断言。命令会写本目录的stdout/JUnit/receipt，因此历史证据应先在独立报告位置保留再执行。本次报告后没有为补文档而重跑测试。
