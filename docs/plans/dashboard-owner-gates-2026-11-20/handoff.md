# Dashboard 公开读取修复交接

后续五项已完成接口修复和正式资料读回，详见 [F2 验收](f2-acceptance.md)。[F1 回执](followups.md) 保存修复前的基线。下方保留阶段 E 的运行包和回退记录。

## 当前版本与数据

- CWP 正式原件包含阿里旧港股年报以及药明 W12 依赖的七份原件。原生引用公开口和三表复用以 `3fadcbe07` 或后继为准。StockWiki 主线 `7ab8778` 已发布阿里和 MDB 对应的研究关联与六条原文引文，本仓无 Git remote。
- FF `fcacf2e4` 用正式 CWP 库读回中微 FY2025 三表八项。RF 使用 `f1af2193` 公共入口成功在正式目录登记原 W12 作业和原报告，二次入册复用同一结果。
- Dashboard `main@007787a` 已推送，使用业务主库与 r25 的公开身份配置通过真实组合。新增运行配置见 [Dashboard 交接](../../../../investment-dashboard/handoffs/owner-requests/DASHBOARD-F2-READBACK-20261121.md)。现役 `48766` 使用阶段 E 运行包，首个正式指标快照已在该运行数据根读回。新读接口的运行包切换跟随 Dashboard 自己的部署节奏。

## 运行时接线

- CWP、FF 和 RF 使用各自公开 CLI、受管解释器和当前代码版本。Dashboard 配置的代码根与数据根分别绑定。旧 B37 配置指向已移除的工作树。现行原件证据与目录数据仍由原配置的资料库提供。
- CWP 的 StockWiki 证明配置只属于发行人资料列表。已知文档版本直接从 CWP 的精确公开入口读取。浏览器内存预览和原件有界流式读取各自使用已有资源边界。
- StockWiki 已快进本地 `master@c1eeb99d`，本仓未配置 Git remote。引用配置由 StockWiki 在读取时检查一次。研究能读、引用配置不能用时，一次响应返回研究和具名诊断。不同 StockWiki／IQS workspace 的实体或挂牌 ID 以各自公开身份面为准。
- RF 用 `d80c39b2` 或后继，按已验证的发行人、挂牌及原件范围登记真实已有作业。历史原件可由同发行人的已验证历史挂牌绑定。核对原作业和报告 SHA 后走 `import-rf-job`，同一已登作业返回原报告和快照。
- IQS 现已使用本地及远端 `master@296ab84`，先切换正式 `8766`。发布目录在 IQS 的 `.runtime/iqs-e20-296ab84`，正式 `scripts/open_dashboard.py` 使用原 `config/dashboard.local.json`、原独立 UI、`--port 8766 --no-refresh`。发布目录是代码根，配置继续指向原快照与工作区。名单命令由所属模块处理版本和幂等冲突。
- Dashboard 本地及远端 `main@f5259812` 已切换 `48766`。实际发布目录是 Dashboard 的 `.runtime/dash-e20-f525981`，含 `backend`、`contracts` 和 `apps/web/dist`。使用原 `.runtime/f4-feedback/read-listener` 数据根、现役 r25 身份、IQS `http://127.0.0.1:8766` 与 `UNI_IQS_APPROVED_214_20261025`。两仓发布目录各有 `listen-<port>.receipt.json`。相同业务范围内再次发布时，从实际包预演网页和固定结果后切换。
- 指标发布使用 Dashboard 本机 data-dir 中的定版快照。具体接口和复现实例见 Dashboard 候选的 `handoffs/m7-owner-publication-20261120/handoff.md`。

## 真实覆盖

- IQS r25 已定位药明和 MongoDB，公开目录暂无正式结果、历史为 0。阿里目前缺 r25 对应挂牌，页面使用单独的空态。
- 首批发布覆盖中微八项指标。名单其他 214 家展示待核。扩大范围时继续使用正式 FF 报表与同一批次的固定名单分页。
