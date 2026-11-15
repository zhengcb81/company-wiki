# progress — CWP1 身份匹配双缺陷修复

格式: 每节点一行（做了什么/怎么验证/遗留）。

- 2026-11-15 开工: 于主工作区执行 `git worktree add ... -b codex/cwp1-identity-suffix-20261115`
  创建独立 worktree（该命令不改主工作区工作树内容）；基线 ac8841c55（非任务书 66c97834d，
  差 4 个 docs-only 提交，属任务书陈旧，已登记 findings）。验证: `git branch --show-current`
  + `git rev-parse HEAD`。遗留: 无。
- 2026-11-15 基线采集: （a）三探针 CLI 实测复现任务书诊断: "Alibaba Group Holding
  Limited"→ambiguous/fuzzy_candidates_require_user_selection（top=US BABA 0.9167 类）；
  "BABA"→ambiguous/multiple_verified_exact_identities（HK alias_exact + US ticker_exact，
  同 issuer_link_id）；"09988"→resolved。（b）回归探针: AMD/腾讯/騰訊控股/贵州茅台/
  Apple Inc 全部 resolved 基线已存 findings.md。（c）测试基线: 核心 4 文件
  41 passed/1 failed（FC-1301 注册漂移，master 既有红，含 security_identity.py:1167/1172
  两个既有未注册 code）；邻接 7 文件 55 passed/1 failed（r8 entity gate，resolver 装配
  AttributeError，基线既有红）/2 skipped；test_stage_taxonomy 20 passed。合计
  116 passed/2 failed/2 skipped，两处红均为基线既有，非本包引入。验证: pytest -q 实跑。
  另: worktree 无 .source_catalog（主仓未跟踪），只读复制主仓 security_master 至 worktree
  .source_catalog/（gitignore 已覆盖，不会入库）。遗留: 无。
- 2026-11-15 A1 实现+commit: security_identity.py 新增 _suffix_equivalent_text 与
  后缀等价类，_exact() 的 official/alias 名称比对切换到该归一化（ticker 严格精确、
  fuzzy 不动）。首版无词边界，全库差分（15825 记录/59933 串）抓到 VSE/VSA、
  LASE/LANV 垃圾键碰撞，修正为 ASCII 词边界 + CJK 尾部最长匹配规则（详见
  findings.md）。验证: 身份契约测试 23 passed（含 6 个新测试）+ 探针 + 全库差分。
  commit 7fa16a213（fix(identity): canonicalize corporate suffixes on exact name
  match，边界规则与差分结论写进 commit message）。遗留: 无。
- 2026-11-15 A2 实现+commit: identify() 多 exact 候选分支在"跨 market 且共享同一
  issuer_link_id"时 reason 细化为 cross_market_dual_listing_requires_market_selection
  （候选不折叠、不选边；同市场/无链接保持旧 reason）；observability.py REASONS +
  STAGES_BY_REASON 各 1 条纯增量注册（FC-1301 正规流程，红线偏离已登记 findings）。
  验证: 身份契约测试 27 passed（含 4 个新测试）+ BABA 探针具名 reason 两候选。
  commit 7595473f2（feat(identity): name the cross-market dual-listing ambiguity
  reason）。插曲: 曾误将 A1 边界修正 amend 进 A2 commit，随即 reset --hard 重建为
  base→7fa16a213→7595473f2 两个干净独立提交，重建后树与重建前内容等价（仅测试
  函数顺序不同），全部测试与探针重跑通过。遗留: 无。
- 2026-11-15 全量验证: 12 文件身份相关集改后 126 passed / 2 failed / 2 skipped，
  两 failed 与基线完全相同（FC-1301 既有漂移、r8 resolver 装配缺陷，均基线既有红，
  且 FC-1301 失败清单不含本包新 code）。全库差分最终记录: 59933 串中唯一行为变化
  "Kemper Corporation" 1→2（KMPR/KMPB 同名双记录，fail-closed 语义内，登记
  findings.md）。8 探针实测（真实 CLI）: "Alibaba Group Holding Limited"→resolved
  (US BABA, official_name_exact)；"BABA"→ambiguous +
  cross_market_dual_listing_requires_market_selection（HK 09988 alias_exact +
  US BABA ticker_exact）；"09988"→resolved；AMD/腾讯/騰訊控股/贵州茅台/Apple Inc
  五回归探针与基线逐字段一致（status/reason/resolved name/market/exchange/ticker/
  match_basis）。验证: pytest -q 实跑 + CLI 实测。遗留: 无。
- 2026-11-15 PWF 收尾+commit: findings/progress/task_plan 定稿，PWF 三件套作为
  docs(pwf) commit 提交于 lane 分支。未 push、未并入 master。遗留: 无。

## 2026-11-15 续作（施工包 §5 验收 2/3/4 与 §8 收口）

- [节点 6] §5.1 解析探针: 真实 CLI 跑 "Alibaba Group Holding Limited"/"BABA"/"09988"
  → resolved(BABA US, official_name_exact) / ambiguous(cross_market_dual_listing_
  requires_market_selection, 2 候选) / resolved(09988 HK)。另跑 4 个显式 --market
  具名消歧探针，BABA 在 US/HK 下分别唯一解析到 BABA / 09988。全部 stdout/stderr/
  exit/command 落盘 evidence/。验证: CLI 实跑 + JSON 解析。遗留: 无。
- [节点 7] §5.2 FF reuse_only 联动: 4 个探针。全称（±market）与 BABA+market=US 均
  exit=0 / source_candidate / resolution_outcome=reused_existing / download_events=0，
  命中 20-F 原件 sha256 36daec0c…。BABA 无 market 保留为 exit=2 具名消歧失败样本。
  未修复 master 对照同一请求 exit=2 / identity_error /
  "ambiguous / fuzzy_candidates_require_user_selection"，复现施工包 §1，修复后消失。
  验证: fetch_filing.py 实跑 + 基线对照。遗留: 无。
- [节点 8] §5.3 RF 六路线联动: 通过 source_preparation.py 官方入口复用 RF 六个原始
  请求体。route3 (HK FY2025 reuse) exit=0 / found_capture_ready（完整来源记录 +
  verified_read 收据）；其余 5 条 exit=3，具名原因 acquisition_validation_failed 或
  local_prepare invalid_local_prepare_request，全部 downloads=0。为诚实归因，在
  未修复 master 下重跑同样六路线：逐条结果与修复后完全一致（route3 两边都成功）。
  结论: 本包未引入 RF 回归；route3 成功非本包功劳；剩余 5 条属既有下游契约/
  元数据缺口，非 fuzzy/ambiguous 复发。验证: 双源码树六路线实跑 + 汇总 JSON。
  遗留: 5 条缺口具名登记并交接（见 findings）。
- [节点 9] §5.4 证据: 每条探针落盘 command/stdout/stderr/exit；失败样本未改写；
  汇总 evidence/README.md；总 < 300KB 全量落盘。夹具不进 git，生产配置零改动。
  验证: find 清单 + du。遗留: 无。
- [节点 10/11] §8-1 独立重审与 §8-3 交接: 主工作区有在途 WIP、ff1 lane 未收口，
  按 §8-3 情形 2 不并线，PWF 写显式交接任务 + handoff（含 40 位 release commit）。
  详见 findings.md 与 handoff 文档。

