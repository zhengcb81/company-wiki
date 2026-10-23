# W09 ROOT v3 独立内容整合验收：有限通过

**本节点通过，未发现需继续修复的实质问题。** 独立中性正负控与真实 CLI 共 **16P / 0F / 0E / 0skip，pytest 4.45 秒**。本报告没有重跑或累计 ROOT 的62项/8subtests，也不代表 W08 新摘要采用、W12 公司四审或经济质量通过。

绑定交接 JSON SHA `39ec769279845512db78c0658ec4b32155437f1f65ae170c81543b49daff3d59`，最终 v3。七个候选文件尚待 ROOT 正常整合/安装；本轮没有 checkout、stage、commit、push 或安装操作。

| RF 正式候选路径 | 字节 | raw SHA-256 |
|---|---:|---|
| `scripts/research/authoring_projection.py` | 5509 | `00f1afb61975d2a88b8d7021ea38756590fdfa961673472787c3e50b45668703` |
| `scripts/research_projection.py` | 1427 | `0b1754b93857aa0a7c3f2c703c14db7fb3f9b3aacb4b54b4d88b3367d83dc353` |
| `tests/test_authoring_projection.py` | 7841 | `9a306dd1e116a02d037a763636108369b6581d5f900206adb91871cc64bb6f06` |
| `tests/test_authoring_projection_basis.py` | 2324 | `f16dbe1929c762fd417eaa6ff877034034e346e6a5e88c7540247a481fd249f8` |
| `references/evidence-role-calibration.md` | 17292 | `1b87ef549be31f213fc538534290ed22dac24f4da409fb45bb69d9b8bfe86e81` |
| `references/buy-side-methodology.md` | 15830 | `e74781a92c7edb64f2d15c1e90c411966cd27912af2473b45c8963f1aba6cf5f` |
| `references/input-construction.md` | 20259 | `d8cccba419e5c08d054c633cf77aac9f543504374a52ffd0c073fee065e3e951` |

完整实际路径、LF SHA、工件哈希、运行/清理和复现源码在 final-review.json、run-receipt.json、data-audit.json 及 REPRODUCE.md。raw 字节绑定本轮版本；LF 只证明 CRLF→LF 规范化后的确切文本对应，不给其他产品修改自动签署通过。

## 共享根因与内容

- **C01**：history-only 正向证据同步更新 driver title、thesis、causal chain、persistence、leading indicators/falsifiers 与 evidence conclusion/type/distance；相同说明继续投影到 native headwinds。历史、零范围与负贡献未改成虚构未来机制。独立反控确认真实 mechanism、mixed、未分类证据不会被历史计划抹掉，contrary 节点保留。Calibration 按自身 scope 更新，未涉及业务保持原样，status/observed_range 不变。
- **C02**：实际 main/stress 的 Low/Base/High 各从本情景 parent 与相同可比基准独立重算，分别约 **4.30383385% / 35.30152373% / 65.19096716%**，不是把 Base35.3%复制给所有情景。说明同时保留自身 price/mix、FX、条件和真实 parent ID。Stress 明确这是 **共同非TIDES递延3000 CNY million之前** 的经营路径；D&M与残余的递延分配未知，未把同一3000再分摊或伪称最终压力组件收入。中性 CAD 业务用40%/100%/180%独立桥验证泛化；错 scenario、period、unit 均拒绝，零可比额不编造增长率。
- **C03**：未计算的 several-percentage-points 量级与不存在的舍入表指向已修正；25项经营桥数值逐项保留。该修正没有产生经验区间。
- **C04**：memo 将逐位相同限定到实际测试的收入格，明确旧作者路径/身份与 ROOT v3 新执行；置信分不再充当金额保真证明。本轮采用实际金额、公式、工件与消费字节核验，未以置信分判定数字。

Owner 接收 reviewed authoring plan；上下文和基准的经济真实性仍属于研究责任，不是代码从名称/关键词推断。未新增公司/域名白名单、native schema、任务/来源/授权状态或第二计算引擎。

## 独立数字和来源保真

- 实读核验 **79个身份**：7候选、44最终工件、28作者原交付，大小与 SHA 全匹配。两份输入的 sources 和183个 claim对象均与作者原输入完全相同，每份183个 excerpt.strip() SHA自行重计匹配；参数除 rationale 外所有字段（含金额、公式、输入依赖）及 segments 完全相同。这里是已有来源链保真，不是再次打开原PDF或独立重签上游原文真实性。
- 独立 Decimal 对比 **108个分区年度格 + 18个合并年度格，最大差0**。额外比较完整输出的所有数字叶子：main1640、stress1738均相同；没有用测试自报的 PASS 字段代替金额。
- 独立受限算术 AST 重算 main128 + stress148条 derived formulas，共276条；最大与存储值差 **4.0400E-12 CNY million**，属于存储舍入，不是金额改动。非TIDES各情景组件桥另从实际参数用 Decimal 重算。
- 三情景 main→stress 年度差均为 FY2026约−4500、FY2027约+3600、FY2028为0，三年合计−900；返回原单年路径没有写成追回取消损失。保留TIDES与non-TIDES互斥共同扰动；未给D&M/残余虚构拆分。
- 六份已有 native capture 的 frozen/consume 原字节都实际保留、相同，并匹配 builder SHA：main `7e9258321e4c1c65a1f26d60e2a1389a8e542b2e24dff188fe855f62c88ac93b`，stress `0c84634ce2a9dbde53f9a5dd2b36f171fca1e74fda5736afb4cb396720c792ca`。每份解析后等于对应最终输入。两快照与实际input canonical hash、完整forecast_result及其canonical hash相符。

## 正式流程与实际 adoption

`references/input-construction.md:163` 明确在角色/scope/scenario变更后，先运行共享 `scripts/research_projection.py --input --plan --output`，再做 native validate/compute/snapshot；不是只有delivery私有修补脚本。薄 CLI 实际 import 同一个 research.authoring_projection。RF既有installation_manifest递归包含scripts/references，测试只属工程；当前候选尚未复制进RF主线/已安装技能，这一步仍由ROOT执行。

本轮独立实际执行：1个中性 projection CLI、1个 v3 main 重投影 CLI、1个真实 native `--validate-only --verbose`。Main重投影与冻结输入语义相同，且验证器**实际读取**新文件665235B，SHA `67dca05aac91c874ad207364a078f148aaf6d0aada0f28cfc9b19efa5444d262`，返回valid。sitecustomize直接记录Path.read_text返回的UTF-8字节，并记录各子进程实际模块路径；新输入在验证前后逐字节相同。Plan的读取记录是正常文本换行归一后的返回字节，不能与其CRLF原文件raw SHA混比。

## 恢复、复现与有限范围

51个候选/最终工件在独立测试前后全部SHA不变，作者原28件匹配冻结清单；RF main三份assurance WIP匹配既有保护收据。本轮未改作者工区、RF main、索引、安装、生产配置、费用账或原件。报告只写本目录。

专属 `.planning/r1-w09-independent-final-20261023` 初始不存在；只放guard、trace和pytest夹具，核对绝对父路径后删除，本轮结束不存在。输入、plan保持原SHA，实际验证不产生发布/registry文件；未清理其他历史临时物。所有进程清除API/访问密钥环境变量、禁dotenv并阻断socket连接与DNS（包括loopback）；无外部HTTP、模型、下载、密钥读取或原PDF/原页读取。REPRODUCE.md与小源码txt保留所有显式fixture依赖。

工程与研究说明修复没有消除旧真实外限：缺少子业务拆分、净价/利用率/确认节奏、经验预测记录等仍未验证；calibration全unverified、observed_range全null。W08最新摘要、真实来源缺口和W12四路公司审查继续保持未完成。30.15MiB只属作者有限磁盘采样记录，本轮未将其升级为连续峰值测量或另建整套交付副本。
