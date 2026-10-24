# W11 一次实际索引恢复结果（2026-10-24）

**索引原文已正式入库、通过SourceRef读回校验；IR/deck/Q&A业务文档仍未获取。** 本节点按授权只抓一个官方index，未跟随材料链接，没有重试或第二次GET。

## 实际结果与新版本

- URL：`https://www.wuxiapptec.cn/investors/announcement/ir-material`。
- HTTP200，2026-10-24T00:00:35.396122至00:00:37.938228Z；`http_requests=1`、`download_events=1`。响应与wire均 **486901B**、usage_complete=true、content_encoding=identity。
- 新SHA：`5f9455a50d1853692211ecfa0b0a057fc30191af9247fd8bbecab8c24d158006`；正式source_id为`urn:company-wiki:source:sha256:5f9455a50d1853692211ecfa0b0a057fc30191af9247fd8bbecab8c24d158006`。来源结果`imported_new`、SourceRef2.0、text/html。
- 此为新抓版本，**不是**旧486789B/SHAf1e822a8…正文的历史重放。旧缺失与封存证据不改写。SourceRef的published_date/FY/period_end仍null，language unknown；抓取时间没有补成发布日期。历史研究窗口保持2026-01-01至2026-10-21。
- 实际HTML标题：**财务报告和演示材料｜药明康德**；canonical请求描述标题单独保留，不把它当正文核验结论。

官方`capture`成功后，执行public `read`二进制落入独占工作副本，size/SHA完全匹配Reference；只对该真字节运行public `discover pages`。后按ROOT补充指令仅再做一次同SourceRef本地binary read到内存，0GET、无新大副本。

发现原结果逐字保留：`coverage_status=checked_index_only`，`candidates=[]`，`limitations=[]`，`no_documents_claimed=false`；这里仅签当前索引检查范围，没有改成全部材料已找全或无文档。

## 为什么0业务lead

新HTML有可读正文，排除chrome/script后的主体417字符，包含真实栏目文字：

- 2026/08/03：2026年中期业绩，演示材料、财务报告、摘要。
- 2026/04/27：2026年第一季度业绩，演示材料、财务报告。
- 2026/01/14：第44届摩根大通医疗健康年会，演示材料。

但实际34个`a[href]`中，5个文档后缀锚全部是3个不同的隐私/条款PDF，其余为导航、地区、分页等；业务材料标签没有出现在可消费的业务材料锚中。当前发现owner扫描真实锚且排除这些法律链接，因此返回0。没有把页面说成空壳，也没有仅因含外部script就推断解析失败。

脚本MIME实数：unspecified5、application/ld+json2、module1、application/json1。两个JSON-LD是Corporation/ContactPoint与BreadcrumbList/ListItem，未声明材料；`__NUXT_DATA__`为29663B JSON、548项索引数组，本地有界观察2193节点，含attachment/link等索引引用。实见literal PDF URL仅terms/privacy。没有执行JS、解码并猜配Nuxt引用、请求bundle/API或捏造材料URL。

**因此材料获取仍为external_limit/未闭环：这次静态响应没有给出可直接交给现有锚点发现器的业务URL。** 这不证明客户端交互后的真实目标不存在。后续若ROOT继续，可用现有浏览器工具对真实DOM/点击目标做另一次有界观察，再把实际目标交CWP；本次未验证某份材料可公开直取，未启动后续网络或新provider。

## 精确代码与执行证据

实际官方owner前后字节一致：discovery `6869349b5d6f4861e9c78cdc8748aaa7f547d2866cf278fc5f721418a137b123`、CLI `bdd06d5728dc25ef9a7433e5d7c1c89534f3fa52b9dd6e15ce7867e40d9c6162`、source_flow `3c4640201f9a1f70b4ce41a51d752f3f8fb5d048eb28f1296658298d2cf714c9`。真实子进程模块路径均来自母src，Python3.14.2；调用argv、请求SHA、stdio、时间/exit与SourceRef全在新attempt。

只读reflog推得执行起止HEAD均`b0344200a3efe15ef18cb551c5d6a276b1d7fe28`。调用前未独立采样whole-tree dirty；ROOT同时处理无关W08合并/hook，事后dirty观察已如实保存。**不把该HEAD或旧1be/a837当作所有工作树源码的精确版本**，本节点用实际官方owner文件SHA绑定。未改Git。

三原始请求SHA：capture `81e558914dd1e18f69f10e52c077ac0aaa535bf820ed8654a087def578f78fa7`；read `a974cfd7d83bd35665a463ce50a363925c9a73cb3c56d135a040320bf12f3ba7`；pages discover `55c15be84407830e8f4648d682ca06c9c594edad407dbd2f03722f29b137c924`。三调用exit0；额外本地read同样exit0且486901B/SHA相同。Capture阶段允许唯一真实HTTP；read/discover/复查阶段显式阻断socket/DNS。

完整细节目录：`C:\Users\郑曾波\Projects\revenue-forecast-audit\runs\r1-20261021-cn-wuxi-apptec\execution_replays\r1-remediation-02\w11-actual-20261024`，主要入口operation.json；实际capture/discovery/local-inspection、before/after/runtime、final-validation及cleanup均在receipts/。此次自有细节在最终manifest前68491B，未保留重复大HTML。

## 费用与恢复

硬限1MiB/20s/0新增provider费、自动重试0。实际获取**1个index，0个业务文件**；原生acquisition cost=0，模型调用/token/费用增量均0。母usage.jsonl与metadata.json逐字节SHA前后不变，原unknown未释放。

正规storage新建486901B HTML与3260B source sidecar并更新既有隔离catalog；全部预存raw的size/mtime不变。旧封存manifest/index、配置、官方owner源码前后哈希不变；initial639/final3/author未写。母源码、PWF、Git、安装、RF均未操作。

仅删已校验的工作副本work/ir-index.html及空work目录，精确路径与SHA/size留cleanup；正式raw和必要诊断均保留。旧本地pages请求里的工作路径现不存在，ROOT可用保留的requests/read-index.json经public read以二进制stdout再生同一SourceRef字节，重新核SHA即可回放。**下一步未自动执行，本worker至此停写交ROOT。**
