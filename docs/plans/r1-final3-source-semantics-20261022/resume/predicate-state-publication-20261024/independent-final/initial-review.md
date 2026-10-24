# W08 measure/guidance 独审：需要修复

**本轮有限节点不能 PASS。** 独立17个中性断言实跑 **8F / 9P / 0E，3.07s**，实际W08 import、共享policy、公共selector、citation/model端口均来自指定工区；10份源码/原测试前后SHA稳定。原77和原20没有改动，staged预算merge与unstaged语义delta均未写。源码冻结/全部实际输出见 `initial-review.json` 和 `semantic-probes-red.json`。

## 两类共同根因

### W08-MG-01（P1）：实际数量与未来状态的责任分裂

`We anticipate/project our reactor volume of 143 kL.` 以及“公司有望/力争反应器总体积增加至143kL”均落入实际经营观测 `operating_quantity`（中文还带metric_change），而原文明确为期待/目标。相同框架真实已达数量正控通过。measure的unrealized gate与guidance的expectation语法各有一份不一致词表，这是共因，不应再给每条句子补例外。

### W08-MG-02（P1）：expectation未绑定收入自身谓词和期间

下面四个原文都实际输出 `source_revenue_guidance`，且该reason进入真实EvidenceSpan：

- `We expect customer renewals to improve and our subscription revenue is USD 143 million.`
- `We expect customer renewals to improve while subscription revenue has reached USD 143 million.`
- `We expect subscription revenue to have grown by 14% last quarter.`
- `We will announce that subscription revenue increased by 14% last quarter.`

前两条借了另一谓词的expectation；后两条是过去期间估计/未来披露过去事实，不是未来收入指引。应由同一assertion/state/time owner识别收入自身未来谓词与时间，不是继续堆一个“was/is/reached”负词表。原文不删、单位/金额不换算，真正forward/passive guidance必须继续保留。

## 正控与审查边界

真实已达英文/繁体数量、英文/繁体未来指引、被动式指引、issuer前提闭包，以及第三方主体/不同业务/错误forward方向不借前提，共9个正反控制通过。原字段没有forecast-input/modality，因此报告只按真实reason/purpose、source spans和task成员/原文判断，不编造规范化数字或机器字段。

预算合入由另一独立子agent交叉核，报告另见 `budget-merge-review.md/json`；它的84P不抹去这里的8个失败。跨页祖先、96/48000选材多样性、年报14、真实付费摘要及研究仍OPEN。本审查者曾参与旧qualifier基线，本轮只独审ROOT新增measure/guidance delta，不对自己旧实现再给完整独立认证。

## 失败证据和恢复

`independent-red.txt/xml` 是原始真实RED。另有1个本审查捕获层warning：子进程stdout为主机GBK，父进程尝试UTF8解码；实际观察始终直接写UTF8 JSON，17个断言结果没有丢失，0E。归档的后续测试runner只改为捕获bytes，不改数据/期望/断言；未据此扩跑产品。实际执行版本和后续版本SHA均已保存。

原探针/断言分别封存为 `semantic_probe_frozen.py.txt`、`independent_semantics_executed_red.py.txt`、`independent_semantics_test.py.txt`。原观测与补全task原文的正式观测均保留。独占母`.planning/w08-mg-independent-20261024`和本次pytest重定位根均恢复不存在，未删W08旧失败/未跟踪材料。

**至此停止读取/测试产品，等待ROOT共享owner重构后按同一17断言有限复审。** 未改源码、原测试、Git、配置、W09/W11；0外部网络/模型/下载/原件。
