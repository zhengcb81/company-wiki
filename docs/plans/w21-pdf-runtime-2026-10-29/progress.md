# Progress

2026-10-29 ROOT准备独立工区和完整卡，尚未启动作者实现。四个seed文件是已知ROOT脚手架，可纳入A提交；其他项目和旧env/model只读。

2026-10-29 A完成：读ROOT隔离env全部证据与三个owner文件+现有测试（37通过）；本机NUL归一化实测；
边界冻结见findings.md。启动形态定为 [python,-B,-I,-X,utf8,script]+allowlist env；guard仅探针侧。
下一步：B先RED（新tests+探针旧guard复制），再修launch owner与guard。

2026-10-29 B完成：RED捕获（8 failed：旧guard复制误拦devnull正例4项 + owner函数缺失4项，存receipts/b-red-initial.txt）；
随后GREEN（18新测试通过）。修复内容：narrative_pdf_enhancement新增CHILD_LAUNCH_FLAGS=(-B,-I,-X,utf8)、
child_launch_command、child_environment（OS必需allowlist+显式offline/线程变量+PYTHONNOUSERSITE，不含PYTHONPATH/PYTHONHOME），
enhance改用之；探针guard改为字面量+realpath双条件discard-device规则。相关既有117测试全过，ruff/mypy干净。
冷启动rev1收据：status=ChildTimeout@30.015s（卡内固定界，未提额未重跑），guard_rejections=0（旧17.8s误拦点已通过），
isolated/safe_path/utf8=True，prefix=env；fauilthandler栈=importlib.metadata读元数据（transformers扫描，IO-bound：
8.6s CPU/25s wall）。根因：本机冷文件缓存下固定SDK import>30s，与旧探针（热缓存仍死于18.8s、从未到DONE）一致；
30s界内完成性如实记PARTIAL，SDK启动完成性由C阶段120s生产界E2E复验。

2026-10-29 C完成。E2E与冷启动迭代出完整根因链（每步都有receipt）：
- rev2/rev3：pycache前缀引入后，探针guard与tempfile探测交互暴露更深根因——隔离env python.exe文件带
  Mandatory Label Low (I)(NW)（继承自Low标签的部署树），子进程恒Low IL，无法写Medium的%TEMP%；
  dill.session在import期调用tempfile.gettempdir()，所有候选目录对Low child均不可写 -> FileNotFoundError。
  生产enhance原把TEMP指向parent %TEMP%下的TemporaryDirectory -> 生产child从来不可能在本机完成导入（主线SDK阻点的完整根因）。
- 修复（均在launch owner范围内）：child TEMP/TMP/TMPDIR指向repo-local Low树 (__pycache__/pdf-paragraph/tmp)；
  pycache_prefix同根（worktree整树Low, child可写）；allowlist补USERNAME（getpass.getuser()在无console无env时崩溃）。
- rev5冷启动：DONE_NO_DOCUMENT于16.2s（30s界内），guard_rejections=0，peak 616MB，isolated/safe_path/utf8=True。
- canonical E2E（ROOT profile原python路径）：triage 2页gap信号触发，真实worker经生产入口完成
  identity+import+CONVERTER_READY，PAGE_1处ChildFailed：docling-parse 6.2.0 C++窄串路径
  （pybind11 UTF-8语义）在ACP=GBK机器上无法从非ASCII部署路径打开pdf_resources
  （fopen对照证据：GBK字节OK / UTF-8字节FAIL）-> ConversionStatus.FAILURE -> 诚实native_fallback。
- ASCII别名E2E（junction同一env，--python诊断参数）：同一生产入口全管线成功——
  completed_pages=[1,2], stream_complete=True, actual_engine=docling 2.96.0, 真实model_sha,
  converter_instances=1, peak 3.25GB(与卡内~3.10GiB特征一致), 43.2s<120s界,
  alignment拒绝2组 -> 诚实unaligned_native_fallback, 原文text/hash保留, replay不重启模型。
- 故障恢复：既有checkpoint测试覆盖超时/损坏尾记录/finished-page保留（test_pdf_page_checkpoints.py 53测试）。
- 清理：junction已删，ROOT importtime.log误写已删，诊断脚本已删，env/receipt/model SHA全部核对不变
  （profile bcc427…/probe bb67326a…/model 00333a…/config fdea30…），env今日零写入，prefix/tmp无残留。

2026-10-29 事故与恢复记录：为验证DU2测试是否基线已有，误在共享stash语义下运行了 git stash / git stash pop——
工区树上无未提交改动，pop实际弹出ROOT共享stash@{0}("c3 semantic WIP")并部分应用到本工区（UU冲突）。
立即git reset --hard HEAD恢复（HEAD=5a33d923完好），ROOT stash两条目未drop、完整保留；"already exists"条目
实为稀疏索引缺席文件，reset后按稀疏规则正确不在盘上。工区现已干净。教训：linked worktree的stash列表与主仓共享，
工区车道内禁止使用stash。DU2失败在干净基线上同样失败（稀疏缺docs/plans/document-understanding-2026-10-13），非本包回归。

2026-10-30 措辞更正（采纳初审INFO）：本文件早前ASCII别名E2E一句中的 replay 表述，在 replay_verified=0（0 spans）下不承载证明，收敛为：replay入口在0 spans时为平凡通过；replay不重启模型的证明由既有integration测试（mock runner，9例）承载。独立审查报告见 delivery/w21-pdf-runtime/review-initial.md（10项全PASS、0阻塞、6 INFO已采纳）。

2026-10-30 推送处置：pre-push gate contract smoke 在本工区确定性阻断 test_projected_two_parents_cannot_borrow_one_raw_proof
（gate外单独运行必过）。根因（gate精确复现+逐帧+长度对照）：persist_projection 走 atomic_output 的82字符staging名，
文件全路径在 gate 的 worktree 内 basetemp 布局下达270字符，超 MAX_PATH=259（LongPathsEnabled=0）；ROOT 主工区同布局254字符
故从未触发。属共享层（official_json_projection/_atomic_file/pre_push_gate）既有潜伏缺陷，非W21改动；按卡不跨范围补，
交最小反例 receipts/push-gate-path-length-counterexample.md。pushed_to_remote=false，交付STOP等ROOT验收。
诊断残留 gate_repro.py 已删。
