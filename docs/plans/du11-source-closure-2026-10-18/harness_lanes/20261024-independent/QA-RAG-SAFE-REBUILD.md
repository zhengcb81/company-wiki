# QA-RAG-SAFE-REBUILD：安全重建本地知识库

状态：READY；与 company-wiki 主线没有代码依赖。项目 C:/Users/郑曾波/Projects/QAbyLLM。独立工作目录 C:/Users/郑曾波/Projects/QAbyLLM-rag-safe-rebuild。branch codex/qa-rag-safe-rebuild-20261024。冻结起点 main@ad389f84cd15e54207fc6fcfe4881f86edac63f1，检查时 origin/main 一致且干净。PLAN_ID=qa-rag-safe-rebuild-2026-10-24，PWF_PLAN_ROOT=docs/plans。

## 根因与目标

rag_system.py 的 build_knowledge_base 当前先清空 active collection，再读取/切块/embedding/写入。任一后续步骤失败，旧知识库已丢失，调用者只收到 False。要修复“先破坏可用状态、后验证新状态”的根因：新库完整构造和校验前，旧库必须可查询且记录不变；失败或中断不能错误发布新库。

## 唯一写入范围

允许：rag_system.py；新增 tests/unit/test_rag_safe_rebuild.py、tests/integration/test_rag_rebuild_lifecycle.py、tests/fixtures/rag_safe_rebuild/**；本卡 PWF 与 handoff。

禁止：config.yaml、config_example.yaml、vector_db/**、test_vector_db/**、output/**、真实 JSON 报告、UI/启动脚本、document_processor.py、hybrid_retriever.py、providers/keys、其他仓库与全局安装。不得对原有 vector_db 或真实 collection 调 delete/reset/migrate。

## 实施要求

1. 用 fake collection 注入解析、embedding、写入错误，先重现失败时旧库被清空。
2. 设计最小 staging/publish：新 generation 写到独立位置，验证完整后再切换 active 指针；成功后才清理旧代。不得原位清空重建。
3. 注入发布前后中断与切换错误，验证重启仍找得到上一 active generation；孤儿 staging 可识别清除但不得删除 active。若 store 不支持原子 rename，采用清晰的 generation pointer/manifest，说明原子性边界；不引入通用任务队列或新数据库。
4. 文件枚举顺序变化不能造成 chunk ID 与文件 metadata 错配。定义重建时覆盖、删除旧 chunk 的规则并有反例；不能依赖 os.walk 偶然顺序标记 doc_0。
5. 保留公开调用兼容。区分“本次失败但旧库仍可用”和“新代成功发布”，关键阶段不能吞异常后报成功。

## 一次集中验收

覆盖首次构建成功、旧→新成功切换、空目录/解析/embedding/写入失败时旧库完整保留、发布前后模拟进程中断可恢复、active generation 不被 orphan cleanup 删除、输入枚举重排不串档、测试根 sentinel 不变。所有测试禁用模型/API/网络，只用合成 TXT/MD、fake embedder 和 fake/local temp vector store。若用真实 Chroma，只能建在本卡临时根，完毕后确认原 vector_db 目录清单和 SHA 不变。

运行：

    python -B -m pytest -q tests/unit/test_rag_safe_rebuild.py tests/integration/test_rag_rebuild_lifecycle.py

同时跑直接相关的既有 RAG 测试，报告精确命令和结果；不修无关全仓失败。测试临时目录结束前后清单及 hash 必须一致。

## 独立审查与交接

任务分支提交并冻结 SHA 后，未参与实现的独立 agent 审查完整 diff，挑战 staging 顺序、异常注入、崩溃恢复、输入重排和范围隔离；自行运行测试并添加至少一个失败注入反例。所有发现修复并复审最终 SHA PASS，才可交接。提供 docs/plans/qa-rag-safe-rebuild-2026-10-24、docs/handoff/QA-RAG-2026-10-24/handoff.md/json、审查报告、测试日志、清理证据；不得交付 vector_db、真实配置或公司报告。
