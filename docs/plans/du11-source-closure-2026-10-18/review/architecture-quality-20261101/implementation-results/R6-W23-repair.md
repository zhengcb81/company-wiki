# R6 W23 campaign预算/cache根修（新工具独审PASS，待ROOT整合）

当前工程状态：ae438新工具已由独立review_a实际审查PASS，**未合并/推送主线**。经验性比较仍PARTIAL，不接受生产替换或小米模型优胜结论。当前没有重模型调用/下载/原文解析复测。

## 范围与版本

- 作者工区`company-wiki-w23-xiaomi-ocr-r1`始终只读，HEAD `d2f6e6f015cb69b826b499ef56e1ab3d6053fced`。原ledger/comparison/真实run/gold/失败review不写改。
- 自有`C:/Users/郑曾波/Projects/company-wiki/tmp/w23-r6`，branch `codex/architecture-w23-repair-20261101`；正常`--no-checkout`＋精确non-cone sparse＋`read-tree -mu HEAD`初始化，没有完整checkout原件/模型。
- 新runtime本地commit **`ae438a32c942ccc50e9f0fa4d8e9825bd11ca210`**，仅`tools/ocr_comparison/campaign.py`、`cache.py`和专属`tests/integration/test_w23_ocr_r1_transactional_runner.py`。原实验SRC/生产依赖/config未改。
- 另改当前handoff/PWF/工具README以更正scope；历史作者claim保留为historical字段/进度，不伪造76292e3f最终审查。代码raw/LF SHA和保护证据见同名JSON。

## 四个RED的共同根因

原campaign用调用者已读ledger计算余额，最后才记账；异常或死进程中间没有可恢复的预算占用。X1真实分支写cache却从不读，动态remaining又进入模型identity。余额0仍调用runner；JSON允许NaN/Infinity通过比较。因此并不是增加重试就能修好，而是采集结果、预算事务和恢复顺序没有一个责任owner。

新结构继续只用**原单JSON ledger与原ResultCache**：

1. 短OS mutex中重读账、复核cache和已有结果、持久`inflight` reservation，再释放锁调用模型。并发和陈旧快照不能重复分配；同campaign最多一份推理占用。
2. 异常/`os._exit`不撤销占用，不自动续预算或免费重跑。已完成但cache丢失有明确not_run诊断，不能伪造成功或静默再次推理。
3. 成功/失败输出先进入同cache，并写一个小completion marker，才结算ledger。新进程据真实已捕获结果补结算，无第二次runner。cache中只有部分输出而无完整marker则保留unknown，已捕获输出仍能读。
4. X1真实arm先按nominal请求cap＋完整模型/参数/preprocess身份查cache，仅missing页一次batch，避免逐页冷加载。effective remaining-limited deadline在capture/receipt记录，不让动态余额破坏cache命中。R0/fake走同一reservation owner。
5. 0余额仍可读取cache；未跑项逐页保留。known spent、unknown reservation、accounting completeness与execution status显式输出；真实超支不截断账，标partial。
6. finite/nonnegative读写拒NaN/Infinity/bool。旧格式本身不是门：空/完全记账旧ledger可原地迁移；只有观察到无事务证明的零秒真实R0/X1推理才保留资源unknown，禁止不明成本上的新增分配，cache始终可读。不要求签收、不新增许可文件、第二账本或换campaign逃成本。

## 验证与限制

宿主`C:/Miniconda/python.exe -B -X utf8`，`PYTHONPATH=src;.`。新测试在**真实X1F/R0 campaign routing**处stub模型identity与runner，不走仅`X1F-fake`专用路径；用独立新进程、真实kernel mutex和`os._exit`验证。

- 首次新14case：**8F/6P，3.54s**，包含重复推理/无inflight/预算0仍runner/NaN接受；新增恢复接口尚不存在的RED也保留。
- 新事务实现＋原ledger/fake进程短域：26P/7.50s；并发/R0/双快照补反控后31P/10.05s。
- 现有OCR比较器旧回归＋新测试当时29case：**108P/2warnings，93.51s**。这里只做无模型文本/合成转换/元数据测试。
- 最后新增实际overrun不截断、runner NaN保持占用，及测试scratch逐例恢复后：**最终新31P/23.02s，Ruff PASS**。与108域重叠；现110唯一case未在最终单次一起复跑，不累计成139。
- 覆盖cache后/settle前死亡恢复、并发同key、两进程先读同一余额后竞争、原测量时间保留、preprocess变化不复用、预算耗尽cache/miss分母、未知旧成本cache仍读、空/已知旧账迁移、有限资源读写、非合作死亡和R0真实arm。
- 新测试仅自有TemporaryDirectory；逐例恢复并回收独立进程，不复制PDF/模型或全局清TMP。原有fixture/metric测试沿既有tmp范围，不冒称做过全机器临时文件清理。

第一次广域的8个error是sparse缺少旧sample_manifest/gold两个小JSON，只补了这两文件；另1失败是Low沙箱对4字节合成转换hardlink拒写，获准宿主同域绿，converter未改。一条`git sparse-checkout add --no-cone`在本机Git不支持，去掉重复mode参数后继续，没有源码副作用。以上均未当成模型或产品RED。

本地正常commit执行了既有钩子；该基线钩子对tools-only范围均skip，不能冒其为额外测试证据。实际Ruff/测试如上。未执行全unit、付费模型、真实OCR性能或完整原公司链。

## 历史事实不能被新代码洗掉

历史1431.40547是**记录charges**，含1080秒未启页过计，也漏了7个真实R0零秒原调用耗时。144.15秒重测是额外工作，不是原耗时恢复。实际总耗时=null，旧<=1800合规未证；原ledger字节/历史余额不改，不靠净额或新campaignID追认。

旧`review_independent.md`最后是NEEDS_FIXES，未提交与声称76292最终READY绑定的报告。当前handoff将原requirements/limitations等标为historical，另列ROOT当前状态，避免7/8页、no IR-QA等旧词变成当前事实。新代码必须由review_a审实际ae438源码及后续真实修复版本。

作者PNG `r1_wanhua_qa2021_p003.png`仍579,214B，SHA `097eaf47d1da132c80a64dfdd42ca81c72d3b559969ca552b6bc7fb1d00478fc`。这是只读作者工区实验资产，未盲删；已纠正“all PNG deleted”声明。模型缓存未复制/加载/修改。

上段及独审是当时观察；不是永久清理例外。ROOT随后依据原卡，对该已确认生成PNG核对parent/非reparse/PNG魔数/579214B/SHA后精确删除，`R6-W23-derived-cleanup.json`现记录exists_after=false，原PDF/模型/其他cache未动。当前handoff已绑定真实后处理收据；旧review/ledger/comparison不回写。保留source manifest/renderer可按需重渲染，此次不运行。仅删除这一衍生页，不虚报全缓存/物理空间清理。

## 唯一下一步

独审`R6-W23-independent-final.md/json`已绑定ae438和3文件真实raw/LF SHA：原4RED全GREEN，另补marker前死亡反控GREEN（读到真实缓存但保留500秒hold、partial、runner仍1次），选10case全绿4.02s，无实质P1/P2。独审自有tmp/w6已恢复不存在，原作者4artifact raw未变，PNG保持。

作者正常本地提交scope/交接文档后STOP。ROOT整合最新稳定master、在已有architecture候选CI验完整unit再决定并线；不重跑110或原模型来等待。当前handoff绑定这份真实新审查，不追认76292旧READY，不把工具stub绿变成旧实验准确率、生产ready或完整项目完成。

作者收尾：正常本地代码提交ae438后，8份交接/计划文档提交 **`0af261ce2b84f064ec1e7d082b0402005ba79451`**，；后续精确PNG收据文档提交 **`7462a472ef421812228c2271df1e79dd4418c190`** 为当前HEAD。branch为`codex/architecture-w23-repair-20261101`。未push、未合main。自有tracked WIP仅Windows `.githooks/pre-push` mode-only（未提交、已解释），没有遗留源码/测试/handoff修改。最终新测试自有scratch逐例恢复、独审tmp/w6已清；常规ignored pytest/Ruff缓存不冒称全局清理。稀疏工区保留供ROOT集成/候选CI，模型复制0、作者PNG/cache无删改；到此STOP。
