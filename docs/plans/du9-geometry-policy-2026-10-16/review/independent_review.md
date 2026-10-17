# DU9-CWP-GEOMETRY-POLICY 独立全面审查

- 审查者：真实独立 agent `/root/du9_policy_final_review`，区别于实施者 `/root`。
- 原实现：`30df8eae2d530081b0173a0965bf30f2e9b45c74`。
- 最终审查提交：`6e0edeefa7b46def4df61ebb538051f44363eb50`；基线 `8b7a46ac`。
- 结论：**PASS，未解决发现 0**。仅表示 POLICY 所属组件及其真实公开入口通过，不表示 PLANNER、默认生产几何调度、真实 PDF 或收费摘要质量完成。

## 方法与范围

先读取原施工卡、固定 INTERFACES、作者 A 调查及 ROOT 的 task_plan/findings/progress，再实际读取 git 差异、编译器、registry、测试、24 份 family 规范、生成 catalog/defaults、既有生成工具及相邻测试。未以 ROOT 的 614/626 项收据代替独立复核。完整实际源码/测试/规范 SHA 清单在同名 JSON。

### 架构与语义

- 编译器是纯数据投影和验证：不重新识别公司/期间/文档、不匹配章节、不 IO、不检查权限、不分配页/预算。不存在新词库、任务库或第二 runtime 配置；runtime 仍唯一加载 catalog，生成器仍只作维护工具。
- 同 role 的规则保留完整嵌套 path、aliases、questions 和 family 因果来源。稳定完整 SHA 包含所有实际规则语义；完全相同规则报重复，合法同路径不同 aliases 不折叠。缺字段和部分 intent 保守 unknown；非法 enum/path/role/priority 有稳定诊断。
- 阅读 priority 与 fine 请求意图解耦。行政 priority 1 不自动 fine、其真实经营附件保留 operating 意图；经营/募投/混合附注保留 on_candidate；风险/背景为 context，电话会和问答不自动要求几何。
- 实际枚举并编译全部 24 family 加 fallback：A/H/US 年半季、IPO、再融资、可转债、可研/项目变更、IR/路演、业绩附件、电话会、行政、第三方、修订与 unknown。此为配置广度，未声称 24 类真实 PDF 均已处理。
- 独立逐字段比对旧新 catalog：除版本和 typed intent 外，仅可转债四条 section 的完整 path 根新增募集资金运用变体；未偷改 recognition、问题、投资研究边界等。旧 15 profile wire 指纹仍保持，相关组件改动进入既有 version/digest，无关 family 不扰动该源。
- 默认 intent 仍 unknown；部分 intent 不推断缺失字段。编译策略不能自行声明页已读、扫描完整或原文事实成立。生产 partial/页覆盖仍由 ROOT/PLANNER 管理。
- 没有提高原页数、时间、字符或费用上限，没有供应商/下载/原件副本。独立有限 1000 次纯编译约 0.04 秒，只作观察不设脆弱耗时断言。

## 发现、根因及处置

### R1 / P1：解析结果浅拷贝会污染共享 catalog — 已修复复核

原实现 `dict(section, ...)` 绕过原 `_sections` 深拷贝；修改返回值 aliases、嵌套 heading_path 或 questions 会改变全局 `_CATALOG`，并污染后续公司 profile/version。独立真实探针三个字段均复现 `catalog_changed=true`、`next_profile_affected=true`，首轮退出码 1：`receipts/reviewer-initial-probe.json`。

根因修复为每条 section 完整 deepcopy 后投影。ROOT 新增 family/fallback/overlay × 四字段共 12 个跨调用隔离回归，不只检查 observation 输入不变。独立原三反例修复后全部通过，catalog 及下一次解析不受修改，见 `receipts/reviewer-fixed-probe.json`；全部新增回归也由独立测试实跑通过。修复提交为最终审查提交。

### R2 / P2：IR 路由用例实际走 generic，却被计为 IR 覆盖 — 已修复复核

原 IR 标题加泛 Business Review 正文实际 route=generic、family=null；测试缺预期 family 断言，fallback 同样绿，不能证明 IR 路由。此非路由器错误，真实来源不充分本就应保守。

ROOT 将 IR 用例改为已有真实问答片段，并给全部 12 路由显式 expected_family 断言（unknown 预期 None），没有更改路由。独立另外构造弱标题与自写问答两组：前者继续 generic，后者实际 `investor_qa_record`。12 个真实公开 route→resolve→compile 用例独立执行通过。修复提交为最终审查提交。

## 独立执行与证据

详见 `receipts/reviewer-final-runs.json`，每条保存真实 argv/退出码/耗时及原输出：

| 检查 | 结果 |
|---|---|
| POLICY + 全部既有 profiles 集中回归 | **263 PASS / 0 FAIL，4.78 秒，exit 0** |
| `tools/import_reading_policies.py --check` | **24 families / 14 facets，exit 0** |
| 独立跨调用隔离、弱 IR、独立问答 IR | **5 检查通过，exit 0** |
| 独立 catalog delta、25 组 family/fallback 编译、11 畸形反例、partial/component 隔离 | **通过，exit 0** |

独立测试使用 owned TemporaryDirectory；sentinel 字节/mtime、生产配置字节/mtime均不变，临时目录最终删除。0 下载、0 原件读取/复制、0 真实供应商。只写本包 reviewer 报告/收据；作者工区和 PLANNER 均未改动。

审查工具自身首版 catalog 反例把可转债下标写成 11，实际是 12；已改为按固定 family ID 定位后重跑，通过且不改生产数据或断言范围。第一次独立工具退出码 1 为审查脚本索引错误，与首轮真实 R1/R2 失败区分，不当作生产 RED 或最终通过。

## 限制与后续

尚待 PLANNER 交付后 ROOT 集成已有 matcher/native windows、共享 WorkBudget 及生产 source/parse port；真实深页 PDF、默认选择、缓存恢复、配置中的供应商摘要和 heldout 质量不在本次组件验收结果内。未运行完整 6213 项、未调用收费 API；ROOT 自己的 626 PASS/11 SKIP 是相邻集中回归留证，11 个 SKIP 不计作真实资料通过。

本报告绑定最终提交和同名 JSON 中的实际源码 SHA；后续如变更源码/测试/fixture需对变更增量复核，单纯补交接文档无需重跑全部测试。
