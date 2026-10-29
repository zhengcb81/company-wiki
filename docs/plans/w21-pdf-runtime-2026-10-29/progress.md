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
