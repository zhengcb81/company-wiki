# FF ROOT验收最小复现

`replay_probe.py`与`retained-case.json`可一起复制。用已有宿主Python：

```
python -B -X utf8 replay_probe.py --ff-root <filing-fetch-w20-replay工作目录>
```

脚本只读导入作者既有模块，不启动子进程/网络/下载，不写作者工区。第一部分将一份旧真实report的case对象交给当前断言（不是完整报告oracle，原report SHA见fixture）；第二部分仅用mock验证handler的kill trigger控制流，不能冒称跨仓E2E。未修复时输出`assertion_errors_now=[]`与`triggered_on_unrelated_preexisting_sidecar=true`，即两条反例。

`disk-summary.json`保存23条交接文件核验与4份真实case阶段摘要。测试收据见上层`ff-review.json`：183 passed/6.78秒，原41权威单测保持；不需要重跑41全批。`counterexamples.json`是ROOT首次实际probe输出。pytest自有临时树已清理，作者工区clean。
