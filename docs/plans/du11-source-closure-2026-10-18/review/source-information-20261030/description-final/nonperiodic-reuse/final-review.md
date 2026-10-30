# M1 非期次原件 provenance 工程大节点独立终审

结论：**本次六路径工程范围 0 OPEN**。已冻结独立25项纯合成测试，最终 **25 passed / 0.47s**；未将工程合成通过写成真实原件准备、摘要完整或预测采用成功。

绑定文件与raw/LF SHA-256见 `final-seal.json`。对象为RF工作树六路径：`scripts/contracts/company_wiki_original.py`、`scripts/contracts/source_provenance.py`、`scripts/contracts/document.py`、`scripts/contracts/evidence.py`、`scripts/company_wiki_source_v2.py`、`tests/test_source_provenance.py`。审查不改产品，所有独立测试/收据仅写ROOT本目录。RF预存assurance/runs三项hash与baseline逐字一致。

## 共因修复验收

- 初版 `12 failed / 1 passed` 揭示HTTP URL错误从Collector收集回归成直接抛出；null provenance仅部分字段绑定，放行缺kind、annual缺FY、坏period_end、原始采集时间矛盾、坏read receipt与不相干capture工具/host动作。
- 重构为单一 `contracts.company_wiki_original` 纯DTO owner后，准备adapter与最终source evidence复用同一Ref/receipt/manifest字段、period/time语义。当前无文件IO、provider发现、身份刷新、人工许可或forecast计算依赖；document → provenance → original/evidence/source_clock的导入方向无环。legacy opaque document ID保留，未新设document ID摘要必须等于原件SHA的要求。
- 独立补充的Collector缺capture/host字段、optional signature半对，以及fiscal_period类型/trim负对照进一步揭示结构安全短路问题。ROOT在已有evidence字段检查处解决，未复制第二份capture字段表；字段缺失/签名半对在collect模式记录后return，source capture在host已失败时不再依赖其字段。fiscal_period使用一般optional trimmed text，未加行业或文种专用枚举。
- 最终冻结25项全部通过。ROOT将manifest/period/time/receipt/capture及Collector全缺字段循环/签名半对等反例纳入RF永久 `test_source_provenance.py`，不只保留在独立审查包。

## 最终边界判断

`valid_source_url` 保持公开HTTP URL验证含义。有非空invalid URL时不能降级成local路径；仅显式`url=None`允许完整CWP原件追溯，始终要求capture，即使`require_capture=False`。Missing URL不等于null。准备时仍验真实bytes/SHA/size，最终source evidence验证版本化DTO与捕获链，不再次外部IO。

unknown published仍走既有exact-SHA SourceReader2.2 availability lineage；已知future publication、晚于cutoff availability、当前open冒充旧cutoff、original retrieval/read矛盾均不能通行。非期次FY=None允许，periodic FY仍必需；原件URL、FY、publication未被制造。现有read2.1/2.2精确字段集未扩大为未知版本吞入；未来metadata增字段需按已有版本协议显式演进，消费者不静默接受。

Collector下public provenance wrapper保留require语义；结构失败在私有纯规则短路，不继续访问坏对象。旧HTTP默认不额外要求capture，原有有capture路径保持其含义。新null路径对tool、issuer、action、timestamp、source/capture/manifest/ref/receipt hash及policy字段作绑定，未新增签名强制或人工签收。

## 验证记录与限制

复现命令（ROOT cwd，`-B`、无pytest cache、独立config、`--noconftest`，不加载ROOT自动夹具）：

```text
.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --noconftest -c .planning/summary-quality-20261030/nonperiodic-independent/pytest.ini .planning/summary-quality-20261030/nonperiodic-independent/test_independent_provenance.py --junitxml=.planning/summary-quality-20261030/nonperiodic-independent/final-junit.xml
```

真实日志 `final-tests.log` / `final-junit.xml`。初版与中间失败保留 `initial-result.json`、`recheck.log`、`recheck2.log`、`signature-shape.log`，未覆盖成全绿历史。最终seal同时核对RF预存WIP三项，全部unchanged。

执行仅合成BODY、纯合同/adapter和既有测试数据；未运行作者采集/预测脚本，未启动provider、下载或模型POST，未解析真实PDF。原临时湖恢复、CWP真实public只读open、narrative reference/read、SourceCapture以及实际forecast claim→used parameter→formula采用仍由后续独立验收完成。已有6/8摘要覆盖/语义问题不因本节点关闭。

## 正常发布前测试中性修正复核

pre-commit正确要求bootstrap后的测试导入有E402显式标注，并阻止负对照夹具内的固定宿主路径。当前仅永久测试文件增加精确`# noqa: E402`，将两个固定路径负对照改为`tmp_path / original.pdf`和`tmp_path / source.pdf`；原拒绝断言、参数数量和产品规则保持。独立冻结25项再次执行：**25 passed / 0.53s**，日志 `publication-tests.log` / `publication-junit.xml`，未扩大测试范围。

新六路径seal为 `publication-seal.json`；其中生产五路径raw/LF均与终审`final-seal.json`完全相同，测试文件更新已复核。发布工具对预存`assurance/runs/weekly_manifest.json`发生CRLF→LF归一化：原364B SHA `44e46cd57e5373803fbdaa5dff5e93041840b8e8cc671e710e0346a133c4df97`，当前353B SHA `4098f5a347b3dbb882d656712021eb407dfd9cfe9fbe12285957dafabff4ee9b`。独立只读转换回CRLF后hash等于baseline，确认内容相同；daily/weekly_alert raw仍相同。这是ROOT确认的pre-commit stash/restore工具副作用，未stage，不计产品工程OPEN；原字节恢复由ROOT在正常commit/push后另补保护收据，本次不伪称当前raw完全未变。

另核对ROOT `real-registered-ir-v2/receipt.json`：其限定范围报告真实IR owner byte open + RF source input validation PASS，未知元数据保留、download/POST/raw copy为0、临时湖删除。该收据不包括narrative或forecast adoption；本审查没有自行重跑真实样本。
