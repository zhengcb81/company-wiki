# ROOT 当前基线与规划输入

日期：2026-11-11。本轮只读代码调查，不代表重新跑过产品验收；无下载、模型调用或原件修改。

## Git 基线

| 仓库实际根（Projects 下） | HEAD | 分支 | 跟踪文件观察 |
|---|---|---|---|
| company-wiki | 08dfe8bf1 | master | 规划前干净 |
| filing-fetch | f65e6ca | main | 干净 |
| revenue-forecast | b005a179 | main | assurance/runs 下 daily_alert.jsonl、monthly_manifest.json、weekly_alert.jsonl、weekly_manifest.json 四项既有修改 |
| StockWiki | 12c441e | master | 干净 |
| revenue-forecast-audit | 3589b69 | main | 干净 |
| investment-dashboard | b707473 | main | application/service.py、ports/protocols.py、transport/http.py、tests/support/factory.py 四项既有修改 |
| earnings-transcripts/earnings-transcripts | 003c1c0 | main | 干净 |
| StockInfoDLSimple/v2-clean-rewrite | c0f07e1 | v2-clean-rewrite | 11 项既有修改，见下文 |

这是 `git --no-optional-locks status --short --untracked-files=no` 的只读现场结果；没有新鲜 fetch，也没有对未跟踪文件作清理或穷尽盘点。外仓普通沙箱 Git 曾报 work-tree/Permission denied，宿主只读重查成功；不能把该环境错误算作仓库架构缺陷。

SID 修改路径：README.md、config_template.json、main.py、src/browser.py、src/downloader.py、src/logger.py、src/mapping.py、src/models.py、tests/e2e/official_e2e_test.py、tests/unit/test_downloader.py、tests/unit/test_official_e2e_contract.py。新任务不覆盖这些内容。Dashboard 沿既有 owner 工作，不另开竞争作者。

## 为何旧阶段无法给出全局关闭结论

1. 父 task_plan 的 D5 标题/完成定义曾使用“全局 ACCEPTED”，最新 P3 又明确全局 OPEN。CURRENT_STATUS.json 仍有 `execution_mode=mainline_after_d5_global_decoupling`、旧 `current_work` 和 `no decoupling package remains active`。既有 D4/D5 证据只覆盖冻结接口，必须保留该成果并限定范围。
2. 仓内边界、跨仓交付边界、旧工具分发、真实摘要语义和公司研究质量未形成互斥问题清单；局部通过后又把新的问题合并到同一个“解耦完成”口径。
3. `tests/support/layer_boundary_scan.py` 的 `_LAYERS` 列举 9 组，其他根文件归为 `<shared>`；扫描 `src`。`test_layer_public_boundaries.py` 有 6 条冻结兼容边和较多指定文件/语法形状断言。它能阻止已知绕行，但不等同所有可执行入口、部署包和状态 owner 都隔离。
4. `tests/conftest.py` 将 `src`、`scripts` 和 `tests` 加入 sys.path；`test_packaging_contract.py` 只核 TOML/目录，CI 安装 requirements 后跑源码。已有 DU 和 summary 子进程拒绝无关 imports，以及实际 reader 可替换测试，必须复用；仍需用实际交付包在无邻仓实现的环境覆盖活动入口。
5. 前一节点的部分失败来自 WinError5 和 monkeypatch 已删除私有 helper。应让边界行为测试绑定公开合同，明确环境故障，不用整仓反复重跑代替归因。

## 不把字符串命中当缺陷

`source_catalog/control.py` 中存在外层 `source_catalog_worker.ps1` 定位，但独立调查追踪到其 start/resume 已退休，CLI 只有 status/stop。这不是已证实的现役安装故障，应进入遗留入口分类。现役默认配置路径与 clean-install 缺口另行由 owner 复现。

## 本轮原则

- 完成标准绑定当前活动入口/协议/状态 owner；新发现归入该有限矩阵，不扩成无边界的语言解释器或全部研究质量工程。
- 独立安装/替换实现、跨仓黑盒组合与状态写入隔离是验收；AST 是补充。Python `_`/`__all__` 不是安全沙箱。
- 已证明的接口不重写；历史兼容不能作为当前默认路径的暗门；无现役使用的旧工具按 owner 分类退休。
- 可选日志/review/格式/文件长度不作任务许可；真正源身份、协议、原文和付费状态仍由唯一 owner 负责。
