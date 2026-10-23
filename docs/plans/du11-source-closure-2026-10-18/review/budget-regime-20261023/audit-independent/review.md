# Audit low-budget 独立审查结论

**结论：PASS。low 语义与恢复行为通过；发现的一项既有 P3 文档笔误已由 ROOT 修复并独立复核。**

这是对 `revenue-forecast-audit` 的独立审查，不是生产作者自签，也不代表总预算制度、真实公司运行、安装同步或主线发布已完成。

## 审查绑定与改动质量

独立18项探针时五文件SHA/字节数与作者handoff完全一致，探针前后未变。随后ROOT只更正契约大小端文字并统一换行；独立反向恢复文字及原换行形态，逐字节精确重建原文SHA，确认没有其他文本差异。四个代码/测试文件仍完全相同。最终绑定见 `review.json`，原探针历史绑定保留 `probe-result.json`。生产脚本 SHA：

`eff14102ef7258eb8c5588043884004f11f3cd2388d1ecc8bc40e11d6895a492`

读取了 AGENTS、所选 task_plan/findings/progress、原 RED、相关测试、全套测试及清理收据、handoff、五文件真实 Git diff；CodeGraph 未初始化，按只读范围使用指定实际文件，没有初始化或修改索引。

生产修复集中在既有 budget handler 和 derive owner：low 添加提醒；只有 exhausted 走真实全局硬限额停止分支。没有新增公司名、金额、阈值、provider、账本、许可或审批链。用既有 observation 声明预算状态；公司 soft allocation 的使用方不能把软超额伪造为 exhausted。此 reducer 不读取或判定实际余额，也不替实际付费调用执行全局/单请求限额。

## 独立验证：18/18 PASS

实际导入目标脚本及同目录 audit_run，检查 `__file__`。使用全新中性公司/版本/预算输入，不导入作者的测试或真实公司夹具。

- 14种阶段逐一对比 ok/low 的完整 next_action：选样、executor进行中/失败/封存、部分/全部活跃writer、未知writer、四报告、expert无问题/major、待复测、版本变化、真实抽样达标、公司池耗尽。动作完全一致；low仅多 budget_low_warning，原入参/抽样/当前公司/费用/clean/有效版本不变。
- low/ok/unknown 存在可能收费记录时均先 reconcile，cost 保持 null、resend=false。known但无金额仍不能假装完成；unknown附金额不会变成已知；确证为0才恢复正常派工。
- 真实 exhausted 保留当前公司、待对账、选样和 clean，停止相关付费而不宣布活动完成；恢复 low 后继续对账，不重发收费调用。
- 同事件重放不增加 revision；冲突事件不把 low 偷换成 exhausted。
- 旧版本可能缓存 low→stop 的旧 next_action；用现有 `request_next` fold 即按新代码重算并保存 dispatch，不改历史费用/版本/选样。ROOT 安装后应使用既有恢复入口，勿只读历史 cached next_action 当成新判定。
- 独立 CLI 共13次实际子进程：init，low dry-run/apply，重启 request_next，unknown费用，真实exhausted，low恢复，确证零费用。plan不改state字节，apply/CAS版本递增，重启不换样本；每次返回0。

最终耗时约7.12秒，不重复作者全套。作者原收据：58相关测试通过；全套662 run/660通过/2既有skip；官方技能校验通过，均绑定当前五文件；原始4个RED未改期望。作者全套既有mkdtemp残留由单独 full-cleanup.json 关闭，原始full.json未被篡改。

## 唯一发现：P3 既有文档小端/大端笔误

`skills/revenue-forecast-audit/references/pool-progress-contract.md` §3第2条写“每块按4字节小端”，而 `_hmac_byte_stream` 实际使用 `int.from_bytes(..., "big")`。这是先前已有的说明错误，不是本次 low 回归。ROOT已只将文档“小端”更正为“大端”，同时将原113个LF和末尾1个CRLF统一为114个CRLF（13831→13944B）；保留既有算法和冻结抽样期望。独立反向还原文字和原换行后，SHA精确等于作者旧文档SHA，无其他文本变化。新文档SHA为 `33db81fa6fb4e08e8598fe010fc133ad1aa7528fc3bfc2e0311d34ccd6822478`。代码/测试均未改，不重跑全套，此项已关闭。首次仅反向文字的字节检查因换行规范化失败，随后查明真实原因，并未把该核对失败冒充产品缺陷。

## 测试环境与清理

首次沙箱 reducer 16项通过，但 CLI init 的 os.replace 被 Windows sandbox 拦截（WinError5），完整原始失败/源码未变/临时目录已删除证据保存在 `probe-result-sandbox-attempt.json`。同一离线探针申请真实本机执行后17项通过；追加旧缓存恢复反控后最终18项通过，没有改产品绕开原子写。前17项成功版本保留 `probe-result-v1-17.json`。

三次执行均在本目录新建独占 `owned-neutral-cli-*` 临时目录并finally删除；最终目录不存在。所有网络在 reducer 探针禁用；CLI本身无网络/模型/provider派发入口。没有读取原件或密钥，没有费用，没有改Audit源码/Git/安装/历史run/账本。`cleanup.json` 再核验作者及独立临时目录均不存在。

## ROOT 后续

1. low 工程及P3文字均已通过独立验收，可定点提交；最终五文件绑定在review.json。
2. ROOT 对当前有效scope采用已批准的全局10M tokens/$20与公司软分配；历史scope和费用不改。本审查不伪造这些生产动作已完成。
3. 定点同步三个技能文件到 `.claude`/`.agents` 并检查一致；作者所报三文件DRIFT正是待同步变更，不能称已部署。
4. 继续原生request_next/plan恢复，真实provider调用仍按原配置和共享账本执行。