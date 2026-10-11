# W08 / Post-W03 三家公司来源环境准备

冻结时刻：2026-10-11T01:13:42.893071+00:00。**来源准备执行 PASS；资料资格仍 PARTIAL，研究尚未执行。**

公开交接：[source_environment_handoff.json](C:/Users/郑曾波/.codex/worktrees/m3-acceptance-20261010/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/post_w03_original_research_2026-10-11/source_environment_handoff.json)。CWP source HEAD `0f7540b50e404eb1083192ad5412b9aa6fa4d4bc`；as-of 2026-10-08。

## 实际结果

| 公司 | 原件真实Ref/字节读回 | 原verified patch/evidence原样转用 | 实际capture | 来源就绪 | 新环境占用 |
|---|---:|---:|---:|---|---:|
| CN-688012 | 7/7 | 6 | 10 | PARTIAL | 724,820 B |
| HK-00700 | 14/14 | 13 | 16 | PARTIAL | 1,122,375 B |
| US-MSFT | 11/11 | 10 | 14 | PARTIAL | 956,484 B |

8个register、29个source-facts、3个public SourceVersionReader读回capture共40次真实命令，全部exit0且input/output完整。每条命令原输入/实际消费SHA、stdout/stderr和实际capture ID在各run roles/coordinator/commands；没有自造HandlerResult或旧预测复用。

财报读回使用filing_reuse；其它资料使用source_export。每个新Ref由新库query_ref实际签出，并与已冻结真实旧Ref一致。29份证明按get_verified_assertion(old_catalog.reader, reader=steady)取真实旧patch/evidence，source-facts用新Ref实字节验真，读回再比对完整原proof。没有编造日期、locator、observed_at或新证据。

## 仍保留的真实缺口

- CN FY2024 (`3273711fbb79`)：无旧verified source-facts，市场/出版日期unknown。原件可验真实读，不等于as-of正式资格完整。
- HK 2026Q1 (`ef3baa5008e1`)：无旧verified patch；原侧栏出版日期2026-05-13、真实字节读回有效。保留证明来源差别，不新增人工许可。
- HK September overview (`a9b0a5d6c68d`)：原proof明确出版日期null，继续unknown，不由标题猜9月日期。
- US FY2026 10-K (`2c86b6365b53`)：无旧verified patch；原生SEC capture已有出版2026-07-29，filing_reuse真实读回通过；不伪称已补旧patch。

## 隔离与复原

70个保护文件（生产/旧3catalog DB/config/cache及新scope/config等绑定）前后SHA一致；32原件size/mtime一致。外层未重复全额hash原件，实际SHA由公开source责任层验证。保护证据：`C:\Users\郑曾波\AppData\Local\Temp\mW03-ahg078jp\CN-688012\work\source-owner\protection-after.json`。

新原件复制0B；没有整库copy、整湖scan、SQL reactivate、旧目录/Dayu代码/侧栏改写。US三个Dayu季度accession group按现有public登记语义读取原件和附件，声明受限组15文件/51,772,580B；并未复制这51.8MB。原错market=HK薄侧栏字节原样保留，新source facts沿原US/CIK/period证明转用，当前filing_reuse由source层验证。

每家公司只有新catalog/owned work及其roles/coordinator日志被写入；scope/run/cohort、源码和安装未修改。新环境小于每家公司256MiB上限。0模型、0外部provider、0新增费用/token。此状态不覆盖母账旧unknown hold，不称旧全项目成本0。

owned mW03树留给下一fresh executor和四路审查；完成后由ROOT按初始不存在基线删除仅此owned树。当前不可提前清除：尚有研究未执行。

## 下游入口与责任

ROOT现在可派三家独立fresh RF executor，沿各已冻结scope的真实installed RF→FF→CWP入口。消费者通过source_items中的Ref2/config binding与公开sourceport使用原件；不能直接拼source_owner_registration_locations。物理定位仅供来源owner或审查复核。

本任务没有86页SSE JSON import/project，没有新解析/摘要/模型运行，也未读任何旧预测或执行研究结论。那些步骤继续由各fresh executor按既有W08/预算执行，不能用本来源PASS代替RF全流程/研究完成。
