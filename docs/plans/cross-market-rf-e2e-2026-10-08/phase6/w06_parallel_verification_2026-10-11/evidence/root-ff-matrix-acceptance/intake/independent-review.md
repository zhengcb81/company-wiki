# W06-FF-MATRIX — ROOT 独立只读接收

**结论：交付及证据已接收，当前不能签 COMPLETE 或作为并线验收套件使用。建议状态 PARTIAL，ROOT 在隔离工区修复测试工具的共同根因后复验。** 没有改动 FF/ET/CWP 产品、共享 PWF、Git、安装目录、Dayu 或 IQS；没有真实下载、LLM、供应商或网络调用。

## 交付边界与 Git

- 实际工区 `C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix`，分支 `codex/w06-ff-contract-matrix`。
- 基线/FF canonical main：`08ec85b27133cdf8a8d3b38fdba15255fc1ebac2`。feature：`8dd00e207e1465095f37ff720bc165b541bdd093`；handoff HEAD：`c5527f1a9b2123e3f1796b5eb4dd35e0a81e13f5`；main 与交付为 0 / 2 commits。
- 相对基线 139 个新增路径，工具/新测试/PWF/小型交接记录；既有 FF `scripts/` 零改动，未改 ET/CWP/Dayu。交接目录目前实际 136,567 bytes。
- 工区尚有 `.planning/w06-ff-matrix/{task_plan,progress}.md` 修改，都是写“完成”和补最终进度；handoff 的旧 SHA 因此 2 项不匹配。`input/` 是未提交 ROOT 输入。不得直接 reset 混掉这些可解释记录。主线唯一未跟踪 `config/FMP_API_KEY.txt`，内容未读取。
- 25 个 manifest / changed_files / input_evidence 行中 23 SHA 匹配，非 PWF 的工具、新测试、输入和 6 个 manifest 交接文件全部匹配。详见 `sha-verification.json`。
- attempt-5 明确记录实际 CWP HEAD `c145da9b...` / ET `c91f5f54...` / FF `d9c5383e...`。后者对象存在且 `scripts/` 与交付 HEAD 相同；9 个 producer module 实际 SHA 全匹配。不能把这次运行称为固定 CWP `01ea86a3...` 上的回放，也不能把 current isolated OCR/RF WIP 不在 canonical 视作 FF 缺陷。

## 已有成绩与证据范围

交付 12 个纯单测独立重放 **12 PASS，整体 3.19 秒**；无缓存写入外部工区，pytest 临时根测试后删除恢复。原 attempt-1 及 attempt-5 完整保留，intake 不覆盖原 FAIL。

原 attempt-5 有 16 PASS / 86.76 秒记录。真 FF 公开 CLI、ET `transcript_tool.main` 和真实 supervisor/worker 的 seam 调用是存在的；ET `_SpecSession` 只对已注册 URL 返回合成响应，未注册 URL 抛异常，不回退真实网络。proxy 没有整层伪造 ET stdout。FF 本身调用真实 transcript import 和 reader 路径；真实结果表明一次合成原语言 FMP JSON 入库，下一次相同 SourceRef、provider_calls=0，publication_date=null 时保留 unknown_publication，而非猜测 historical eligible。402 / 缺凭证 / unknown usage 各有正确诊断的保留记录。PDF 是完整 xref/trailer 小样，HTML/TXT 是合成合法字节。

这些有用记录不能弥补 runner 的错误验收谓词。intake 只调用现有纯函数、case helper 和明确替换全部 producer 的 in-process CLI 脚手架，不把该脚手架叫真三层。11 个独立控制得到 **10 FAIL、1 正确季度拒绝正控**；证据为 `independent-counterexamples.json`。没有断言实际产品一定存在这些合成响应错误。

## 需要 ROOT 系统修复的阻断项

### FFI-P1-ISOLATION：最小合成环境与密钥不读声明未成立

`run.py` `ProductionGuard` 把 `FMP_API_KEY.txt` 传入 `_hash_meta`；该函数调用 `report.sha256_file`，后者直接 `Path.read_bytes`。使用本 intake 临时合成假密钥，确定观测到读完整字节并生成 SHA。原工区并非必然含此文件，**没有证据交付运行已读取或泄漏真实密钥**。

`Context.child_env` 全量 `dict(os.environ)`，仅替换/移除 FMP_API_KEY、移除 FMP_API_KEY_FILE；其他供应商密钥、endpoint、路径配置全部继承。独立控制仅用假环境名称和值，证明 DEEPSEEK_API_KEY、OPENAI_API_KEY、API_BASE_URL 会原样传播，不读取真实环境值。`cli_main._verify_binding` 更忽略传入合成 env，另一次复制真实 os.environ 并以 ET 码根为 cwd。没有发现实际泄漏发送。底层已注册 ET seam 不会联网，但 runner 并未建立“所有进程全部 HTTP 拒绝”的证据，report 的网络零与 translation=0 都是常量，没有 network guard / TranslatorFactory construction spy。

**共同根因：测试运行环境没有统一责任层。** ROOT 应用一个平台启动 allowlist + 合成必需变量生成器，所有 binding/scan/FF/ET/CWP 子进程同用；scratch HOME/USERPROFILE/TEMP 可满足配置解析，不继承 host keys/provider override。密钥路径检查只 stat 元数据，不读字节/输出 SHA。网络拒绝与翻译构造计数仅为隔离测试机制，不给生产增加权限门。

### FFI-P1-ORACLE：PASS 谓词和证据之间失去约束

- `case_call_wrong_quarter` 请求 Q3，却 `status=downloaded, fiscal_quarter=2` 判 PASS。
- `case_call_past_cutoff` 把任意 upstream_error/provider_unavailable 当 cutoff 证据；独立 arbitrary_import_failure 仍 PASS。交付真实 ET 该案例给 not_found，而非具体 cutoff receipt，报告需准确表达范围。
- `case_fin_fetch` 第二次又 downloaded_new，缺 source_ref、download_events=0，仍 PASS；counter 是从成功结果数推得而非真实 adapter 调用日志。
- `case_err_unknown_usage` 对 requests=0、usage_complete=false 判 PASS；oracle 的 `or 0` 同样将 unknown 误当已测 zero。
- `_verify_binding(...).verified=false` 不阻止任何 case 和最终 exit=0；空矩阵、缺完整 registry 也不被 oracle 识别。三层 proof 只检查若干自填 bool / SourceRef 是否非空，没有绑定到可复查 fresh reader bytes、usage、实际 module 和 requested identity。

**共同根因：case/oracle重复依赖自声明 bool 和弱错误判断。** 用共享 typed result predicates 绑定精确请求 FY/Q、正常/失败类别、真实 usage 和完整必需案例。无数据应 UNRESOLVED/NOT_RUN，不能 `or 0`。季度/as-of/byte 正确性由各产品责任层一次验证；测试消费并复核证据，不创建第二身份许可链。保留 original FAIL 和合法显式 quarter_mismatch 正控。source_ref 只作引用；从独立 fresh SourceVersionReader.open_version 记录字节 SHA、exact original-language canonical bytes、单一来源版本数量，来证明三层链完成。

### FFI-P1-OWNERSHIP：可删除非本次生成的测试文件，恢复报告失真

CLI 对已存在 owned_root 使用 mkdir(exist_ok=True)，直接覆盖 sentinel；对 `owned_root/scratch` 无条件 rmtree，且无 root/out overlap、reparse/symlink、预存文件控制。独立脚手架仅在本 intake 创建一个合成 preexisting scratch 文件和原 sentinel；CLI 删除文件、覆盖 sentinel后还输出 restored=true。

没有生产文件被本 intake 删除。ROOT 应优先拒绝非空/重叠/不安全 owner 路径，或为本次生成全新确定 owned child，保留调用者预置 sentinel/清单；only remove paths created by this invocation，终于关闭 SQLite/子进程且异常也有 finally 清理。这是测试文件生命周期，不需要用户签收。out_root 必须是新 attempt、不覆写 sealed report。

### FFI-P1-TIME/COVERAGE：预算只是 WARN，关键产品 FAIL 被避开

BATCH_DEADLINE=180 定义但不参与调度。CASE_TIMEOUT 只事后 WARN，单 FF run 的 subprocess 等待 timeout+20，一个 case 可两次调用；init/binding/seed 不在 batch 计时内。模拟 41 秒 case、220 秒 batch 和未通过的 binding，CLI 仍 exit=0。统一绝对 deadline 传至所有调用，超限保留 partial、终止并回收当前子进程，不能仅调大上限或新增睡眠。

原 attempt-1 的同 entity/kind 旧期本地来源阻断 fetch_if_missing 是具名产品故障，worker 改用 HK 无同类候选来获取绿。ROOT 可独立处理 CWP shared prepare/ensure 根因；在修复前矩阵必须保留原向量，报告 PARTIAL，不把避开问题称整体 COMPLETE。

16 cases 仅三个不同市场/类型的命中、一 HK annual 缺口和四非周期 kind，不是 CN/HK/US × annual/semi/quarterly 全矩阵。未覆盖卡指定 wrong-symbol、坏 SHA、错误 MIME、超字节、硬 timeout、真正已发请求后失败/retry清理、reuse_only 本地缺口、完整本地 TXT/JSON精确复用计数和未翻译构造断言。w06-fixture-cn 替换供应商整个适配器，证明通用 CWP JSON adapter 数据合同，**未证明真实 StockInfoDLSimple/各实际 provider 工具选择**。不能标 actual provider routing PASS；不支持的真实工具类型显式 GAP。Dayu 保持纯外部零写，不增 provider、不改其源码。

## 非阻断交接整洁事项

- task_plan.md 任务复选框和 Next Step 仍是初始项，状态却 all phases complete；真实最终进度位于未提交状态修改。ROOT 定点接入可解释最后记录并刷新 manifest，保留当前接收快照，不重签原证据。
- 单测中六失败向量是绿色的 oracle 检出测试，没有单独 callable stub 的行为 RED 日志；attempt-1 是真实产品错误/工具首次失败，二者范围分开。以后 formal RED 必须约束上列共同根因，不重跑老 645 项去替代少数有效新测试。
- scratch_peak_bytes/retained_bytes 在 handoff 是 null；现有留存 136,567B 可以据实写回，scratch 峰值必须测量或保持 unknown，不能声称 ≤64MiB 已验。

## ROOT 下一步：一次集中修复与集中验收

1. 新隔离 FF ROOT 工区正常 merge 两交付 commits，不写原 worker/main/WIP。先保存这里 frozen helper vectors 为有效 TDD RED（并加合法正控），修共用环境、owned-root 生命周期、deadline/result evidence/report，而非按公司打补丁。
2. 工具快测只跑新单元+相关 helpers；保留全部旧断言。矩阵补 required cases，并保留跨期 FAIL 独立标 PARTIAL，若 CWP 根因由 ROOT 改好再跟 final code 明确绑定。
3. 大节点在新 scratch、final明确 CWP/ET code roots 跑真实 FF→ET(supervisor fake HTTP)→CWP register/fresh open→复用，一轮剩余矩阵；记录实际模块/HEAD/SHA、所有 counters、before/after 和 partial。如果 upstream错误未修就如实 PARTIAL，不能去掉向量冒签。
4. 独立针对冻结反例和真实关键链验收；整理 finalPWF/manifest，正常 commit/merge/push，由 ROOT 决定安装。快工具单测可进入 impacted CI，跨仓手动矩阵不塞每个 commit。

ROOT 负责所有产品修复、并线和共享计划。此 intake 没有改变既有门禁、没有新增用户许可或人工签收，也没有收取 provider/模型费用。
