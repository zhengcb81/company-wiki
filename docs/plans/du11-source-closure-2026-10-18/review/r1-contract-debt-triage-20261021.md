# R1 / R5 两份 contract 债分诊（2026-10-21）

结论：当前有效执行面实跑 **31 项，27 passed / 4 failed / 0 skipped，pytest exit=1**。两份文件不是各一个失败：boundary 为12通过/3失败，transport 为15通过/1失败。本次只分诊，未修代码、正式测试、配置或安装；未访问并行RF executor目录，未下载或调用外部模型。

代码绑定：HEAD `45195e96cb15a1652b13899a99cfb827932a62f1`；最后代码提交 `76a9440b9a580889460db0b7b545135060f1ce2d`；`src` tree `433e0c872c3ac4e8ea378bff7032cf084b69081f`。`git diff 76a9440b HEAD -- src scripts config tests` 与工作树同范围diff均空。先读AGENTS、CURRENT_STATUS、HANDOFF后按实际结果判断，未沿用旧文档的失败数量/原因。

## 实跑收据

| run | UTC 开始→结束 | 执行面与tmp | 结果 |
|---|---|---|---|
| baseline | 20:59:42.520334→20:59:52.374971 | 普通沙箱；长TEMP被重定位至156字basetemp | 13 passed /18 failed /0 skipped，exit1 |
| short-temp | 21:01:25.531451→21:01:38.201191 | 普通沙箱；58字basetemp，无重定位 | 13 passed /18 failed /0 skipped，exit1 |
| approved-short-temp | 21:04:55.488058→21:06:31.720078 | 经批准执行面；58字basetemp，无重定位 | **27 passed /4 failed /0 skipped，exit1** |

日期均为2026-10-21。三个run均31 collected、0 errors、未timeout。JUnit自身带当地`+01:00`偏移；上述时间取execution.json的真实UTC。完整argv、环境覆盖、每项结果、日志/JUnit SHA-256已嵌入[JSON报告](r1-contract-debt-triage-20261021.json)。本机原始收据位于 `.planning/shared-reading-production/r1-contract-triage-20261021/{baseline,short-temp,approved-short-temp}/`，每轮都有execution.json、stdout.log、stderr.log、junit.xml；不宣称这些本机材料已提交或fresh clone可完整重放。

实际选择固定为：

```text
.venv/Scripts/python.exe -B -m pytest tests/contract/test_automation_store_boundary.py tests/contract/test_narrative_transport_cli.py -q -p no:cacheprovider --basetemp <exclusive-short-tmp>/pytest --junitxml <owned-run>/junit.xml
```

runner命令为 `.venv/Scripts/python.exe -B .planning/shared-reading-production/r1-contract-triage-20261021/run_two_contracts.py <run-name>`。后两轮分别使用独占 `.planning/r1ct21`、`.planning/r1ct22`；ROOT明确认可短tmp环境纠偏。baseline wrapper在写完收据后回显日志触发GBK编码错误，wrapper退出1；这与记录中的pytest退出1分开计算，日志和JUnit完整保留，未据此重写首轮结果。

## 环境噪音与真实 RED

首轮13个transport夹具因长路径报FileNotFoundError，另2个已出现投影retry。短tmp后15个transport夹具统一在`published_fixture:152`返回`retry_scheduled`，未到CLI断言。observer-only探针捕获`NarrativeEffectDispatcher.dispatch_next → NarrativeArtifactStore.prepare → LocalNarrativeObjectStore.put → os.link`的`PermissionError [WinError 5]`。独占28字节合成文件的硬链接探针在普通沙箱失败、批准执行面成功；同31测试经批准复跑后15个setup阻塞全部消失。因此这是执行面限制，**不应修改CAS原子发布来绕过沙箱**。

导入路径明确指向本仓`src/company_wiki`，不存在已证明的旧安装包遮蔽：Python3.14.2、pytest9.1.1、PyMuPDF1.28.2；distribution元数据company-wiki0.1.0不等于本次行为版本。有效轮功能项包括TXT/JSON/PDF/skip原样读取、畸形输入拒绝、未知发布日期/current/historical区分、identity与原字节校验、缺catalog不创建存储，均通过。没有删除失败断言或临时替换CAS实现。

| RED | 根因判断 | 影响与后续修复方向 |
|---|---|---|
| `test_b01_migrations_no_forbidden_tokens` | 旧的无条件token规则过期。`migrations.py:415`的WAL初始化retry有monotonic总deadline5s，sleep上限10ms；当前首先撞`time.sleep`，其后还会撞`while True`。 | 这是有界锁重试，不是常驻daemon。保留retry，精确限定静态例外/边界，并保留既有peer完成、永久锁deadline、nonbusy立即失败的行为测试。不能仅删sleep破坏并发初始化。 |
| `test_b01_store_no_forbidden_tokens` | **实现契约债**。`store.py:699,1376`实际有两处`SELECT *`；`:1396`另有`SELECT j.*`，旧literal规则漏检。 | 保留禁止通配投影的意图，后续改成精确run/paid-reservation字段和明确job列；补alias-star覆盖。不把它归为测试过期。当前未证实数据损坏或运行错误。 |
| `test_b01_store_imports_only_allowed_modules` | 旧白名单未跟上共享identity契约。`store.py:624`导入`company_wiki.narrative_subject.publication_target`；该模块是detached identity验证/命名契约，不持DB、来源物理路径或worker状态。 | 可精确允许该纯契约，或将纯API放入约定契约层，并对齐store旧docstring；不能放开任意company_wiki依赖。未发现越入StockWiki或新网络/LLM依赖。 |
| `test_current_public_producer_regenerates_normalized_txt_golden` | 历史golden被直接要求等于未pin版本的current generator。旧记载的0.8.0/0.4.2其实是**selector**版本，并非parser。 | 当前生成与旧golden有12处路径差异，超过provenance-only refresh许可；应保留历史兼容向量，经语义核对后建立版本化current snapshot。不能仅抹版本/重刷所有hash。 |

边界规则最初针对AUTO-2，后续`cf662cc2e`引入终态压缩，`93ac5a534`明确引入有界WAL让步，`795a076de`引入共享subject发布身份；通配SQL与新恢复逻辑也未同步旧规则。四项没有一个共同的运行时bug；共因是功能和版本演进后，旧静态契约与current/historical快照维护脱节，相关fast contract绿点未覆盖这两文件。SQL通配债仍需真实改实现。

## Golden 的12处差异

仅归一化安装policy hash后，差异包括：parser`0.1.1→0.3.1`、selector`0.4.2→0.8.0`、prompt`1.6.0→1.7.0`；`topics`新增`core_business`，`selection_reasons`两项换序；由此span output SHA、span ID及claim/byte-binding的evidence引用改变。完整逐路径old/new值在JSON，捕获的当前bundle另保存在本机probe目录。

原件SHA/字节、抽取文本、locator、选择数量、summary claim文本未变；这可说明是新生成政策/身份演进，不能证明旧已存bundle读兼容失败。现有`refresh_narrative_transport_golden.py`只允许provenance变化，必须继续拒绝这些标签/身份差异。本任务未运行该writer。后续需明确审查新主题和顺序的正当性、ID变化与版本对应，再选择新的current golden；旧向量保留用于历史读取/回放，不能静默重解释。

## 后续 RED/GREEN 范围

1. RED采用本次批准执行面的四个失败及其完整收据；历史baseline保留为环境诊断，不当作18项产品回归。
2. RF当前执行封存后集中修复静态边界的精确契约、三处SQL通配和version-aware golden。修复后同两文件31项应通过，仍用短tmp且支持硬链接的执行面。
3. 按实际改动附加已有小范围测试：WAL重试既有行为项、terminal receipts unit/integration、paid-recovery字段读取，以及变更涉及的历史parser/replay/版本兼容。**这些附加套件本次未跑**；未跑全量7k、全contract或RF/FF套件，不写成通过/跳过。
4. 沿用既有大节点独审；不新增逐材料许可、canary或常驻门禁。

隔离核对：测试、fixture、conftest均先审读；所有新raw/catalog/AUTO/config为合成tmp数据，golden只读。三个run被检源码、测试、fixture、golden和生产`config/source_catalog.yaml`前后hash一致；当前生产配置SHA-256为`3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`，`git status -- config`空。API密钥从测试子进程剥除、dotenv/network/live LLM禁用；无新费用账或生产预算写入。仅本分诊计划/探针/日志及指定MD/JSON产生新文件。
