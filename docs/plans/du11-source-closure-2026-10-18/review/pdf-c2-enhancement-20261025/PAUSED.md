# PDF-C2 暂停交接

## 2026-10-25 用户明确暂停（本段为唯一当前状态）

已停止代码实施。PDF-C2主体代码`f13de801`已正常提交并推送master；正常pre-commit及pre-push154项通过。段落分诊、严格成员对齐、按需增强及actual观察持久化已实现，真实HK缺口已改善。最终源码/测试独审F1–F5 PASS/0 OPEN；**随后ROOT补查发现新的Linux类型检查问题尚未修复，发布不能记完成或CI全绿。**

未完成项：`_paragraph_worker.py:51`使用`ctypes.WinDLL`，本机`mypy --platform linux`报告attr-defined；Windows完整检查通过，说明是平台类型接口差异，不是财报内容错误。拟按现有`cast(Any, ctypes).WinDLL`惯例修复一行；用户暂停后没有改源码、没有继续测试或重跑模型。下一次先修这里、核精确CI，再进入C3。详见[暂停交接](review/pdf-c2-enhancement-20261025/PAUSED.md)。

真实三源五页旧同组口径6/8→7/8；独立事实v2为8/9→9/9，不能合并两个口径。整份HK自然12/13/17页实际81.10秒，120秒cap内通过，单converter三页；提交内存峰值约3.10GiB，已根修误把RSS作为Job提交限额的配置依据。229集中、最后34新短测、36观察恢复检查及源回放已绿（重叠不相加）；原件/config/catalog不变，临时根恢复，0付费/下载/原件副本。

**恢复后唯一下一步：** 修Linux类型接口窄接缝→Linux完整mypy与正常hooks→独审补充绑定→提交推送/精确CI→正式摘要/语义/cache/RF。默认原生、增强显式配置；跨文档热池、新US PDF/扫描件盲测、typed经营表及C3没有代签。下方旧“当前/下一步”是历史快照，不能覆盖本暂停。无关hook模式WIP、W19/作者工区、RF WIP、Dayu/IQS和原件保持。

## 不重复做

不重做C1、H1/DOCX根修、五页选型比较或81秒冷启。f13de801是已推送源码；仅Linux类型窄修待做，不要把它误判成内容召回失败。

## 审查快照

独审报告和原README保持审查时字节，不改成新通过。独审0 OPEN仅覆盖当时F1–F5；ROOT随后发现的Linux发布问题另列。本目录失败JSON收据保留，重复失败gzip删除已记SHA，无原件删除。
