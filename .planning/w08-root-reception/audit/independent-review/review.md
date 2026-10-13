# W08-AUDIT-EVIDENCE 独立只读接收审查

2026-10-13；作者工区 `C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence`，交付 HEAD `96889c6`，base `2c494913`。

## 结论

作者交付已实现可选实读层、旧 CLI 兼容、supplied SHA 比较、缺 SHA 诊断、未知 PDF/tool-call 不冒充可验证，以及输出经济质量不评估。这些范围正确。**并线前需要集中修复三类真实行为缺口：执行绑定、数字覆盖计数、资源 envelope。** 不需增设人签、许可或新的来源身份验证。

只读原文件，零 provider/LLM；未改作者/生产文件，也未碰 DU 外包目录。`python -B` 运行作者 40 focused 单元行为测试，全部通过（5.660 秒）。另外 `reproduce.py` 在本报告目录下创建独占 TemporaryDirectory，逐案生成合法小包并清理；真实实测回执在 `reproduction.json`。报告里短路径均指作者工区。回执出现的临时源路径已经恢复不存在，不表示留存了那些原始测试文件。

## 必须修复的问题及最小测试

### 1. 执行绑定只有数量，当前报告只打开字节（P1）

位置：`skills/revenue-forecast-audit/scripts/review_evidence.py:517-559`，`review_evidence_reconcile.py:162-191,257-268`。

真实复现：storage `command_started` 的 capture_id 为 A，`command_finished` 为 B，总数各一；仍 `unchecked=[]`。把该 role 文件里的 event.role 全部改成 analyst，同样未核查为空。把当前位置 `reports/attempt-1/storage.json` 内容写成 run_id=old-run、role=analyst、review_attempt=old-attempt，仍 json_status=OBSERVED，没有报告身份 mismatch。当前 report bytes 虽被打开，coverage payload 与实际磁盘报告没有对照；事件也没有与各行/输出引用对应。

影响：工具声称核对本轮报告和实际已知事件字段，但旧报告内容、另一角色事件和不相配的调用都可得到干净绑定诊断。旧 `check_coverage(payload)` 不能消除此缺口，因为它只读声明 payload。

必要修复：保持 byte-open 和 resolved/bound 的区别；读已打开报告 JSON 的已有 run_id/role，显式存在的 review_attempt 对比本轮值；未知/缺字段只诊断。按真实 capture_id/call_id 对 starts/finishes 配对，角色/run不一致列 mismatch，缺 ID 保留 unknown；不要把 started/finished 总数相等视为匹配。对显式声明的输出 artifact/call 引用记录实际关联/未核查，不能推断每个打开文件都由 reviewer 读取或由该调用生成。可复用 `audit_run.parse_event_observation` 的既有 canonical/legacy 身份语义，不再新增身份解析器。

最小测试：A开始B结束、错误 role/旧 run 的事件、当前目录内旧报告 JSON、合法同 ID start/finish、finished-only/未知ID保持诊断、显式输出引用不存在。全部只影响 additive diagnostics/unchecked；旧 CLI 和 records_complete 的结构语义保持。

### 2. 已打开文件被当成数字位置已解析，重复位置覆盖计数膨胀（P1）

位置：`review_evidence.py:460-464`，`review_evidence_reconcile.py:199-246`。

真实复现：V1.recompute.locator=`invented result paragraph`，行有明确 `matrix_status=null` 和 free-text 未解析理由，但 numeric `recompute_rows_observed=3`、`unresolved_recompute_value_ids=[]`。V2复制V1的同一文件/同一pointer，仍3行被计为已覆盖且没有重复引用诊断。作者 `test_identical_reference_under_two_value_ids_only_covers_one_locator` 自己断言3行OBSERVED，同时文档称相同引用不会增加覆盖；现有测试冻结了此矛盾。

必要修复：普通 free-text 文件可以保留 byte OBSERVED，numeric 只把实际 pointer/行范围已解析项计入已定位计数，未解析 value_id必须留诊断。保留已解析目标的类型以及真实数值/显式计算表达式可观察性，不能把任意元数据字符串pointer存在说成numeric复算已核对；不在本工具重算表达式。对 resolved artifact + canonical locator 统计唯一位置并报告重复 value_id映射，原始声明条数另列。一个大对象可能真实包含多个计算值，不因共享对象引用阻断；如果仍保留 per-value 已打开行计数，需要另列 unique resolved reference count并修改命名/说明，避免把它当独立覆盖证明。此工具仍不重算预测、不判经济真值。

最小测试：free-text复算不计已定位；两个不同 value_id 同一规范化引用不增加唯一位置计数；不同pointer正常计数；缺SHA正常、坏pointer降计数。对 broad object共享引用只诊断，不能伪造数字独立复算。

### 3. 限额规格没有兑现，stat 后全量读取突破字节上限（P1/P2）

位置：`review_evidence.py:105-116,267-291`。

真实复现：normalize_limits 接受 max_seconds=NaN、Infinity，max_files=999999，max_files=0.5 后截成0。这与 reference “只可收紧、非法值报错”不符，NaN令时间比较恒不满足。确定性增长夹具：stat=1字节，随后真实文件扩成40字节；max_file_bytes=4、max_total_bytes=8却读取40字节、error=null、budget.exhausted=null。此夹具显式控制增长间隙，证明读取算法无硬 byte bound；没有声称已观察生产文件增长事故。

必要修复：有限且为正的 seconds，计数/字节/行/token必须正整数；按已约定只收紧规则拒绝超默认值。读取最多 min(单文件上限,剩余总量)+1 字节，以额外1字节判溢出，实际字节如实计账；溢出时不返回完整SHA/已解析，重新检查 deadline。不要仅事后 len(body) 验证，因为峰值读取早已发生。每次读取仍使用原有一个 Budget。

最小测试：NaN/Inf/小数计数/超默认值报错；增长文件或bounded file-like证明 read请求长度有界；limit+1 不记完整OBSERVED；精确边界可读；后续资源拒绝不冒充不存在；时间超限未知仍可生成诊断报告。

## 额外观察和未成立的问题

`max_pointer_tokens` 可配置但实际委托固定128 tokens的 `audit_contracts.resolve_json_pointer`，下调值未接线；可删除无效配置或在委托前限制，不必扩造第二引擎。

`_run_metadata` 和 `load_events` 直接调用 read_bytes，未走 reader.resolve；普通文件路径在显式根内，但 symlink/reparse逃逸缺少与evidence一致的解析检查。这是静态代码观察，**没有在本机复现外部链接读取**；建议共享一个resolve入口，避免加权限库。

尝试1500层JSON，当前Python成功解析，未复现递归崩溃，因此不报为实际缺陷。峰值内存、真实公司审查、真实 agent 独立性、原件内容真值/预测经济合理性本次均未评估；作者边界说明是诚实的。

ROOT可在独立接收工区一次集中修复并运行上述反例和原40测试，然后原 C 节点离线 E2E；无需增加逐小节点审查。原包本身符合安装/生产隔离要求，但三类合同缺口修复前不应签全量接收。

## 反例输入与断言定位

全部通过 `python -B .planning/w08-root-reception/audit/independent-review/reproduce.py` 生成 `reproduction.json`，没有真实公司输入。脚本 `sample()` 使用作者 PackageBuilder 的固定合法夹具后仅改变单因素：

| case | 最小输入改变 | 预期断言 | 作者实际 |
|---|---|---|---|
| mismatched_capture_ids | `roles/storage/events.jsonl` 第二行 `data.capture_id=other-capture` | storage 未匹配开始/结束各1，unchecked含未匹配调用 | started=1 finished=1 unchecked=[] |
| wrong_role_events | 同文件两行 `role=analyst` | storage binding中无合格storage事件，错误角色诊断 | storage started/finished仍各1，无unchecked |
| stale_current_report_contents | `reports/attempt-1/storage.json` 改 `run_id=old-run,role=analyst,review_attempt=old-attempt` | 实际已知字段mismatch | json_status=OBSERVED，无身份mismatch |
| unresolved_free_text_numeric | coverage `numeric_coverage.verified[0].recompute.locator=invented result paragraph` | V1位置未核查；已解析numeric2 | rows_observed=3；unresolved=[] |
| same_locator_two_value_ids | `.verified[1].recompute` 复制 `.verified[0].recompute` | 唯一位置数2，声明value_id数3；重复引用诊断，不能推断经济错误 | 仅rows_observed=3，无重复引用诊断 |
| limits_normalization | `limits=max_seconds nan/inf, max_files999999/0.5` | ValueError或规范的非法限额拒绝 | 分别接受nan/inf/999999/0 |
| file_growth_between_stat_and_read | reader limits单件4/合计8；真实文件stat时1B，read时增长40B | bounded read最多5B探测；不记完整观察 | 完整读40B，error=null |

原测试命令（避免平台临时根权限干扰）：`python -B -c "import pathlib,tempfile,runpy; tempfile.tempdir=str(pathlib.Path('.planning/w08-root-reception/audit/independent-review').resolve()); runpy.run_path('C:/Users/郑曾波/Projects/_harness_worktrees/w08/audit-evidence/tests/test_w08_review_evidence.py',run_name='__main__')"`。40/40通过仅证明现有断言，无上述新反例覆盖。
