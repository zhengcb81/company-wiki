# PDF v5 完成页检查点独审

PASS。绑定 handoff-v5 四文件，raw/LF SHA 在测试前后均一致。无 open 发现。

独立定向验证 **48 PASS / 4.04秒**：冻结独立18项，加30项必要wire/legacy/partial控制；其中2项真实标准库cold子进程，无Docling或原件PDF。未重跑作者165项，也不把作者统计当本审查执行。

- PDF-IR-01闭合：公共合法天花板由wire常量共用（16页/300秒/8GiB/32MiB），父层实际请求及剩余deadline绑定不变。生产3页/120秒/4GiB/2MiB及64MiB输入/4线程默认未提高。
- PDF-IR-02闭合：低层opaque source ID有限非空、原样传递和精确echo；错ID仍整流拒绝，SHA独立绑定。
- PDF-IR-03闭合：迭代JSON prefix语法按对象跟踪解码后的唯一key；合法UTF8及Unicode转义的每个byte切点、深栈和跨对象同名key通过，完整坏帧/重复key/不可扩展尾拒绝；完整对象无换行不冒提交。

验证了单converter、页顺序、聚合2048items与实际输出余额；仅Timeout/ChildFailed允许最后未完成半帧，OutputLimitExceeded不恢复；完成页严格原生成员对齐，异常退出不冒完整；旧成功单JSON /1 /2保持可读且严格校验。

旧CHANGES_REQUESTED报告和76项65P/11F的v4证据保存在 independent-red-review.md/json 与原日志，不冒签新版本。

自有 .pcir28 已按绝对路径边界检查删除，父环境未变，无后台审查进程。产品、既有测试、PWF、生产配置及原件零编辑；网络/模型/Docling/真实PDF均零调用。真实Docling行为、HK来源闭合和最终摘要质量尚未验证。

| 文件 | LF SHA-256 |
| --- | --- |
| `src/company_wiki/source_catalog/narrative_pdf_enhancement.py` | `bb8aff2e74c0b757d8caa17ebe86806d59126dc46ad2d1b590f55504ff174f16` |
| `src/company_wiki/source_catalog/_paragraph_worker.py` | `7ac1c62070273995cfe6b64d4c48a616f5c4ea7dfa6ecb0afa28baf8645b989b` |
| `src/company_wiki/source_catalog/narrative_pdf_page_checkpoints.py` | `c6c697805caf4e18c556ecec4b2ae831ae2955544c340fadbde2ea61404c3f03` |
| `tests/unit/test_pdf_page_checkpoints.py` | `e33796aaa00b0cc4e5d1e1d26501e2ccc674c664beac494bdc279dc211a883fa` |
