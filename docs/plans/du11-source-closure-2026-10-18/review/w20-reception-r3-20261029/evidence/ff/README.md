# FF第3轮ROOT证据与最小复现

```
python -B -X utf8 mid_import_probe.py --ff-root <FF工作目录>
python -B -X utf8 probe_isolation.py --ff-root <FF工作目录>
```

两脚本仅读作者源码，mock外层边界，无真实CWP/下载/外网/进程写入。前者沿用旧真实mid-import run trace调用当前实际handler，not_found应能通过，probe_error/confirmed应不能通过；2b61088未修前实际三个均FAIL，见actual_handler_counterexample.json。后者为新子进程函数的输入隔离控制流验证，A/B不串且父stdio不变；并非新真实CWP E2E。

case-evidence.json保留两份最新真实lostreply/control case及原report路径/SHA、19+文件SHA核验与完整oracle复核0findings，以及旧真实mid-import case。它不是整个原始报告副本；不冒充新真链。ROOT当前192短测6.25秒，与两原验收问题关闭结论对应。唯一遗留为三态字段迁移遗漏，ROOT自行小范围根修，不再交作者第四轮。
