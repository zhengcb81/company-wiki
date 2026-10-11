# W05-CWP-OCR ROOT 修复后的独立最终审查

**结论：整体 FAIL，暂不发布。** 固定下列五个产品文件的恢复、预算、坐标、配置与 Windows 边界局部工程复核为 PASS_WITH_SCOPE，但 ROOT 的真实配置 PPTX E2E 已失败：phase1 在85.047s产品绝对deadline触发，第一轮native transcribe没有产出。ROOT最终组合包184 PASS、原6探针 PASS和50ms真实startup PASS不能替代真实E2E。性能共因仍须分段实证定位，不提升时间预算来掩盖。此报告不将 W04 selector/摘要或 RF 经济质量标绿，也不宣称 POSIX 已在 Windows 测过。

## 冻结对象

树：`C:/Users/郑曾波/Projects/_harness_worktrees/w05/cwp-ocr-root`。本报告绑定实读文件 SHA，代码尚未由本审查提交。

| 文件 | SHA-256 |
|---|---|
| local_ocr.py | `ff7db0e6aeea844c1f32d3de3f3fdfa7965e6a3cd4f3fe56d4e455efc08a574f` |
| ocr_composition.py | `9a4d517114d6bcd4b692eee4520c9fc2d16f6caa84854f348d1c655d668bd9fe` |
| ocr_region_recovery.py | `2803919d0f9b816c5cff45cf6344709abea8104f124945d9a3da24862417823e` |
| isolated_ocr.py | `d59a52a35dc6fc9c196d9e293b962ea844f171caf132e5823ea97f66b4303c98` |
| narrative_normalization.py | `b29a4fe2069713800d171c30ecd09d7bcf3a35984ef2f872ed85d8d4986ccbfd` |

配置只实读核 hash，未漂移：local_ocr.json `3ef4d36adff892e66115271a15e3e73dd20a530af615e24d80cdb35f4cf20105`；config.yaml `2f4df37c3d39ef380caf476b6b678949a1e4b7604bdb95b73b0033804209c589`；source_catalog.yaml `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`。

## 独立实测

1. **原6个反例，期待和脚本未改，全部 PASS**：针对最终freeze再跑一次，记录 `frozen-counterexamples.json`，SHA `7ad080a7e5f563a4017dffd6f6ccedf47d13263d90c0e741ee2ff397a6efac33`。原交付5 FAIL的 JSON/script/报告，以及中阶段修复结果均完整保留。
2. **新独立产品startup反例 PASS**：现有formal startup测试是已经过期的deadline，本审查补有效未来50ms的绝对deadline，真实启动bootstrap pid5240；在 **52.16ms** 由产品返回 `NormalizationLimitError(deadline)`，backend未开始，bootstrap已回收，proxy scratch为空，owned测试根删后复原，配置身份等同输入。此证明未借助 ROOT emergency Timer 或外层 subprocess timeout。
3. 只读审查 formal 新测试与完整失败留证：恢复机制第一次 formal RED 是9行为 FAIL；修复集中37 PASS。硬边界原3行为 RED、第一次fixture导入故障、missing dispatch input、Windows native-handle清理竞态均保留，后续6直接影响项 PASS、3 NNorm/AUTO兼容项 PASS。ROOT另完成最终组合包184 PASS，本审查不重复整包或真实 OCR。
4. 已实读 ROOT `root-real-e2e-original-fail-result.json`、`root-real-e2e-original-fail-receipt.json`：phase1 **85.047s FAILED**，错误是 `NormalizationLimitError(...isolated local OCR)`；整体runner **86.166s、exit1**。原件与配置前后SHA一致，scratch初末均absent，网络/LLM/费用为0。新增 **OCR-I05 P1**：配置原生子进程真实性能未满足同一90s单页E2E边界；具体耗时环节未知，不能签完成。原失败留证将保留，ROOT委派分段诊断。

启动探针：`hard-startup-probe.py` SHA `dc5d4e7efb9e1abd25a86d4a98b7a4e6a958a1f44adba6542d8f405e84d1cab4`；`hard-startup-result.json` SHA `946417781df16c120a2405848ed10e35af6086acd682441122e0a5a5373ec918`。探针文件配置是隔离临时假模型，不打开生产模型或原文。

## 根因修复的验收

- **OCR-I01 预算**：同一 RecoveryBudget 在源图/ROI推理前原子预占 max_image/max_total pixels；不足剩余量不调用backend；跨图共享、失败已花的量保持记账。原“剩余1 pixel却先识别15,660”的实际调用已消失。
- **OCR-I02 过滤契约**：evaluate检查真实 adapter的 dropped诊断，而非只看已经过滤后的高分行；所属原region尚有未读清内容不签 recovered。外部邻居仍可不干扰完整正文。每次attempt留过滤诊断，原正确行不变。
- **OCR-I03 坐标**：split-stack detector框必须完整落在单个实际块x/y区间；跨块、空白padding、超尾框拒绝，无法定位的额外文字不被静默丢弃后拼接。旧假框越界测试修到合法坐标，同时保留成功文本/失败语义和专用越界负例。
- **OCR-I04 旋转**：90/270 使用正确的原画布维度；非方形真实PIL正向旋转生成独立golden。恢复过程本身没有新增旋转梯子，不靠手录公司答案。
- **派生身份与回放**：`bounded-source-roi/2` 进入 LocalOCRConfig 身份，旧算法不能冒充。新proxy原样保留config.identity_manifest/fingerprint；恢复单位继续绑定原source/media/原图bbox/连续locator，低分乱码仅诊断。旧adapter默认诊断空兼容，recognized仍不是完整召回。

## 原生隔离边界审查

- public `enrich_pptx` 对默认 configured LocalOCRAdapter 创建请求拥有的 IsolatedOCRAdapter；正常返回、异常均退出context回收。默认 NarrativeNormalization 也用该proxy，显式注入的legacy假adapter签名不变，增加close/context，不在parent先跑原生preflight。
- 一个绝对effective deadline覆盖解释器启动、模型构造/预检、input/result传输、原图及ROI所有调用；首次无显式deadline时才固定90s fallback，后续取min不能续期。清理仅另有固定2.5s grace，不延长工作许可。
- image/result采用每份≤32MiB owned文件，配置≤64KiB，通知≤4KiB原子JSON；不在管道里阻塞发送大payload。操作完成即删该次image/command/response/result；失败和close回收全owned树。
- Windows用CodeGraph核既有WindowsJob结构：KILL_ON_JOB_CLOSE；bootstrap必须先assigned Job才放行启动native；CREATE_NO_WINDOW；正常timeout主动TerminateJobObject，owner消失也由OS关闭句柄杀整棵树。native持GIL不能阻止父进程deadline。nativePID释放与scratch删除共用一次清理grace，解决真实WinError32竞态，不削弱原断言。
- AUTO daemon兼容：使用真实新解释器subprocess，不用daemon父进程禁止的multiprocessing子进程；formal测试直接施加daemon flag后仍可创建并清理proxy。
- POSIX另开session + 独立轻量guardian看stdin EOF，native占GIL不影响guardian；kill原group（即便leader已经退出）是合理的静态实现。**未在此Windows宿主执行POSIX分支，不能记成Linux实测通过。**

## 剩余范围、费用与清理

- ROOT须修复真实native路径性能共因，再在同一预算下记录SourceVersionReader→配置OCR→正常compose→locator replay的退出、elapsed、原22行与两定义、原件/config SHA。当前真实FAIL未产出单位，不能声明恢复两定义已经在最终代码通过。不能拿外层emergency Timer代替产品硬截止proof。
- 未detected的文字、重叠区域保守排除、通用合成图没触发真实低分分支的限制仍诚实保留；opaque/unverified不改为完整召回。
- Windows uncatchable owner kill可遗留有限系统TEMP scratch：进程存活由OSJob防止，删除只能best-effort；正常/handled路径必须复原并已有证据。不是生产数据写入或模型下载。
- 本独立审查 **0 provider/0付费/0云OCR/0模型下载/0原文读写**。唯一新增临时根 `owned-hard-startup-kinv8yib` 经绝对父路径校验后删除；恢复成创建前不存在。写集只本independent证据目录；没有产品、六PWF、原件、配置或提交修改。
