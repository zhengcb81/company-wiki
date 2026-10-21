# W04 执行记录

2026-10-21，分支 `codex/r1-summary-runtime`，base `0622f242`，ROOT 指定独占工区 `C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki`。

|节点|实际结果|
|---|---|
|来源/接口读查|W04 与 shared_contract 已读；R2 分诊与原脚本只读，原件/配置/旧账不写|
|RED legacy final|4项，3 FAIL/1 PASS，真实 store immutable-zero 冲突，退出1|
|RED retire 初稿|5 FAIL，其中1为新夹具跨 parent错误；日志保留|
|RED retire 修正夹具|5 FAIL，均为预期退役行为缺口，退出1|
|首次 GREEN|新10项 PASS/6.58s；旧114项 PASS/35.76s|
|首版最终 GREEN|扩为14项 PASS/10.77s，0 skip；保留首轮与最终日志/XML|
|只读兼容补证|新1项先RED，定位MODEL_NOT_CONFIGURED遮蔽旧partial；前移历史只读分支，仍在source依赖验真之后|
|最终组合 GREEN|最终15新增/改造+114既有=129 PASS/61.42s，0 skip/0 error|
|质量|ruff PASS；正常 git commit 静态 hook 结果见 commit-product.log，不跳 hook|
|产品提交|588d4635 + 375c29f9，只提交自身分支，未合主线/推送/安装；ROOT 独立验收尚待|

第一次 pytest 未设可写 TEMP，采集前报 No usable temporary directory（环境错误，不算产品 RED）。随后显式设置本包母仓 owned TEMP，正常采集和运行。默认 Miniconda Python 用于正常 commit，移除测试 PYTHONPATH；测试用母仓 `.venv` 并明确导入本工区 src/tests，防止误测母仓 editable install。

具体 argv/UTC/退出码/源码与证据 SHA 在 `handoff.json`；紧凑日志在 `evidence/`。本包无新 live API、下载或真实 token/cost，原 hold不释放；真实 paid-resume/cache/context消费仍交 W07。ROOT接受后下一唯一动作是集成 W04，再继续 W03 与 W07。
