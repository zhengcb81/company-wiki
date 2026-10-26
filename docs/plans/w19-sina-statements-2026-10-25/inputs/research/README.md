# 新浪 A 股三表：实测调查（2026-10-25）

## 结论及范围

可以做确定性的免费数据工具，不需要 LLM、PDF/OCR 或浏览器自动化。已直接检查用户给定页面、实际加载的新浪 JS，再有界调用该 JS 使用的公开 JSON 接口。这里的“API”是本项目对网页后台数据的封装，不是新浪承诺稳定的商业 API，也没有承诺覆盖全部 A 股。

- 页面：[中微公司财务摘要](https://vip.stock.finance.sina.com.cn/corp/go.php/vFD_FinanceSummary/stockid/688012/displaytype/4.phtml)。页面本身是动态壳，静态 HTML 没有三表数据。
- 实际脚本：[cncw2022.js](https://n.sinaimg.cn/finance/2022/pc/cncw2022.js)，本次 SHA `5a79412a56ba365e41fc8a5efa1d4bfc9ead2aae86491f8fad382a52096eb339`。
- 实际接口：`https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022`。
- 不需要 API key 或登录。此次成功不构成长期可用性/覆盖保证；403/429、空数据、接口变化应诚实返回。
- 仅观察数据格式及可用性，尚未与官方财报逐值核对，**不是财务数据正确性验收**。

## 真实请求与结果

参数：`paperCode=sh688012`，`source=lrb|fzb|llb`；`type=0` 全部、`4` 年报、`3` 三季报、`2` 中报、`1` 一季报；`page` 从 1 开始，页面 JS 默认 `num=10`。年报过滤 `type=4,num=2` 也已实测成功；没有假设无限大 `num`。

| 探针 | 实际结果 | 不能据此推断 |
|---|---|---|
| 中微利润表 lrb | 4 页，共 36 个唯一报告期，2016-12-31 至 2026-06-30；各期 77 行 | 36 个完整季度，或所有行都有数值 |
| 中微资产负债表 fzb | 4 页，共 33 期，同首尾日期；各期 141 行 | 与利润表逐期完全对齐 |
| 中微现金流量表 llb | 4 页，共 36 期，同首尾日期；各期 64 行 | 三季报是独立第三季度数值 |
| 中微 lrb 第 5 页 | HTTP200 / result.status.code=0 / data=null | 网络故障或完整历史为空 |
| 美的 sz000333，lrb，num=1 | 报告数 79，返回最近 1 期；营业总收入与营业收入不同 | 两个科目可互换/相加 |
| 招行 sh600036，fzb，num=1 | 报告数 102，144 行 | 可使用工业公司的固定行号 |
| 平安 sh601318，lrb，num=1 | 报告数 90，76 行 | 保险收入就是工业营业收入 |
| 无效示例 sh999999，lrb | HTTP200 / code=0 / data=null | HTTP200 即业务成功 |

全部三表初次历史采集为本例 **12 个请求**，不是固定所有公司 12 次；其他公司按各表 `report_count` 和实际页推进计算。此研究另有空页、年报过滤、三类公司和无数据反例。`capture/manifest.json` 的 20 次/2,634,389B包括网页和 JS；前期形状探查还发生过网页/JS/API读请求，不把 20 次说成整个会话全部网络次数。无收费请求、无凭证读取、无生产库读写。

## 数据含义与必须解决的问题

1. **直接保留原值。** `item_value` 是十进制字符串、null 或空字符串，不能走 float，不能把 null/空/0 混成一个值。前端 `Yaccuracy`/`Yuniter` 会按数量显示万/亿，truthiness 还会隐藏某些零；工具不复用前端显示文本。`item_precision=f2` 是显示精度，不是单位；`ps4` 见于每股收益，不能统一当 CNY 金额。
2. **科目由代码及原标签表示。** 保留 `item_field,item_title,item_source,item_group_no,item_display_type,item_precision`。fzb/llb 中有空 `item_field` 的分组行，不能把它们当金额，也不能使相邻数值错位。所有科目原样可查；只对有证据的常用字段建立小映射，不要求固定 77/141/64 行，不只抽营收/净利。
3. **报告期与数据基准不同。** 顶层 `report_date` 带 `date_value,date_type,date_description`；报告本身带 `rType,rCurrency,data_source,is_audit,audit_opinion,publish_date,update_time`。样本中利润/现金也写 `rType=合并期末`，所以不能用它判定“时点”。资产负债表是时点，利润/现金流须核官方样本确认累计期间；如提供单季派生，需相同币种、主体、会计版本及相邻累计期并有两个来源引用，缺条件返回 gap。
4. **历史知识时点不能伪造。** 例如中微2023-12-31利润表的本次 `publish_date=20250418`；2025年末 fzb 的 `publish_date=20260820`，而同年末利润/现金为20260331。保留 provider 原值、`update_time`、本次 `retrieved_at`，不能修成推测的最初披露日。当前接口不提供所有历史修订序列，不能声称支持任意历史 as-of 回测。当前快照查询与严格历史知识时点查询必须区分。
5. **第三方数据和官方原文分开。** `provider=sina_finance`，不能借 `import_original_staged` 现有 `provider=official` 路径而标为公司官方发布。原件仍留存；不替代官方年报、不自动让该数据签收下游预测。抽样核对单位、期间和数值是施工 C 节点责任。
6. **三表不同缺口。** 页数/日期集合分别维护，分页重叠、重复页、缺期、count变动、同键不同内容均要显式报告，不按一个表的 count 强行补全其他表。
7. **A 股范围。** 已探 SH/科创板和 SZ；尚未验证 BJ、退市/更名、特殊金融主体、合并/母公司可切换。代码前缀来自一次既有证券识别，不靠数字前缀猜，不为不支持的市场乱试供应商。

## 现有架构调查

- FF 主线 `e0d96426445e4b93bc6cc7a6e6014996ad0a777d`，只读检查 tracked clean。`scripts/fetch_filing.py` 已有 company-wiki identify、`ff_configuration.py` 配置、`ff_process_transport.py` 有界子进程；不应让新浪工具重做公司身份库。
- CWP 主线 `243993d2c9e12c2a9cb6e2b728e547928607abff`，精确 [CI40195639414](https://github.com/zhengcb81/company-wiki/actions/runs/40195639414) success；主线财报来源/共享引擎仍在施工。
- 当前 source catalog schema 为1.2.0，`CatalogStore._initialize` 对当前版直接验证后返回；新增表必须进入唯一 DDL/版本迁移链，不能只加 CREATE 后假设老库自动升级，也不能查询时造库。
- `CanonicalSourceWriter` 负责不可变原件、SHA、去重、SourceRef。`DownloadCandidate` 目前要求单一 fiscal_year，`import_original_staged` 则把 provider 固定为 official；多年度第三方 JSON 不能假填一个年或冒充官方，需小范围泛化已有 writer 的“有来源的原始字节”入口，仍调用唯一 `_commit_staged`。
- 查当前 source catalog 未见独立财务三表规范化数据表；叙述引擎中的 financial-only 检测不等于此处要建的历史数表。

## 证据、复现及空间

- `probe_public_source.py`：研究脚本，最多24请求/12MB，逐次有界读取，无重试风暴；仅显式命令运行，不加入CI或产品。
- `capture/manifest.json`、`observations.json`：URL、参数、状态、SHA、抓取时点及抽样字段。
- `capture/*.json.gz`：18份原始API响应的无损压缩快照，共 **175,785B**；验证以解压后的原字节 SHA 为准，不重格式化供应商响应。
- 中微全历史基础行数为 `36*77 + 33*141 + 36*64 = 9,729`（含分组/null）；这些是源侧行数，不是9729条经过审计的金融事实。
- 压缩夹具大小不是未来生产库的大小。施工必须实测单份原始JSON及共享SQLite增量，禁止每格/每次读都复制原响应；不重新生成PDF/MD/LLM摘要。

开工卡：[W19-SINA-STATEMENTS](../construction_card.md)。此卡是用户新要求的第四张独立卡，不修改已派发三卡的正文/接口。
