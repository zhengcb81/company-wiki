# W11 独立大节点审查

## 结论

**FAIL，暂缓 W11 验收、提交和安装。** 既有 11 条关联测试独立复跑通过，但两个独立控验暴露真实残留。不是用增加人工签收处理；MAIN 应在责任代码内修复并加入聚焦回归，再集中复审一次。

审查者：fresh_native_documents（与 W11 实现者 MAIN 不同）。只读审查 audit 工程，不修改源码、主 PWF、旧执行记录或其他 agent 报告。

实际源码：`C:/Users/郑曾波/Projects/revenue-forecast-audit/skills/revenue-forecast-audit/scripts/audit_run.py`。审查时未提交字节 SHA-256：`0f3c8418a3e4c507dde734bf218c3c2ca16825e4e3f9fb8a2f53023063f0cf77`；行号对应此版本。测试源码：`C:/Users/郑曾波/Projects/revenue-forecast-audit/tests/test_precall_input_history.py`。

## 本次亲自执行的范围

`python -X utf8 -B -m unittest discover -s tests -p test_precall_input_history.py -v`：11 条全部通过。启动关联测试仅传操作系统引导变量与禁用 dotenv/字节码的控制值，不外发凭证或真实资料。另在独占 `audit-w11-review-*` TEMP 运行下列两个控验，保存 exact argv、实际执行 argv、SHA 和观察字段于 `independent_review_receipt.json`，随后恢复 baseline 并删除本次 TEMP。

控验是 `python -X utf8 -B -` 的 stdin 脚本，没有虚构落盘脚本路径；下面给出可直接改写成 unittest 的原代码。真实 RF 四次原生联调仅复读 MAIN 已有 `native_recording.json` / `reproduce_native.py`，本审查未覆盖或改写该 receipt，亦未把合成回放当作整家公司 M3。

## 具体问题

### W11-R1 — P1：输入/输出参数混淆，历史快照可以被覆盖

证据：`freeze_command_inputs` 第453、464行扫描除 executable 外的所有 argv，任何值解析为所选 source path 就作为 input binding；第508行把这些位置全部改成同一个 frozen path。它没有区分读输入的位置与写输出的位置。

实际控验 native argv 为：

```python
native = [sys.executable, "-B", "-c",
    'import pathlib,sys;p=pathlib.Path(sys.argv[1]);assert p.read_bytes();pathlib.Path(sys.argv[3]).write_bytes(b"changed output");print("completed")',
    str(source), "--output", str(source)]
args = AUDIT.parser().parse_args([
    "capture", "--run", str(run), "--role", "executor",
    "--freeze-input", str(source), "--", *native])
observed = AUDIT.capture(args)
```

`source` 是独占 TEMP 的 `原始 输入.json`；原始字节是 `b'{"business_progress":"approved customer trial"}\r\n'`。exact 当次绝对路径和全部 argv 已在 receipt 内保留；这些临时路径现在明确已删除，复跑须新建自己的 TEMP。

观察：

- `recorded_executed_command` 中 input 与 `--output` 值均指向同一个存档文件；child 的读取成功后写输出，覆盖该文件。
- `exit_code=0`，`output_complete=true`，`execution_error=null`。
- `snapshot_matches_pre_call_sha=false`；receipt 内 `snapshot_declared_sha256` 与 `snapshot_actual_after_child_sha256` 不一致。
- 原 draft 仍保持原字节。这不是原件丢失，但**本次应保留的调用前历史丢失**，并改变了 native 输出参数的含义；失败后历史可复现的交付不成立。

需要修复真正的 argument binding / archive ownership。明确哪些 argv 位置消费输入，不能按任意相同路径值盲目重写输出。对于原地修改或输出别名，也要保证本次原始输入历史不会被 child 改掉，或明确拒绝不可保真的调用，不能保持成功和错误 SHA。方案不能通过新增人工许可或把 native 业务预解析一遍来实现。聚焦测试须覆盖读同一输入多次的合法情况，以及输入值同时出现于写输出位置的情况。

### W11-R2 — P2：trust statement 清理异常遮住主失败

证据：`write_trust_statement` 第647行 `os.replace(staged, target)` 若失败，第649行 finally `Path(staged).unlink(...)` 也失败时，后者替换了主异常。此前 InputSnapshotError 的 primary 保留修复仅覆盖 input copy，未覆盖这个本次新增 writer。

实际控验（trust 仍是合法含 unattested/null 的 JSON，目标先有旧声明）：

```python
real_unlink = Path.unlink

def cleanup_fail(path, *args, **kwargs):
    if path.name.startswith(".audit-statement-"):
        raise OSError("CONTROL_SECONDARY_CLEANUP_FAILURE")
    return real_unlink(path, *args, **kwargs)

with patch.object(AUDIT.os, "replace", side_effect=PermissionError("CONTROL_PRIMARY_REPLACE_FAILURE")), \
     patch.object(Path, "unlink", cleanup_fail):
    AUDIT.write_trust_statement(AUDIT.parser().parse_args([
        "trust-statement", "--run", str(run), "--trust-file", str(trust)]))
```

观察：只得到 `CONTROL_SECONDARY_CLEANUP_FAILURE`，`primary_failure_preserved=false`；旧声明保持原样，但原 replace 错误完全丢失，不能定位真正写入失败。修复应让清理结果作为附属诊断，主写入异常继续为 primary；清理仍限 owned scratch，不引入恢复许可或全目录删除。

## 其余检查

| 责任 | 结论与证据 |
|---|---|
| pre-call 原字节及实际 input argv | 一般只读输入正确：先 copy/hash/fsync/rename，再持久 command_started，之后 Popen；修改原 draft 不影响已冻输入。R1 的输出别名使这个保证不完整。 |
| 改 draft / native failure 后历史 | 既有非法 JSON→修正成功测试通过，两次不同字节 SHA 留存；R1 是仍可破坏历史的例外。 |
| 总 cap / 多文件 / Unicode / relative / flag=path | 关联测试通过，max_input_bytes 是 aggregate，不是每个文件倍增；未匹配/不存在/超 cap 不启动 child。输入不做 JSON roundtrip。 |
| native exit / timeout / stdout cap | 非零、启动失败、直接 child timeout 和 output_complete、unknown usage/cost 语义保留。现有终止范围只直接 child，Windows descendants caveat 如实保留。 |
| copy 清理 primary | 既有 cleanup regression 通过；新 trust writer 仍有 R2。 |
| terminal 正文 | capture 返回摘要/产物路径与输入元信息，不重复 retained 正文；之前 stdout 正文泄漏修复已在现源码中。 |
| truth / unknown / unattested | trust-statement 对 <=64KiB JSON 作脱敏投影，保留 null/unattested，返回原 JSON 与输出 SHA；不包装成签名/预测质量保证。非法 trust JSON不覆盖旧声明，测试通过。 |
| 新门禁 / 扫描 | 未引入人工许可、签名、private/public、重复身份判断或全仓配置扫描。runtime 只记录本 recorder 信息和现有 scope 引用。 |
| 旧包和真实研究 | 本审查没有改旧执行、失败历史、MAIN receipt 或真实公司材料。零 provider/付费；M3未审完。 |

## 清理与复审接口

独立控验 baseline restored=true、temporary root absent=true，第二次补充 exact argv 的 TEMP 也恢复不存在。当前 review 的输入/输出原字节仅存于短期 TEMP，已按测试恢复要求删除；小型 SHA/argv/错误观察保留于 receipt，不宣称临时 artifact 可继续打开。

MAIN 先将 R1/R2 写成真实 RED，修责任代码并集中 GREEN 后，交回新的 source SHA、RED/GREEN 和 targeted control 结果。复审只检查这两个残留与被改动接口，不增加小节点人工签收，不要求重复整家公司或付费回放。真实三家公司 M3 与来源/研究质量仍由原整体计划执行。
