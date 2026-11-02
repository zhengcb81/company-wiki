# W23 ROOT修复新版独审 — 工具工程PASS，经验资料仍PARTIAL

**结论：`ae438a32` 的本次工具工程范围 PASS，未发现实质P1/P2。** 可以由ROOT整合此工具修复与真实交接记录；只接收旧试验的限定PARTIAL资料，不签小米准确率优胜、生产OCR替换、内存cap已解决或整个项目完成。

审查对象 `C:/Users/郑曾波/Projects/company-wiki/tmp/w23-r6`，runtime commit **`ae438a32c942ccc50e9f0fa4d8e9825bd11ca210`**。开始分支 `codex/w23-root-repair-20261101` 后由ROOT正常改名为 **`codex/architecture-w23-repair-20261101`**，runtime不变。作者仍在收口handoff/PWF文档，未修改这3份runtime/test文件。审查者 `/root/rectification_review_a` 未参与本修复实现，也没有改工区、Git、生产配置/源码或原作者资产。

同名JSON绑定两工具＋新integration测试的raw/LF SHA，**3/3与作者收据及ae438提交字节吻合**；测试后runtime未变。开始误找tests/unit，随后按实际提交确认新测试在tests/integration，不属于产品错误。

## 原四个真实路径RED独立重放

沿首轮 `R6-W23-intake.json` 的独立探针，从新工区加载真实campaign/cache/runner模块。仅显式stub模型身份与真实X1 runner seam，**不使用X1F-fake分支**；每次恢复是独立新进程，使用真实OS mutex与磁盘文件，没有模型/原件/下载/费用。

| 原缺陷 | 新版独立结果 |
|---|---|
| 同页新进程恢复重复推理/重复扣费 | runner共 **1次**；spent **1→1**；第二次cache_hit=True，原测量仍在。 |
| 已开始runner异常后无持久占用 | 异常后spent=0，但**500秒inflight已落盘**、可用余额0；新进程不再调用runner、不释放未知占用。不能把spent=0误读成免费恢复。 |
| 余额0仍进入runner并抛错 | runner **0次**，完整请求页返回not_run。必要身份观察不等于模型推理，本例没有宣称跳过所有身份IO。 |
| NaN账本可以提供额度 | load_ledger明确LedgerCorrupt，不提供request预算。 |

**4/4 GREEN。** 探针源码、逐进程结果与账本收据全文保存在JSON，不靠作者测试自签替代。

## 新增独立死亡窗口反控

作者新测试已覆盖“cache completion marker写完，ledger settle前死亡”。独审另补“**页输出已写cache，completion marker尚未写时立即os._exit(29)**”：

- 第一进程退出29；第二进程复用实际已捕获输出，cache_hit=True；
- runner累计仍1次，**500秒占用不退款**，inflight仍1，可用余额0；
- accounting_complete=False、execution_status=partial。

该结果同时保留原文输出的可读性和未知费用边界，既不重复推理，也不把缺完成证据的结果虚报为完整成功。**1/1 GREEN。** 故此次独立自有探针合计5项，不是新增模型试验。

## 选取作者10个新case独立执行

正常获准host `C:/Miniconda/python.exe -B -X utf8`，**10P/4.02s**，JUnit全文/逐例清单在JSON：

1. R0同事务路径跨进程cache命中、原测量不变；
2. R0非合作死亡后保留占用，不免费重试；
3. 输出与completion marker落盘、settle前死亡，新进程补结算且不重推；
4. 余额0仍能读取X1已有cache；
5. 并发同key仅一个真实runner；
6. 两进程先读同一旧余额后竞争，只有一个0.75秒写入成功；
7. 实测超支2秒不被预算1秒截断，真实记录2、partial且余额0；
8. runner返回NaN计量，异常后保留durable hold，不能续跑；
9. 有完整已知费用的旧ledger可原地迁移、不重置预算；
10. 旧真实费用未知时已有cache仍能读取，但会计状态继续partial。

没有重跑作者31/110全包。作者“108域含当时29新例，之后补2例最终新31P”的重叠范围保留，不累计冒称139个唯一case或最终110已在同次实跑。

## 架构、事务和失败边界判断

- **同一责任owner**：仍为单JSON ledger＋原ResultCache，没有第二任务库/审批文件/campaignID续期。短OS mutex内重读当前账、检查已有cache与pending、写入reservation后才允许runner；推理在锁外，stale调用者的ledger参数不能控制分配。
- **真实路径接线**：X1先按稳定nominal请求cap与实际模型/参数/预处理/代码身份取cache，只有missing页进一次batch；实际余额限制后的deadline进入capture/receipt，不再污染稳定cache身份。R0/fake复用同一事务流程，而非只给测试fake加特权通道。
- **恢复顺序**：输出→同cache completion marker→ledger settle。新进程只有在marker与对应输出都存在、reservation与页/key对齐时补结算；缺marker的占用不退款，已捕获输出仍可返回partial。已结算但cache遗失会明确not_run，不静默再次推理。
- **资源真值**：finite检查覆盖创建/加载/写入、runner时长及wall；异常或原生死亡保留hold。已观察超支照实入账并报partial，不用min(remaining,elapsed)洗掉成本。余额为0可取cache、miss保留分母。
- **legacy不是许可门**：缺新inflight字段本身不会拒绝旧账；空/有完整费用旧账可安全原地继续。限制仅来自实际记录中“无事务费用证明的零秒真实R0/X1执行”所造成的未知资源，不要求人工签收；已有cache先读。原7个未知R0首跑不能凭“格式升级”获得新余额。

本轮没有发现按公司、材料或旧字段重新加人工门禁。真实执行仍须遵守既有字节/时间/费用限额；工具stub工程绿不是放大额度或生产模型验收。

## 历史资料与文档收口

原作者工区 `company-wiki-w23-xiaomi-ocr-r1` 始终只读。4份受保护历史artifact的**原作者raw SHA全部未变**：ledger、comparison.json/md、旧review。修复工区前三份字节相同；旧review副本只因正常checkout的CRLF比原件多157B，规范化换行后完全相同，Git未改该文件；这是checkout表示差异，不是补造审查历史。

- 历史 **1431.40547是recorded charges**，含1080秒未开始页过计，同时漏了7个真实R0首跑耗时；144.15秒重测是额外工作。**actual_total_elapsed=null，旧1800秒合规未证**。不净额抵消、不新建campaign洗历史、不再跑模型追认耗时。
- 旧review最后仍NEEDS_FIXES，未留存的“76292最终READY”仅保留为historical author claim，不能当有效审查。本报告是对ae438新工具的真正新独审，必须独立绑定，不改写旧FAIL。
- 当前handoff已把原requirements/limitations移至historical_author字段，另列新工具与旧经验的不同scope，旧7页/no-IR-QA等文字不再冒充当前8页事实。ROOT current review字段应在接收本报告后绑定实际runtime/source和报告路径，再正常提交文档；不能用pending字段充当已经发布。
- 观察到的QA PNG仍579,214B，SHA `097eaf47d1da132c80a64dfdd42ca81c72d3b559969ca552b6bc7fb1d00478fc`，保持原样；已纠正“全部PNG删除”。本轮没有删除作者资产、复制/加载模型缓存。
- 独审提出的一个措辞小项已修：当前控制为**1/4 formulas fully faithful、6/10 symbols**；历史作者原文保留。它不构成小米模型质量结论。

## 清理与发布界限

全部测试新材料只在 `C:/Users/郑曾波/Projects/company-wiki/tmp/w6`，短basetemp43、无重定位；完成后恢复最初不存在。复现程序、原四例/独立反控与JUnit以文本嵌JSON，临时页/账/输出/源码副本未遗留。修复工区的文档仍由作者收尾提交；本审查没有替作者commit、push或并线。

**工具工程PASS，STOP。** ROOT可整合此runtime与真实scope文档。旧经验资料维持PARTIAL；Job Object cap/peak不一致、真实小米质量/生产适用性、整候选CI及主线H1/真实摘要/持久恢复/RF采用均未在本报告获得通过。
