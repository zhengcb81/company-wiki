# Dashboard 的 owner 接口并线与改进计划

## 目标和唯一入口

将已验收的 Dashboard 依赖分批发布到各自 owner 的正式主线。解决三份反馈中已证实的业务缺口，保留正常的部分覆盖、未知结果和后置能力。本计划是本轮唯一入口。Dashboard 应用由其 D00 在自己的仓库维护。原收入审查循环继续使用自己的 PWF。

| 实施文件 | 独占写域 | 任务 |
|---|---|---|
| [company-wiki](company-wiki.md) | Company Wiki 来源目录、公开接口和定向测试。确需 PDF 端口时由解析 owner 单独实现 | 基础文档浏览、身份与来源市场、原件流、CN 发行人证明 |
| [filing-fetch](filing-fetch.md) | Filing Fetch 请求、FF 作业端口、部署合同和定向测试 | 作业接口发布、身份与来源合同适配、下载场景 |
| [revenue-forecast](revenue-forecast.md) | RF 作业与目录发布、RF 来源消费、研究输入和验收 | 作业/目录接口发布、MDB 入册、阿里收入研究、v2 演进 |

共用证据在 [findings.md](findings.md)。运行状态与签收写入 [progress.md](progress.md)。本计划放在 `docs/plans`，隔离于日常 `.planning` 的默认发现。在 Company Wiki 根目录的独立 PowerShell 进程选择本计划。

```powershell
$env:PLAN_ID = 'dashboard-owner-integration-2026-11-09'
$env:PWF_PLAN_ROOT = $null
& 'C:/Users/郑曾波/.agents/skills/planning-with-files/scripts/resolve-plan-dir.ps1' -PlanRoot (Join-Path (Get-Location) 'docs/plans')
```

## 当前阶段

| 阶段 | 状态 | 可以并行的工作 |
|---|---|---|
| P0 核对证据和责任 | complete | 三份反馈共 13 项，已按代码、提交和历史回执复核。启动时重取主线和实际部署指纹 |
| P1 发布可独立验收的接口 | complete | CWP、FF、RF 正式主线已发布，独审、CI 及本批 Dashboard 公开接口组合均通过 |
| P2 修复真实业务缺口 | **complete（三个 owner 均已并入并推送各自主线）** | CWP/FF 通用挂牌与来源期次匹配、SEC 20-F 原件驱动的关系登记、Alibaba/Bilibili 真实 US→HK 年报、Reader SHA 验真、生产来源目录 cache-only 身份复验、歧义/错市场负例及 MDB RF 公开目录读回均完成。当前 owner 主线：CWP `master`=`0fc56b25b89da9f3da5921ba64122d9745e1752d`；FF `main`=`f65e6ca75fbce0616e65870f0aea78b793ef883c`；RF `main`=`b005a179280ee19695578bdba9427b4dd44cdd73`。均为普通快进，无强推。CWP 快速发布 smoke 18/18、层边界定向回归 68 passed；FF 发布 hook 11 passed，精确 P2 候选的 `quality` workflow 有成功记录；RF 发布 hook 12 passed，完整远端 Actions 状态未确认。不得把本地 hook 代称完整 CI。支持范围限于可追溯关系，不承诺全市场历史覆盖 |
| P3 收口流式与发行人证明 | pending | Reader 流式端口与原生 PDF 端口可独立开发。CWP 总控串行接入可能共享的公开入口，先流式后 canonical。基础 browse 与 MDB 入册不依赖本阶段 |
| P4 全能力组合验收和消费切换 | pending | P1 公开接口的隔离组合已通过。后续由 Dashboard D00 在自己的发布计划接收确切修订，再按实际启用的 P2/P3 能力验收与切换 |

## Next Step

P2 已分别并入并推送 CWP `master`=`0fc56b25b89da9f3da5921ba64122d9745e1752d`、FF `main`=`f65e6ca75fbce0616e65870f0aea78b793ef883c`、RF `main`=`b005a179280ee19695578bdba9427b4dd44cdd73`。此前“本地分叉、4 个同写域未提交改动”的文字是 CWP 合并前快照，现已处理。P2 的 SEC 20-F 来源证明、Alibaba/Bilibili FY2025 US→HK 请求、原件 SHA 验真、零下载重放、身份负例与 MDB 报告读回均见 [P2 E2E 收据](validation/p2_cross_market_e2e_receipt.json)。模块化解耦按 D5 冻结验收范围已 ACCEPTED；这表示跨仓通过版本化公开接口协作，不表示模块间零依赖或未来不会发现缺口。下一阶段进入 P3：Reader 流式端口与解析层原生 PDF 端口只通过 CWP owner 公开边界接入，不把解析实现泄漏给 FF/RF/Dashboard。P4 是 Dashboard 按实际启用能力做组合验收与消费切换。P2 不表示 P3/P4 全计划完成。

**唯一下一步：P3**。按 CWP owner 公开边界收口 Reader 流式端口与解析层原生 PDF 端口；随后由 Dashboard D00 对实际启用能力做 P4 组合验收与消费切换。

## 依赖与发布顺序

```text
CWP 基础浏览 ───────────────────────────────────────► Dashboard 文档卡
CWP 身份 + 来源市场 ─► FF v2/ff-job ─► RF 阿里输入 ─► Dashboard 阿里链
RF 作业/目录端口 ─────► MDB 既有报告登记 ────────────► Dashboard MDB 列表/详情
CWP 来源 Reader 流式端口 ───────────────────────────► Dashboard 原文传输
PDF 解析公开端口 + StockWiki 证明公开协议 ─► CWP canonical ─► Dashboard 跨挂牌浏览
```

发布接口和切换运行部署分开执行。Dashboard 每次切换前比对实际启用的接口清单。当前配置若还使用 stream/canonical，基础浏览发布后可在临时环境验证，整套 CWP 配置等这些接口在同一新修订可用再切换。仍可按已证实的功能分别关闭工作项。身份归属、来源状态和报告资格各由 owner 负责，Dashboard 消费路径无关的公开 DTO、CLI 或导出。

## 实施与验收约定

1. 每条线从实际远端主线建独立工作树，明确可写文件和要移植的补丁。工作树里已有变更、运行产物和生产配置交给各自所有者。CWP 本地 `62602102a` 有混合工作，按独立补丁发布。RF 同样从当前主线核对候选依赖闭包。
2. 先把原始故障和一条非目标公司对照写成离线回归，再修 owner。以实际公开命令、隔离配置、临时目录及受控 provider/model 验证。仅在正式业务请求已有真实下载意图及预算时采集实件，保留原件。夹具复验后恢复测试目录。
3. 大节点只做三次独立复核。第一次核对各 owner 的发布候选、现有协议和隔离测试。第二次核对阿里来源与 MDB 入册的业务证据，以及流式/CN 边界。最后对实际组合及消费切换独审一次。小补丁使用定向测试。正常 Git 钩子保持快速，发布候选用现有 CI。
4. 交接写明 owner 和用途、完整代码 SHA、协议版本、部署根的非敏感标识、已过测试及关键证据、真实运行范围、还待处理的缺口。产品可用与发布状态分别记为候选已验证、主线已发布、部署已切换、组合已验收。已有证据可直接复用。
5. 通过后各仓按正常方式快进或合并推送，验证远端包含确切修订。Dashboard D00 在自己仓库更新和回滚 pin。遇到兼容回退先回到前一已验证版本或回退部署配置，运行产物与已登记原件保留。各 owner 负责自己新增的持久写入及恢复。

## 全计划最终验收（P1–P4；不作为 P2 单阶段退出条件）

本节是整体计划终验收。P2 的退出条件以阶段表和 P2 收据为准；流式/PDF 端口、实际 Dashboard→RF 消费、目录 UI 切换属于 P3/P4，不应倒灌为 P2 未完成。

- CWP 基础浏览从正式发布修订在 Dashboard 显示，分页和指定版本重开对应同一 SourceRef，物理目录迁移后仍能重开。流式同源验真、取消、上限和 Range 能力与实际部署一致，CN 证明通过解析端口且保持历史 SEC 行为。
- 阿里同一部署可区分 US/HK 挂牌、真实财年、原件状态和 provider 故障。一条真实合格来源贯通 FF 到 RF，可证明实际来源、如实成本和报告可读。其余路由都有可验证的正确结果或明确拒绝，不以六条都下载为成功。另一家双上市及 MDB 控制例回归。
- MDB 已完成作业按 RF owner 的成功发布合同幂等登记并从 Dashboard 读到同一报告。若原始历史证据确缺，明确未入册原因，RF-2 保持开放。
- FF 已覆盖自然下载的受控路径，实际下载证据另列；未发生时记 NOT_RUN。RF v2 与 EXT-02/03/04 有独立排期和证据标准，Range 继续以当前实现声明，均独立于本轮基础并线。
