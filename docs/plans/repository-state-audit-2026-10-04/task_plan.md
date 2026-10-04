# 多仓库支线与未提交文件只读盘点 — 任务计划

**状态：** 进行中
**基线观察：** 2026-10-04（本机 UTC 16:39 前后；远端 refs 以 `git ls-remote` 实测为准）
**范围：** 生成独立 harness 可执行的只读审计卡；不清理、不合并任何目标仓库。

## 目标

识别哪些仓库确有未并入主线的提交、未提交文件或无法从 Git/PWF 记录解释的工作树；为每个需要盘点的仓库提供一份互不重叠的施工卡，定义同一交接格式，并由总指挥集中接收报告。用户已决定 StockInfoDownloader 不参与主线，CWP 应使用 StockInfoDLSimple；因此不为 StockInfoDownloader 建施工卡，也不把它的支线作为合并候选。

## 阶段

1. [x] 只读盘点本机候选仓库、branch/worktree 状态、tracked/untracked 状态，并用 `git ls-remote` 校验关键远端 refs；未 fetch。
2. [x] 对照 CWP、RF、FF、ET、StockInfoDLSimple、StockWiki、IQS 等仓库的可见 PWF/交接记录，标明完成声明与当前 Git 证据的差异。
3. [x] 按用户最新决定移除 StockInfoDownloader 施工线，查明 CWP 现有 StockInfoDLSimple provider 入口和剩余旧引用；不读写 StockInfoDownloader 工作树。
4. [x] 写总览、统一交接模板和 9 份独立审计卡（CWP 报告通过 harness 回复返回；其他报告写入各自唯一结果文件）。
5. [x] 在 CWP 中以测试先行把下载路径默认改为 StockInfoDLSimple，并更新当前说明；保留被 writer freeze 拦截的历史入口为不执行的兼容记录。
6. [ ] 集中核对卡片边界、验收口径、测试和 Git diff；只提交本计划目录与明确授权的 CWP 代码/测试/文档文件，不暂存既有 `config/source_acquisition.yaml` 用户改动。

## 固定边界

- 对被审计仓库仅执行读取命令。禁止 `fetch/pull/switch/checkout/restore/reset/stash/clean/merge/rebase/cherry-pick/commit/push`，禁止改任何目标仓库的 Git 配置、分支、索引、工作树或生成文件。
- 审计卡不运行项目测试/构建/下载/LLM；只查现存测试、CI、PWF 收据。运行测试容易写缓存或运行产物，不适合纯盘点。
- 不读取、不复制、不哈希、不输出密钥及本机敏感配置的正文。只记录路径、Git 状态和必要的非敏感元数据。
- 不清理“看起来像临时文件”的路径；通过计划、创建/消费者、时间、哈希/重复性和 Git 历史证据分类后，仍把删除/回滚作为后续单独决定。
- 每个外部 harness 只负责施工卡指定的一个仓库，只能写其唯一交接结果；不能读取其他源仓库，不碰其他 lane 输出。
- Dayu 是用户明确指定的纯外部项目；只读盘点，绝无代码变更。
- StockInfoDownloader 被用户明确排除，不创建其审计卡，不合并其分支。StockInfoDLSimple 是当前和未来优先的 A 股 provider。

## 主要验收点

- 每个卡都有唯一 source repo、base/default-ref 规则、PWF/commit/worktree 检查法、敏感文件纪律、唯一交接目标和禁止操作。
- 结果能区分：已合并/仅落后主线/确有独有提交/patch-equivalent/本地 dirty/未跟踪/忽略生成物/部署分支/无远端无法确认。
- 结果报告不把 PWF checkbox 等同 Git 合并事实，不把文件名或旧计划的“完成”当成删除许可。
- 计划目录以外的目标仓库内容无变化；用户原有 CWP config dirty 改动保留且不暂存。

## 错误与约束记录

| 事项 | 处置 |
|---|---|
| 初次跨仓分支统计脚本把 behind 误标成 diverged | 丢弃该统计；按 `rev-list --left-right --count base...branch` 的第二列重新筛出 branch-only commits。 |
| PowerShell 批次命令输出曾截断/提前结束 | 改为各仓分支/状态的独立并行只读命令，并对关键仓库逐项检查。 |
| 普通沙箱的 Git ownership 与少量文件访问限制 | 使用单次命令级 `safe.directory` 的只读 Git 查询；未写全局配置。 |

## 下一步

做最终的路径/边界核对，确认 9 个结果接口互不覆盖、目标仓库零写入，且用户原有 source acquisition 配置没有进入暂存集。
