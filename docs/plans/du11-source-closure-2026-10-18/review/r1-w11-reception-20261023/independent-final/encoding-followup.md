# W11 编码风险有限补审：通过

本次绑定 `official_discovery.py` raw SHA **`6869349b5d6f4861e9c78cdc8748aaa7f547d2866cf278fc5f721418a137b123`**，正式unit raw SHA `506ad107b01bef410ecbea297e8d8a89ccb230db3de591ce15dfe1123af754c8`；其他四份源码/测试保持前轮版本。全部六文件raw/LF SHA见encoding-followup.json与encoding-followup-receipt.json。

用实际触发发布检查差异的 **Conda Python3.13.9**，执行原同字节37项：**37P / 0F / 0E / 0skip，7.36秒**。pytest与四个公共CLI子进程都记录母仓实际import。未重跑132项、全仓或其他套件，未修改原37断言或旧FAIL/PASS报告。

另对**本次已报告的确切短UTF8输入** `<main><div>Loading…</div></main>` 做一次直接重现，不扩展一般测试矩阵。Conda真实运行输出确认：共享decoder选择utf8_strict、无repair，页面保持dynamic_content_unresolved/partial。该probe有完整小源码与实际JSON，单独列证据，不加进37项pytest计数。

## 共享根修核对

CodeGraph先定位并读取既有 `document_normalization.html_parser.decode_html_bytes`。Discovery直接导入同一函数，先解码actual original bytes，再将Unicode交给BeautifulSoup；直接probe也核验函数对象身份。只有这一既有decoder，不增加公司、域名、mojibake词表或第二编码猜测器。

既有策略依次为BOM、声明charset、UTF8 strict，再windows1252 fallback/replace；无法严格使用前述编码时返回repaired=True。Discovery收到repair即记录index_encoding_repaired，沿原limitations机制保留partial；raw page hash仍由original bytes计算，不拿解码后文本冒充源字节。静态核对正式新增编码正控覆盖UTF8中文、声明gb18030、声明windows1252与UTF16 BOM，fallback另有诚实性回归；这些5项是ROOT已运行结果，本独审没有另跑或合并为独立通过数。

六个当前源码/测试在本轮前后及特定probe后SHA不变，六个预算/narrative/配置保护文件与初轮完全相同。原initialFAIL与前轮finalPASS所列artifact全部重新核SHA一致。旧PASS只绑定旧版本，本补审绑定本次新源码；不回写旧证据。

专属scratch仍初始不存在、测试后删除恢复不存在；特定probe只读产品并写本目录新证据，没有新tmp。所有测试进程包含CLI子进程通过内置sitecustomize禁dotenv、去除密钥环境变量并阻断socket/DNS（含loopback）；probe同样禁网。0外部HTTP/模型/下载、0原件读取、0作者工区/生产配置/Git索引修改。仅新增encoding-followup*文件，未改已提交报告。

复现（母仓PowerShell；历史产物先保留到独立报告位置，避免覆盖）：

```powershell
& 'C:/Miniconda/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w11-reception-20261023/independent-final/encoding-followup-run.py'
& 'C:/Miniconda/python.exe' -X utf8 -B 'docs/plans/du11-source-closure-2026-10-18/review/r1-w11-reception-20261023/independent-final/encoding-followup-probe.py.txt'
```

Runner源码另有.py.txt，网络fixture内置于runner，原test_neutral_review.py及其持久txt副本已保留。精确原始命令、真实JUnit/输出、模块路径与cleanup见本轮receipt。报告不代替ROOT随后正常pre-push，也不宣称真实IR原件或公司研究通过。
