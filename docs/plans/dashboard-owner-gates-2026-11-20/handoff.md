# Dashboard 公开读取修复交接

## 运行时接线

- CWP、FF 和 RF 使用各自公开 CLI、受管解释器和当前代码版本。Dashboard 配置的代码根与数据根分别绑定。旧 B37 配置指向已移除的工作树。现行原件证据与目录数据仍由原配置的资料库提供。
- CWP 的 StockWiki 证明配置只属于发行人资料列表。已知文档版本直接从 CWP 的精确公开入口读取。浏览器内存预览和原件有界流式读取各自使用已有资源边界。
- StockWiki 已快进本地 `master@c1eeb99d`，本仓未配置 Git remote。引用配置由 StockWiki 在读取时检查一次。研究能读、引用配置不能用时，一次响应返回研究和具名诊断。不同 StockWiki／IQS workspace 的实体或挂牌 ID 以各自公开身份面为准。
- RF 用 `d80c39b2` 或后继，按已验证的发行人、挂牌及原件范围登记真实已有作业。历史原件可由同发行人的已验证历史挂牌绑定。核对原作业和报告 SHA 后走 `import-rf-job`，同一已登作业返回原报告和快照。
- IQS 现已使用本地及远端 `master@296ab84`，先切换正式 `8766`。发布目录在 IQS 的 `.runtime/iqs-e20-296ab84`，正式 `scripts/open_dashboard.py` 使用原 `config/dashboard.local.json`、原独立 UI、`--port 8766 --no-refresh`。发布目录是代码根，配置继续指向原快照与工作区。名单命令由所属模块处理版本和幂等冲突。
- Dashboard 本地及远端 `main@f5259812` 已切换 `48766`。实际发布目录是 Dashboard 的 `.runtime/dash-e20-f525981`，含 `backend`、`contracts` 和 `apps/web/dist`。使用原 `.runtime/f4-feedback/read-listener` 数据根、现役 r25 身份、IQS `http://127.0.0.1:8766` 与 `UNI_IQS_APPROVED_214_20261025`。两仓发布目录各有 `listen-<port>.receipt.json`。相同业务范围内再次发布时，从实际包预演网页和固定结果后切换。
- 指标发布使用 Dashboard 本机 data-dir 中的定版快照。具体接口和复现实例见 Dashboard 候选的 `handoffs/m7-owner-publication-20261120/handoff.md`。

## 证据缺口

- 本机现役快扫使用 r25 身份工作区。资料、研究和 RF 的已验证业务主库读取作为独立配置联调；两个 StockWiki workspace 的历史实体和挂牌键需要各自权威确认。
- 中微三表样本存在于 FF 冻结交接中。生产目录的报表版本尚未登记。现有零成本复用路径仍显示空数据，避免浏览触发采集。
- 阿里已有研究引用的原件与当前公开归属验证通过的年报是不同版本。引用所在原件的归属事实待补。保留旧引用原固定版本。
- MongoDB 的原 10-K 已从发行人目录及精确原件接口读回。老研究引用的 HTML 定位仍需该文种支持的定位方式，不能使用旧的 PDF 页码路径。
- 药明 W12 已按真实原作业隔离登记可重放。生产 RF 目录未新增该次登记。
- 215 家真实名单的指标隔离对照只有一家八项数值。其他 214 家待核，缺失不会被解释为零或通过。涉及用户公司池的物化测试目录已清理。交接记录保留参数和结果摘要，生产发布采用实际 owner 输出。
