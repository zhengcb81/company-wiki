# G-A1：FMP 原件入库与未知公开日期（施工细则）

前置：G-A0已完成JSON字符串转义/UTF-8原字节locator和lineage回放。本卡归company-wiki主线owner，其他仓只读；不启用生产Worker，不调用付费API，不接触原始文档清理。

## 现状与职责

- ET `4924d57` 的 FMP `/2`为26字段：旧24字段的published_date换为call_date、publication_date、as_of_cutoff_verified。生产者golden保存在tests/fixtures/transcript_fmp；它是离线合成fixture，不能冒充真实FMP200。
- CWP当前工具合同只收24字段、HTML/TXT、无query的URL。候选filing_date必填；canonical writer把入库成功等同于历史as-of可复用。必须拆开来源保存与历史使用资格。
- SourceResolver对未知公开日期已经返回AMBIGUOUS；SourceVersionReader.query_local按as-of过滤未知日期。保留这种语义。按精确source/document ID预览和实读hash是另一个层级，不应伪造公开日期去通过resolver。
- ET FMP canonical文本算法为原content把CRLF/CR变为LF再strip；不会折叠行内空白。CWP material为规范化定位文本，带尾换行。两个hash不是同一对象，不能拿material.text_sha256直接替代provider canonical hash。

## 实施顺序（只在以下两个大节点验收）

### 节点一：纯合同与日期/正文语义，先RED再实现

1. 用原producer golden写解析/身份/期间测试；legacy24字段兼容保留，FMP26字段严格限定provider/MIME/extraction版本，不收任意扩展字段。
2. FMP URL仅允许canonical HTTPS主机financialmodelingprep.com和/stable/earning-call-transcript，以及恰好symbol/year/quarter的单值参数。必须绑定当前请求；拒绝apikey、userinfo、fragment、额外/重复query、错ticker/FYQ。勿输出完整原件或凭证。
3. 验证原JSON记录的symbol/year/period/date绑定返回合同及候选身份，而不仅验证外层envelope；字节SHA、原件大小和provider canonical内容hash/大小分别验证。
4. publication_date=null保留null、as_of_cutoff_verified必须false；call_date单独验证但不写进published_date。已知公开日期才可验证历史cutoff；不从retrieved_at、文件mtime、通话日期推断公开日期。
5. 类型化候选允许电话会议的filing_date=null，其他文件原有必填约束保持。所有日期使用点检查nullable，不用空字符串/1970日期等占位符。既有CLI字段集合保持，nullable值从同一入口传递。
6. 原件暂存后缀为.json；独立audit字段保留call/publication/cutoff和provider canonical hash，不修改原JSON也不写翻译。未知日期文件名使用无日期标签，防scanner从文件名猜出通话日期。

### 节点二：存储与使用资格拆开，正式CLI端到端

1. canonical writer postwrite检查来源身份、期间、indexed version与已提交字节；未知公开日期也能保存成功。返回的resolution仍应如实AMBIGUOUS/unknown publication，禁止强改为REUSED_EXACT或设置capture_ready=true。已知日期旧流程继续验收。
2. 一次E2E：producer golden →正式stdin import CLI →catalog →按精确SourceRef verified read →JSON locator回放；assert publication仍未知、历史as-of查询不把它当可复用来源。原件后缀/hash/bytes不变，无翻译文件。
3. 重复导入零重复raw/sidecar；错误原SHA、provider canonical hash/bytes、公司、FYQ、日期、query参数和JSON截断均拒绝且不留下raw/sidecar/staging。未知日期记录不因重复导入被改写为已知。
4. 所有测试在独立tmp wiki root与配置/database进行，finally关闭catalog及子进程，删除该次run新建文件恢复测试目录；不写生产config/raw。保留fixture本身原字节。G-A0/legacy/importer/CLI/canonical writer相关回归在这一次节点包一起跑。
5. 收据写入PWF，正常commit/push并确认短CI绿。然后才进入FF两worktree单owner汇合，不凭CWP importer通过声称FF→ET→CWP完整下载链已完成。

## 交付边界

- 本卡不重写RF/StockWiki的reader；它们消费正式SourceRef及metadata，历史未知public cutoff不得在上游伪造。
- 不新增人工授权/签收文件，不增加逐步骤门禁。可修复代码根因，不删除反例或放宽测试以隐藏日期错误。
- 下一依赖：G-A FF汇合，随后NarrativeBundle/G-C跨仓消费，再G-D派生空间处置。生产并发仍default-off，待真实大节点吞吐/恢复验收。
