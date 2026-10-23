# W11 独立复现所需的网络夹具

没有隐式 conftest。test_actual_import_and_network_guard 所需拦截由 run_final_review.py 内置的 sitecustomize.py 注入，现另以 network-sitecustomize.py.txt 保存完整源码；run_final_review.py.txt 为本轮真实 runner 的逐字节副本。原37项脚本、initialFAIL、产品均未修改。本补充没有重跑测试。

复现命令（PowerShell，母仓根）：

```powershell
& '.venv/Scripts/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w11-reception-20261023/independent-final/run_final_review.py'
```

该命令要求 .planning/r1-w11-independent-20261023 起初不存在；只执行同目录 test_neutral_review.py。runner 将 guard 目录及母 src 置于 PYTHONPATH，禁 dotenv、移除密钥变量、用 --confcutdir 排除外部conftest，给 pytest 和四个CLI子进程注入同一 sitecustomize。拦截 connect/connect_ex/create_connection/getaddrinfo（含loopback）；各进程退出时记录实际import路径；核对六产品/测试与六保护文件前后SHA；验证专属scratch绝对路径后删除。日志与JUnit写 final-*，不会重写 initial-*。在重放历史SHA时请先保留本目录现有final-*证据，使用独立副本报告目录或备份它们；不要覆盖历史收据。

源码绑定与真实测试结果仍以 final-review.json 和 final-receipt.json 为准。此说明不要求再次运行，也不增加许可或签收。
