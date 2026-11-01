# C — H1真实源选材v1观察（非最终版本/非整公司验收）

只执行一次canonical；没有重复解析/整批，没有模型POST、下载、RF或CatalogStore构造。输出在 `.planning/architecture-quality-20261101/real-acceptance/`。随后ROOT通知grammar-unavailable还需R4修复，因此本v1是实际版本观察，不代签后续源码。

## 版本与资源

- 实际观察 `source-passage/5`、`statement-grammar/2`；宿主NLTK3.10.3、jieba0.42.1，全部原文保持原语言。
- Git观察基线1909286a只是文档HEAD，实际产品为当时未提交工作树。425个源码/语法资源的前后聚合SHA都为 `e4c08e425f4479d60bc8888675fea31c504311de746072ac8c78c8d46a26689b`，运行中未变化。
- 精确组件原字节/LF SHA、literal版本、包版本见 `h1-current-v1-runtime-components.json`。
- 运行时间 `37.394217s`，在90秒父deadline内。此前旧源码canonical曾记录7.019s；两次不是同机负载/相同算法的受控基准，不能直接归因为5.3倍回退，但新语法的实际开销应保留观察，不能只汇报召回提高。原工作 `15,998,066/16,000,000`、exhausted=True、complete=False，原112上限未提高。

## 真实结果与明确范围

- 199/199页；4224物理source units，2873已知候选；112span、70group/70view。captured prepared units为4473，包含内部carrier，不能与4224物理unit混作同一计数。
- 12/12冻结原文unit表示通过：p12三具体业务单元、既有D&M原句、p14完整8成员。p12第一项为直接span，另两项同属原生carrier `da5ec7ff...a435`；p14原519字符carrier `1f5e297e...b813`仍含全部8成员，D&M保留直接原句。
- 共111个native成员，逐carrier坐标切片重算SHA全部正确，invalid=0；引用组无missing selected ID，全部source ID一致，handler对所有selected material真实replay通过。
- 7个单独标记为合成的语法NP/第三人称控制全通过，不能把它们计入真实样本召回。
- 结果仍 `partial/coverage_complete=False`、2761 omitted候选、634 dropped_financial，不能写成全文已处理或整公司研究完成。
- selected material SHA `04ad738e14049fafab37d53aa3941e0c1a929ceee1b9a050bd57adbf9327f09c`；decision digest `052e9423584e2dad4cd1fd62c84e1320e0dbaa4bc2e8d5279e51390e79a230b0`。

## 非零退出的准确原因：诊断比较器误判SHM mtime

原 `h1-current-v1.json` 和真实非零exit保留。v1 helper把所有文件的mtime与内容一起比较，只有SQLite SHM的mtime变化：

| 文件 | 大小 | 前后内容SHA | metadata |
|---|---:|---|---|
| catalog.sqlite3 | 3,309,568 B | 13d5fec8...ed5f840，相同 | mtime相同 |
| catalog.sqlite3-wal | 230,752 B | e77a4a9b...79f2d1，相同 | mtime相同 |
| catalog.sqlite3-shm | 32,768 B | af58611c...3f6d3b21，相同 | 仅mtime变化 |

没有改写旧receipt或恢复mtime。修复纯比较器 `observation_checks.py`：DB/WAL/原件保持严格byte+mtime；SHM仅允许同bytes/SHA/existence下的mtime同步变化，其它metadata/内容变化仍失败。10个内存fixture正反例通过0.22s（SHM mtime正例、SHM内容/大小/其它meta、DB/WAL/原件mtime/内容反例以及context映射），Ruff通过。

对同一份已保存观察生成 `h1-current-v1-observation-addendum.json`，新比较器storage invariants通过；**没有重跑37秒真实解析**。v1没有保留原件物理stat前后值，只有SourceVersionReader的实际字节/身份校验，不能伪补原件mtime证据。

## 9个旧context pair仍OPEN

v1只用旧complete support quote找当前span，均未匹配。这个结果不能证明未选择，也不能证明承诺归属修好：新范围可能拆分/合并，且v1未保存全量new span→original-member和citation-view索引，只有总数及12目标的局部数据。

已从原R4冻结support/context span抽出native成员IDs；直接原span按相同原生identity字段确定性重算unit ID，basis逐项记录。与v1当前可用材料比较后，9项均明确 `OPEN_CURRENT_MEMBER_OR_VIEW_INDEX_NOT_RETAINED` / previous_bad_context_observed=null。旧receipt的NOT_SELECTED标签由addendum纠正为未确认，不改旧字节。

未来runner schema2已补紧凑span/original-unit/member SHA索引和group support/context索引。纯fixture证明：原quote拆成新carrier后仍能靠original IDs查出错误context；缺索引只能OPEN。后续源码本来需R4重新验收时再采集这些索引，**不为修诊断标签重复本v1**。归属仍须集中语义审查，未见旧pair不自动PASS。

## 证据与清理

- 原观察receipt SHA `245da7a23cd60873c78a8255d59812f476d29c12581b442a6d36bbe9ca3bf82e`。
- v1实际runner/cases在本次诊断改动前压缩保存为两个小gz，注明是执行结束后观察，未冒充执行前cryptographic snapshot；无需解压恢复演练。
- 无原件复制、无数据库迁移、无收费账变动；仅小JSON/代码证据。外来WIP、生产config、R3/R4封存未触碰。
- 下一步由ROOT决定：R4 unavailable uncertainty修复和A复审后，新的有效源码做一次必要current source检验，再决定正式摘要/恢复/RF阶段；本报告不自动启动Paid。
