# 完成保证审计的独立有界复核

日期：2026-09-06。审查者：audit_filing（非 assurance-audit.md 作者）。范围仅 A02/A04/A05/CA-206 四组主张、audit_probe.py 及 probe-results-extended.json。状态：完成；结论为“核心技术观察成立，需保留 helper/分类器/生产放行三个层级的边界”。没有修改主报告或任何产品文件。

## 1. 方法与安全边界

- 完整读取主报告、探针脚本/结果；先通过 CodeGraph 获取 classify_unit/run_checks 结构，再读取 uc/revision.py、uc/closure.py、uc/receipt.py、tools/release_gate.py、tools/daily_t2_runner.py 和 tests/test_ca206_soak_window.py 相关代码。
- 审阅 audit_probe.py 后运行 `python -B .../audit_probe.py`：只执行已选择的AST纯函数，任务查询替换为内存stub，没有调用 production main、数据库、网络或真实任务调度。输出与 probe-results-extended.json 一致。
- 额外执行一次内存 receipt→revision→classify 联合负例。使用真实源码函数与真实 canonical hash，只把文件对象换为内存路径；repo_roots=None 明确不检查Git对象存在性。没有创建临时收据、没有state advance。

## 2. 四项复核结果

| 范围 | 独立检查结果 | 可支持的结论 | 不可扩大到 |
|---|---|---|---|
| A02 最新 rejected / machine_valid | 确认。revision.select只对旧accepted存在且latest非accepted增加问题；receipt.validate允许rejected；classify_unit无problems即machine_valid。追加内存联合probe使11/12均真实hash且schema通过，最终selection.verdict=rejected、status=machine_valid、problems=[]。 | 拒绝的review可成为machine_valid证据分类；此分类不足以直接作为accepted/完成门。 | 尚未证明该返回值导致生产state advance、CI批准发布或最终closure变complete。closure_report本身固定old_plan_verdict=incomplete。合法记录一份“拒绝”并不应被receipt格式validator拒绝，问题在消费侧是否把valid错当accepted。 |
| A04 daily T2为SQL代理 | 确认。run_checks真实查catalog，但samples仅completed artifact/event计数；latency只测JOIN LIMIT1 SQL；root fingerprint仅3硬编码目录文件数；manifest只检查对象存在。daily_t2_schedule明确RUNNER指向本模块。 | 生产daily runner没有执行其标题宣称的真实resolver/bundle/p50/p95/三根旅程，是真实接线层缺口。 | 不能称“daily完全没跑”或“没有任何真实数据检查”；它确实查真实数据库并可产出报告。当前SYSTEM Action/触发成功与否仍需独立运行证据。 |
| A05 不完整release仍ready | 确认probe：report.ok=false、commit值not-a-commit/x/y、只有一个任意SLI ok、ledger=None，release_decision返回(true,[ready])。validate_report只有三键集合+自hash，无commit真实性/ok==true门。 | release helper输入合同不完整，不能作为完整发布门；compute_sli默认10指标复制ledger.ok不是业务实测。 | 不能说当前生产发布已经被此缺陷放行。release_gate.main只有publish/ack/status，没有release命令；目标范围搜索未见release_decision实际消费者。daily未采用publish_report不能由helper原子写证明其发布原子性。 |
| CA-206 七个同刻run | 确认。daily_window在测试文件，忽略now，只防最大gap>25h与run_id重复；七不同ID同一时刻返回complete=true。 | 验收测试内的时间oracle没有落实独立自然日；即使生产未接，也说明这套测试不能证明原自然周期要求。 | 不能说生产窗口账本已被伪造或运行了该calculator；当前仅test/helper负例，不是修改历史run。 |

## 3. 审查发现与建议修正

### IR-A01（P2，证据层级措辞）：A02必须保持“分类器有效”与“业务放行”分离

主报告已经写“这不等于本轮改动或调用了state advance”，方向正确；还应说明 `machine_valid` 字面是证据格式/配对分类，而不是已证实的accepted状态。当前联合probe足以证明分类结果，尚无完整state advance/CI消费者复现。

建议A02补句：

> 该负例证明格式与配对有效的 rejected review 仍被 classify_unit 标为 machine_valid；如果后续完成门把这一分类直接当 accepted，将产生假绿。本轮尚未证明 state.advance 或生产CI实际依据该返回值放行。receipt.validate允许rejected本身是合理的历史记录能力，修复应在业务资格/closure消费者层明确要求accepted，而非禁止保存拒绝收据。

建议CA-103表中“CONTRADICTED”旁注明被反证的是“machine_valid可独立证明可接受/完成”的解释；若原单元只要求唯一真实配对，则其配对功能是PARTIAL而非单凭rejected判全项错误，最终按原CA-103验收语义裁决。

### IR-A02（P2，原探针证据完整性）：原A02 fixture只能独立证明select，不应称完整receipt校验链已重放

原audit_probe.py替换canonical_hash为常数h，11/12只有kind/identity等少数字段，无schema/hash/commands；直接拿这些对象跑receipt.validate会失败。因此原结果不能单独证明classify_unit结果。

本次用同一真实receipt.validate、canonical_bytes/hash/sign、revision.select和classify_unit增加内存联合probe，已填补该缺口：

```json
{
  "individual_problems": [[], []],
  "result": {
    "unit": "AUDIT",
    "status": "machine_valid",
    "has_new_schema": true,
    "problems": [],
    "selection": {
      "latest_canonical_hash": "9a01aa5dec01b4d4624e3949bf038066058d6490b419531c2f48f996fc0a7870",
      "implementer": "alice",
      "reviewer": "bob",
      "verdict": "rejected",
      "findings": []
    }
  }
}
```

建议主报告引用本附录联合probe，并保留repo_roots=None/内存文件/未执行state边界。不存在伪造生产收据或实际审查签名：所有sign仅对本次内存synthetic字典做内容hash。

### IR-A03（P2，诊断准确性）：CA-206是错误的测试oracle，不宜当成生产窗口实现缺陷

主报告已经明确“位于测试文件，不是生产汇总”，无须撤回七同刻反例。建议整改计划先确认并建立唯一生产窗口计算入口，再让测试调用生产入口和独立oracle；不要只修测试里的daily_window、继续保留生产未接线状态。保留失败run，不能在选连续链前把not-ok过滤掉；同时规定自然日时区、失败打断、未来时间/复制报告、最晚成功新鲜度和晚到补跑策略。

### IR-A04（P2，发布helper整改顺序）：不要把修好孤立helper写成发布链修好

主报告A05的helper边界正确。整改应先列出真正Daily/Weekly/月度/发布入口与报告consumer，再指定唯一schema、atomic publish、full SLI required set、exact triplet/command/sample/policy绑定。纯helper输入校验绿只是中间检查点；独立agent需要验证实际进程轨迹经过新门、旧弱写报告路径不能旁路。

本次没有发现需要撤销A04/A05/CA206核心技术观察的P1问题；上述P2是证据严谨性、判定措辞和防止未来整改再次只改helper的要求，不是产品修复。

## 4. 不在本复核范围内

未重新审查A01/A03/A06全部CA/ZR账本、所有远端CI历史、真实任务状态、生产catalog或网络T3。没有将本有界review包装为assurance报告全量独立签收。仅本文件为新增写入物，主报告维持原字节。
