# W13-CWP-GATES 交接（handoff）

- 状态：**COMPLETE**。独立审查 APPROVE（G01–G09 全 PASS，3 个 minor 发现已修复并经差异补审验证关闭，补审结论 APPROVE）；全部内部发现修复完毕。
- 工区：`C:/Users/郑曾波/Projects/company-wiki-w13-gates`；分支 `codex/w13-cwp-gates-20261024`（已推 origin）。
- code_base_commit：`a31300a70215319e6bcf3a03d32b2882bdf1aeaa`；start_head `8746be6f`；最终head 见 push 后记录；最终被审代码commit `852dff28`（修复commit；初判56baea4c、补审852dff28）。
- 独立审查：`delivery/w13/review.md` / `review.json`（含 delta_re_review 段）。审查者非实现者，实测命令与退出码全记录（145 passed、ruff clean、真实hook缺runner exit 1、12场景G07矩阵、E2E 3 passed 等）。

## 交付内容

日常push与完整验收分层（commit静态检查不变）：

- 全量建议（config/tools/资源/dynamic/未知range返回 `["tests/unit"]`）不再被当命令执行：`tools/pre_push_gate.py::_push_targets` 改跑全部29条 `FAST_CONTRACT_CASES`（成员与基线逐字节一致）并显式声明 defer；closed 受影响文件集仍完整运行+对smoke去重；push 永不隐式启动整个 `tests/unit`。
- `_dispatch_gate`：子进程启动失败（OSError→非零）、timeout（124）、异常（→1）都不再能伪装绿灯；hook 缺 runner 从 `exit 0` 改 `exit 1`。
- 输出语义：`local_fast_pass` / `full_validation_pending`；fast 绿文案不再含 "safe to push"，与完整模式文案（`full local gate GREEN`）不同；`--skip-contract` 绿也注明非完整验收。
- 完整本地模式与远端 `--fast-contracts-only [--junitxml]` 合同原样保留（含 -n 2 有界worker与自有TEMP清理）；两阶段并行调度器随唯一调用方退役。
- 测试：新增 `tests/unit/test_daily_push_policy.py`（33项，含3个真实临时Git push E2E：绿路径放行、ran-scope真失败拒推、缺runner拒推、宽范围defer且串行全量抓到隐藏失败）；按G08 TDD调整两条"每push必须full"旧断言；其余旧断言保留。

## 逐需求结论

| ID | 结论 | 证据 |
|---|---|---|
| G01 | PASS | `.githooks/pre-push` 保留 `--push-checks` 真实stdin链路；E2E真实 `git push`；无skip环境变量/授权文件/缓存绿灯 |
| G02 | PASS | `_push_targets` 推荐集→固定smoke；closed集完整运行；选择函数 `changed_unit_tests.py` 零改动 |
| G03 | PASS | 29成员与基线一致；远端 `--fast-contracts-only` 不变；去重仅在命令组装 |
| G04 | PASS | 完整模式6阶段集合未缩；junitxml参数保持；worker/TEMP合同未动 |
| G05 | PASS | push输出含范围/targets/defer原因与 `local_fast_pass`/`full_validation_pending`；全仓无 "safe to push" 残留（产品代码） |
| G06 | PASS | ran-scope失败→非零+首失败保留；OSError/timeout/异常路径有测试；hook缺runner实测exit 1 |
| G07 | PASS | 空stdin/新branch/ref删除/多ref/删除模块/docs/config等矩阵由 `test_daily_push_policy`+既有选择测试覆盖；政策层显式决定 |
| G08 | PASS | 3个真实临时Git E2E可复跑（`-k real_push`）；旧断言仅G08授权的两处按新规调整 |
| G09 | PASS(记录) | 同机四类实测：docs 44.5s / narrow 66.8s / unknown 46.6s（原~430s场景）；wide 357 targets 628.6s 撞既有600s上限exit 124（与改造前逐路径相同，非回归，不拉长超时）；无墙钟审批阈值。见 `delivery/w13/scope-report.json` |

## 实际命令与结果

- 卡内测试集：145 passed（35.88s）；卡内 ruff：All checks passed!。
- 完整本地模式一次：ruff/compileall/host guard 绿；config_doctor 红（worktree无 `.source_catalog`，基线同现，环境限制）；units 8126 passed/24 skip/19 失败（全部为xdist tmp-file并发抖动，3个文件串行58/58绿）；focused contracts 221 passed/3 失败（`test_b10_read_chain.py` ratchet，src与基线字节一致=基线已红）。首红即停exit 1（G06），其余阶段为证据补跑。
- 真实push：`git push -u origin codex/w13-cwp-gates-20261024` 经真实hook 42.2s 绿，defer语义正确。

## 清理与占用

- E2E全部使用pytest `tmp_path`（自动恢复）；测量driver脚本在系统TEMP；worktree `git status` 干净；无下载/模型调用（0模型/0网络外发，push本身除外）；交付 4.5MiB（<16MiB目标）。

## 跨边界（interface_requests → ROOT）

1. `tests/contract/test_b10_read_chain.py` 3个ratchet在基线 a31300a7 已失败（`test_b10_no_new_column_value_handoff` 等3项；复现 `python -m pytest tests/contract/test_b10_read_chain.py -q`；日志 `delivery/w13/logs/full-mode-focused-contracts.log`）。责任层：ROOT/来源源码 ratchet 登记，非本包可修。
2. 环境限制（非缺陷）：fresh worktree 无 `.source_catalog` 使 config_doctor 必红；本机 Windows xdist 存在 tmp-file 并发抖动19例（串行全绿）。完整模式验收以远端CI为准。

## 独立审查与修复闭环

- 初审（被审 `56baea4c`）：APPROVE，G01–G09 全 PASS；3 个 minor——F1 defer路径标签仍称"affected units"、F2 节点级选择与FAST同文件节点的潜在重复、F3 scope-report 未注明墙钟受负载影响。
- 修复 commit `852dff28`：F1 标签按实际ran范围措辞；F2 去重重构（整文件选择覆盖该文件全部节点；节点选择只去重精确同节点，兄弟FAST节点保留，G03无损）；F3 增加 measurement_caveat。修复后卡内测试 145 passed、ruff 清零。
- 差异补审（同一独立agent，绑定 `852dff28`）：APPROVE；F2 经7个对抗场景验证 dupes=[]/lost_fast_members=[]。遗留3条均为外观/信息级（其中1条为 `.planning/du3-quality/` 既有 ruff F401/E401，先于本包、写范围外，已记录）。

## ROOT 下一步

远端CI（tools/ 变更触发）与并线由ROOT核；b10 ratchet、`.source_catalog` 环境限制见上节 interface_requests。
