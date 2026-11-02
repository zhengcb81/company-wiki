# 两项新残留整改：独立增量审查

**PASS。** ROOT冻结7文件执行前后全部SHA一致，5个真正独立控制全通过，1.461s。没有修改作者源码/测试、PWF或Git；不重复已有54＋33域，也不调用真实供应商/SDK/模型。

## SourceExport v2

使用独立CWP SourceCatalog与SourceVersionReader，实际构造**原文引用本身超过16MiB**的合成UTF8资料并导出，不靠补JSON空白。CWP `from_json`和StockWiki公开`load_bundle`均完整保留正文、原件SHA与字符locator；大wire错bundle hash、重复JSON key和NaN仍拒。两个post-load16MiB门已删除，真实transport资源预算保留；没有换新阈值。

## Paid response

较大非空白UTF8响应在显式相等预算下正常存读；真实预算少1byte，put/read均在对象I/O前拒。等长篡改字节SHA、错object key和坏pin拒；preflight不足不写。

通过真实BudgetedNarrativeCaller及全内存fakeHTTP，独立验证decoder中断→未知费用→新lease；错误request拒且不增请求，随后去掉合成credential，正确request仍可从原bytes恢复并结算92tokens，始终1request/1reservation。与ROOT较大loopback1POST证据分开记录，不冒称本审重复跑过大响应真实网络恢复。

## 历史与清理

首个探针脚本误用不存在的`to_json`，0case执行的ERROR原日志保留；仅把自有探针改为实际`to_dict`JSON编码后5项一次全绿，未改产品掩错。此前跨仓报告不覆盖这些新增CWP/StockWiki项，本报告明确其后发现与修复，不回写旧历史。

精确7SHA、原始日志、独立探针源码及临时资料清理收据在同名JSON。自有合成原件/目录及两份自有日志归档后精确删除，仅保留指定两报告。仍待ROOT正常提交发布与精确CI；真实C和公司loop不在本次验收。
