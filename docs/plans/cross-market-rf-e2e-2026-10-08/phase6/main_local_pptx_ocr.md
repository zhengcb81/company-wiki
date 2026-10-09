# MAIN 施工：本机 PPTX 图片识读与版本化证据定位

状态：已调查，待 TDD 实施。依赖 [调查证据](main_reuse_ocr_investigation.md)。本包属于主线 Phase6，不启动公司池新抽样；大节点完成后仍要做原三家和新三家的真实研究审查。

## 唯一 owner 与写入边界

MAIN 分派 `main_reuse_ocr_investigation` 接续实施。使用既有干净工作树 `C:/Users/郑曾波/Projects/_harness_worktrees/cmrf-20261008/cwp-formats`，新分支 `codex/main-local-pptx-ocr-20261009` 从当前 master 建立。

独占 `src/company_wiki/document_normalization/`、`tests/document_normalization/`、必要新 OCR adapter 测试与 `docs/implementation/main-local-pptx-ocr/`。本包不改 automation/narrative_batch、run/artifact store、narrative_formats、生产配置、安装副本或其他仓库；这些共享接线由 MAIN 完成。已有另线负责跨 run generation manifest，必须交接实际 OCR 配置指纹并由 MAIN 纳入该身份，不能让同一图片不同模型错误复用。

## 实施顺序与接口责任

1. 先写责任 RED：两页 PPTX 内部 ID 256/260、重排、旧 locator；图片正文、重复 media、空白/损坏/低置信、模型缺失/坏 SHA、禁网、deadline/pixel/text 上限、多 span 回放。RED 必须证明产品行为，不把测试夹具或环境错误当作预期失败。
2. 分清 pure package parser 与可选本机识读编排。公开入口保持原有参数可用，新增明确本机 OCR 配置/注入 adapter；不默认调用远端服务。默认纯解析仍诚实呈现 opaque；启用 OCR 的统一入口产生可以回放的结构，不只给 select 拼文本。依赖缺失/模型不可用要具名说明，不能假装 skip_success。
3. 修正 slide ordinal 为 1..N，内部 slide_id 单独保留。升级 parser/locator 身份；旧 1.0.0 证据应能按旧规则回放，或明确声明不支持，绝不在旧版本下静默改释。推荐保留只读旧版本回放，避免破坏冻结样本。HTML 的现有身份和证据不应因 PPTX 修改无谓漂移。
4. OCR 配置仅 CPU，本机模型显式路径和实际 SHA；冻结 RapidOCR/runtime 版本、三模型 SHA、预处理/阈值/线程参数。路径仅用于定位，不构成内容身份；凭证不参与。模型 SHA 失配拒绝，不自动下载/安装/fallback；不能把开发机依赖外推为其他安装已具备。
5. 识读 verified image bytes，输出原语言逐行文字、图内 box、行序、置信与 transform；locator 绑定原件 SHA、展示页序、shape path、media SHA、版本和识读配置指纹。坐标系明确，不把 OCR 行自动补成精确财务表格 cell。选中 span 的文字/box/模型/源图改动必须无法冒充原证据。
6. 单次 normalize 同 media SHA 仅推理一次，复用文字但保留每页独立位置。统一支持一次解析/识读核验多个 spans，避免每 locator 重跑整个文档。完整 OCR 与图片仅在内存/owned TEMP；最终只保留小型 selected spans/bundle 与质量记录，不落全页图、完整 OCR MD 或第二缓存库。
7. 限额由格式/OCR责任层执行：页、媒体、像素、文字、unit 与单调 deadline；ONNX 调用可能不协作，明确依赖现有外层子进程硬 deadline，不能只把 Python 前后时间检查称为强中断。至少证明正常完成、超限、损坏输入与外层中断不产生已发布成功物。
8. 新 API 的配置解析/identity 与 batch/select/verify/language/public read 接线契约写入 `INTERFACE.md`，给 MAIN 一份可直接照做的实际调用示例、需要改的共享文件清单、错误与质量语义。不要自行改共享文件。

## 质量与覆盖语义

OCR confidence 不是召回率。`pages_read` 表示尝试的页，不自动等于全部正文已正确识读。记录每页检测行数、低置信/空白/失败/残留 opaque、阅读顺序和数值表格限制。保持原件原语言，不翻译。实际封面底部小字曾漏识，该限制必须在正文大节点检查，不能仅用“每页有一行”宣布 coverage_complete。

允许来源型经营文字进入叙述候选；财务数字表格保持来源文字/质量标记，由 selector 处理，不以 OCR 产物代替清洗财务 API。全图关键材料未可靠读取时具名 incomplete；可以返回可验证的已读 span，但不能虚称全篇完整。

## 集中验收（只在大节点）

- 快速责任测试：页序/旧版本、纯解析兼容、配置身份、真正离线禁网、media 去重、限额/错误、span 伪造拒绝、多 span 一次解析。
- 真实固定 22 页 deck：读 `benchmarks/cross_market_rf/cases.json` 的对象引用，通过当前只读来源定位，不复制全套原件。SHA 必须是 `c02f4ea1a2719b74d5752559ad7b907d89dd4b47d292424ade8988396fb2dcd4`。至少封面及两张信息密集正文真图对照；保留每页小型统计、阅读顺序与 OCR 数字/漏字差异，真实未完成范围不能计 PASS。实际全 22 页识读只能在本机已验证模型、硬 deadline 与资源上限内运行，零 supplier POST。
- MAIN 集成后做 public batch→select→verify→NarrativeRef read，多 span 一次回放和重复 run 复用；真实生成使用现有文本模型配置和累计预算，不新增 vision provider。
- 日常 CI 仅确定性小夹具/fake adapter；本机模型真实大节点单列，不让每次 commit 跑 22 页/依赖网络。

## 交接与提交

本包先完善独立 PWF 三文档，然后实施。保留实际 RED/GREEN 命令、退出码、耗时、版本、模型 SHA、0 网络/外发、临时根恢复和原件保护。正常 scoped commit，不绕 hook；缺 hook 必须诚实写，不伪称已通过。

交付 `docs/implementation/main-local-pptx-ocr/{task_plan,findings,progress,INTERFACE,HANDOFF}.md`、`handoff.json`、小型测试/真样本报告，包含 base/head、changed_files、API/version compatibility、共享接线清单、known gaps。不合主线、不 push、不改其他 owner 文件；MAIN 统一审查、接线、一次集中验收、合并/推送/安装。

MAIN统一接线细则见 [main_ocr_composition.md](main_ocr_composition.md)：实际配置注入、per-format身份、旧版本回放、bounded语言样本、selected-media精确核验与source partial分开。parser owner不改该共享层。
