# ET 独占施工卡：精确期次的原语言电话会议工具

> **2026-10-01 当前状态：**本仓 `main@4924d57` 已于本轮正常推送到 `origin/main`。精确 FY/Q、未翻译 `/1`、可选原始 payload `/2`、Motley 三入口默认禁用、FMP/Motley producer goldens 和单一请求内 `download_authorized` 网络意图已实现；旧 `--allow-download` 仅兼容 CLI 参数。离线全套 118 passed、2 deselected。FMP 真请求曾返回 402，真实 provider 权益未证实。FF→ET→CWP 汇合仍待 FF owner 完成，主要合同差异是 FMP 26 字段、Motley 24 字段与 CWP importer 当前只接受 Motley 形状。`eval_results.json` 和 `.workbuddy-ai/memory/` 由 ET PWF 记为既有本地评测/工具笔记，本轮保留。下方实现顺序是历史施工说明；不重复实现已完成的 ET producer。

> 可单独交给一个 earnings-transcripts harness。**唯一写入目录**：`C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts` 及其由 owner 创建的独立 worktree。company-wiki、filing-fetch、revenue-forecast 等只读；本卡不授权更改那些仓。开工前读本仓当前 Git/PWF 并保存有效未提交代码，别按 2026-09-28 缓存 SHA 直接 reset。

开工输入包：本卡、S0a observed 接口表、只读 T01/T02 样本清单（SHA/期次/locator oracle）和本仓 fake HTTP fixture；真实 provider 权益不是本仓离线测试的前置。

## 目标、输入和输出

- 现行 `/2` 接收明确的证券/交易所、fiscal year **与 fiscal quarter**；只有 FY 时由 FF 返回 `period_unresolved`，ET 不猜 Q4、不遍历其它季度。若以后需要 FY-only，设计新请求版本并同步 FF/CWP。S0a 已实测：Motley fetched 为 24 字段，FMP fetched 为 26 字段；CWP 现行 exact-key importer 只收前者。ET 不为迎合旧 importer 伪造 FMP 的 `published_date`。
- `transcript_tool.py`/`transcript_api.py` 用一次精确请求返回**未翻译**英文 TXT 的版本化 `/2` 工具结果：安全来源 URL/时间、`provider_payload_sha256`、抽取文本 `canonical_content_sha256` 与 `content_bytes`。`/2` **没有原始 payload 长度字段**；不要在原版本添字段，因为 CWP importer 对结果 exact-key 校验。工具可在受控路径附带原 payload，CWP 入库时另算 deterministic material SHA；三种哈希/长度的含义不能互换。
- 未找到、provider unavailable、凭证缺失、限流、坏响应和超预算各有具名状态；正文不混入 stdout 日志。ET 不产生 CWP source ID，不决定最终公司目录或投资结论。
- 旧 `scraper.py` 的 `--no-translate`/`--disable-translation` 保持可用；新 tool/API 原本只返回原语言文本，不添加无作用的翻译开关。

## 当前复杂门及本线实现

`transcript_api.py` 的 `download_authorized` 与 `transcript_tool.py` 的 `--allow-download` 形成双重布尔阻断。先写“有明确一次请求、无第二份授权仍执行一次精确抓取”和“未请求、错候选、错误主机/期次时零正文网络”测试，然后改为**一个网络意图**。保留 HTTPS/host/redirect 约束、精确 candidate URL/ID、字节/超时/重试预算。逐候选 rights receipt、人工 reviewer/有效期 hash 不成为工具输入。

provider 能否使用由一份简明配置和真实接口能力决定。[The Motley Fool 官方规则](https://www.fool.com/legal/terms-and-conditions/fool-rules/)限制脚本抓取；**现行代码尚未真正禁用**，本线须在 `fetch_transcript`、`discover_transcripts`、`fetch_transcript_candidate` 的共用 provider 选择边界把 Motley 默认设 disabled，即使明确网络请求也 0 HTTP。若将来条款/来源方式改变，另审配置开关，不通过旧双授权布尔绕过。[FMP 官方条款](https://site.financialmodelingprep.com/terms-of-service)取决于账户/套餐，本机既有实际请求曾返回 402；缺 key、402/无权益要具名 `unavailable`/entitlement 结果而非成功。不要为 disabled provider 再建立逐文档审批服务，也不把 fake 测试写成真实联网成功。

## 实施顺序与独立测试

1. 盘点 `transcript_api.py`、`transcript_tool.py`、legacy scraper 与活动未提交测试，收拢为本仓独立提交。保持旧 `/1` 入口兼容；`/2` 正例必须由真实 serializer 生成，并记录 exact request、响应字段、错误码/退出码与 payload 上限。
2. 先改 `tests/test_transcript_api.py` 的双门测试，覆盖单一网络意图、FY+Q 唯一性、Motley 默认禁用下三个入口均 0 HTTP、FMP 缺 key/402、坏 host/redirect、超过字节/截止时间、相同精确请求的确定性结果；`tests/test_translation_controls.py` 保证原语言、无翻译 API 调用和无额外翻译文件。ET 自身不保存文件，“重复候选 0 再保存”属于 FF/CWP importer 测试。
3. 现有 `transcript_tool.main(argv)` 无 fake HTTP 注入入口；先在内部 CLI dispatch 加一个只供测试传入的 transport/session factory seam，生产 `main` 仍使用真实受限 transport。成功 E2E 使用 **fake FMP HTTP + 测试专用假 key/有效权益响应**，走真实 ET CLI JSON 读写→API 解析→fake transport；同时证明默认 Motley 即使有请求也 0 HTTP、无候选/未请求 0 网络、FY/Q 不符失败。不能 mock 掉整段 `fetch_transcript`，也不能靠旧授权布尔打开生产 Motley。再用 subprocess 跑无网络的 JSON/退出码边界。产物和临时根在 finally 恢复；无需付费 provider 联网测试来证明工具合同。
4. 向总指挥交付 tool `/2` 的正式 **FMP 和 Motley 各自字段集** golden 正反例、版本、CLI 命令/退出码、`provider_payload_sha256` 与 `canonical_content_sha256`/`content_bytes` 的定义，以及本仓 commit。FMP 结果现有 `call_date`、`publication_date`、`as_of_cutoff_verified`，payload MIME 为 `application/json`，安全 URL 含 `symbol/year/quarter` 查询参数；CWP owner 须按 provider 精确校验或先协调新版本。若确需新增原始 payload 长度或 FY-only，先升版本并协调 CWP exact-key importer 与 FF consumer。FF harness 据此实现 companion；ET harness 不写 FF 或 CWP。

原始 provider payload、来源 URL/时间和内容哈希不因去掉人工许可而省略。输出字段变更由 ET 更新版本和 golden，交总指挥协调 FF/CWP；如果请求身份、期次或两级哈希不一致，本线保持错误结果，不隐式回退到别的季度或翻译后的文本。

**本线自动验收：**本仓 API 与真实 CLI dispatch 测试通过且新增路由零 skip；默认 Motley 三入口 0 HTTP，FMP fake 200 可解析而缺 key/402 有具名失败；`/2` 正例由当前 serializer 重生、字段集和哈希语义稳定。CWP 的 FMP 兼容另由 CWP owner 用同一 golden 及拒绝额外 query/凭证的负例验收，未通过时跨仓 G-A 保持 pending。测试仅用本仓可写短临时根，前后恢复；交接报告 commit、golden SHA、命令/退出及 provider 未验证状态，不要求人工签收。

## 恢复后的 G-A 补充

FMP `/2` JSON 原件、带 query 的精确期次 URL、26 字段结果及 unknown publication 仍需 CWP admission；实现/测试细则见[跨线收尾报告](results/cross_line_closeout_2026-10-01.md)。ET producer 不伪造 publication，不降级为 Motley 形状；本轮暂停，不重做已交付工具。
