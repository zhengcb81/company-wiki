# N4C阶段耗时调查、版本修复与暂停交接

日期：2026-10-05。用户要求当前任务收尾、更新PWF、暂停；本收据覆盖耗时对照和一个批次版本修复，不把整个N4C标为完成。

## 1. 已完成与边界

- N4-T2外包差异已验收并选择性集成`0657579d`，精确SHA的[CI成功](https://github.com/zhengcb81/company-wiki/actions/runs/37273071081)。不整支合并重复实现，不再等待同卡交付。
- 本次将selector版本`0.2.0`升级至`0.3.0`。parser保持`0.1.0`，未改原件、locator、表格扫描策略、Worker槽数或生产配置。
- 没有启动新真实模型/provider请求，没有增加模型费用，没有删除旧derived/数据库span。原件及其他仓owner工作保持不动。
- S4/N4C仍in_progress；用户暂停是执行状态，目标未完成。

## 2. 同字节控制实验

旧实现取自CWP `069c8d4`的`narrative_candidates/evidence/finalize/routing`四个模块，放入隔离overlay；其余依赖与当前实现相同。这是在当前环境下比较选材实现，不能重现当时整个E6环境。

输入原件只读、内存解析；运行前后校验完整SHA、size、mtime。没有输出正文，没有下载/转换持久文件，没有调用LLM。三个样本：

| 样本 | SHA-256 | 说明 |
|---|---|---|
| P01 | `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5` | 中微公司2025年报 |
| P04 | `19cdb41e03b2d86ac15007753784f5859e1450a2bf79b514a7c0d4bd6830be67` | 中微公司科创板招股书 |
| P07 | `221467c15a24180205a8226f96fea9bda0262c866d5ba8aa31889ec96e6466d7` | 万润股份20260515 IR活动 |

### 无profiler的P04结果（秒）

| 阶段 | 旧wall / CPU | 当前wall / CPU | 旧表格调用/空结果 | 当前表格调用/空结果 | 旧/当前表格发现耗时 |
|---|---|---|---|---|---|
| parse | 27.730 / 27.156 | 30.165 / 29.000 | 141 / 82 | 144 / 84 | 24.443 / 26.726 |
| select | 4.890 / 4.703 | 4.988 / 4.906 | 0 / 0 | 0 / 0 | 0 / 0 |
| replay | 4.797 / 4.750 | 5.041 / 4.922 | 2 / 0 | 2 / 0 | 0.555 / 0.598 |

旧/当前单元14,639/14,646；两边都是160条span、10,391 B精选原文，逐条locator replay全部通过。当前三阶段总40.194s，比旧37.417s高约7.4%。`find_tables`占当前parse约88.6%，84/144（58.3%）调用返回空表。

### cProfile辅助结果（有额外开销，不与E6绝对值比较）

| 样本 | 旧parse/select/replay秒 | 当前parse/select/replay秒 | 旧/当前span数与精选字节 |
|---|---|---|---|
| P01 | 16.333 / 4.579 / 3.727 | 17.980 / 5.081 / 3.577 | 96/96，10,894/10,551 B |
| P04 | 45.731 / 9.199 / 6.048 | 47.032 / 9.804 / 6.425 | 160/160，10,391/10,391 B |
| P07 | 1.476 / 0.037 / 0.456 | 1.367 / 0.047 / 0.964 | 7/11，1,619/3,920 B |

P04的`find_tables`旧143次/39.083s、当前146次/40.465s。CPU接近wall说明本样本主要耗费计算。未测出足以解释旧E6与当前E6约2.4倍wall差异的选材规则成本；完整Worker各阶段trace、环境/缓存差异仍待下一真实批次记录。E6模型固定0.8秒/次，4次模型调用不是全部延迟来源；现有queue时间还包括依赖未就绪等待，不能当作纯调度排队。

表格发现的几何预筛选有提速潜力，但无框表格、跨页上下文和IR问答可能受影响。尚未做逐页真实对照证明，不删除扫描覆盖，不把零表格/零词汇命中自动当作无价值文档。该候选优化不阻塞已有有限批次的大节点验收。

## 3. 版本修复与测试责任

问题：N4-T2行为变更后仍用`0.2.0`，而该版本参与batch input hash。新旧选择可能共用generation，恢复时可能保留旧结果。

TDD：`test_current_selection_never_reuses_pre_n4t2_batch_hash`先RED（当前与强制旧`0.2.0`的input hash相同），升级`0.3.0`后GREEN，要求input hash和event ID均不同。已有同配置/跨时刻幂等测试继续要求同版本hash相同。原件、parser与locator不变。

发现旧英文回归测试把selector固定在`0.2.0`。改为要求不早于英文里程碑召回引入的`0.2.0`，保留parser `0.1.0`断言与全部英文召回/排除/逐条原文locator行为测试；新批次测试专门禁止当前行为复用旧generation。不能仅删除失败测试。

聚焦四模块测试117 passed/1.62s；Ruff、mypy合同及host-assumption hooks通过。完整Unit初跑1425 passed/1 failed/185.74s；唯一失败是旧G1-LEGACY卡通过`git status`要求整个checkout只修改其旧写集，连用户配置及本次计划都拒绝。移除两个一次性Git写集/删除集合测试与allowlist，全部产品行为/原件保护测试保留。正式交付审计仍留在该卡收据；不扩白名单、不清用户修改、不绕hook。代码提交`b09e845a845e172a3659acef6ad6d172f7565d2f`，push精选门和远端完整Unit最终结果写入progress。本次没有重跑慢E6三档或为删除两个Git检查重复本地全Unit。

**发布验收：**该提交已推送，live远端SHA匹配；实际快速pre-push契约门GREEN。[Actions 37354477263](https://github.com/zhengcb81/company-wiki/actions/runs/37354477263)精确SHA completed/success，Python 3.12完整Unit、精选合同、静态与CLI检查通过，job约77秒。全部本轮独立临时根已确认不存在，用户配置SHA保持一致。PWF发布收尾后按用户要求暂停，不启动第5节。

## 4. 目录恢复与复现边界

- 诊断根`company-wiki/tmp/n4c-timing-20261005`运行前不存在，结束finally删除，两次均返回`N4C_TIMING_TEST_ROOT_RESTORED`。临时benchmark脚本在收尾删除，只保留此聚合收据，不归档全文/trace缓存。
- 聚焦测试长basetemp由已有Windows path guard自动迁入临时目录，退出返回cleanup removed=true；请求目录确认不存在。完整Unit使用独立短根`company-wiki/tmp/n4u`，结束finally恢复原先不存在状态。
- 重做控制实验仅在需要验证具体优化时进行：相同SHA、相同依赖，旧四模块overlay对照当前，分别记CPU/wall、finder次数/空次数、span数/字节及所有locator replay；不以profiler绝对耗时决定并发档。

## 5. 恢复接口：只启动下一大节点

用户恢复后，先核CWP/RF当前HEAD及正常账号owner状态。RF已提交main `8a153f3387ae75fb172e70f8ab63ffd38100779a`含正式N3a；active fcap目录没有该文件不代表功能缺失。使用提交源码的只读隔离导出或owner正式环境，不checkout/switch/写RF。此轮正常账号未提交仅两个assurance weekly文件；旧3,833删除计数是沙箱ACL误读。

下一动作：遵循[n4生产实施卡](../../n4_production_batch_implementation.md)，建立新独立run，跑一个有限多文档真实provider批次并接RF N3a consumer。模型并发1、有限P4最多3 compute+1 model；每个source用正式SourceRef及实读SHA，metadata来自测试admission时明确标注fixture，不能冒充生产metadata。

- **预算**：旧`n4c-20261004-wave1`未知用量保留10,325 tokens、5,258 microUSD；原总60,000 tokens/$0.10的剩余上限49,675 tokens/$0.094742。不得清零旧预留、复用旧run ID或无限重试。执行时重新核账本，额度只能缩小；provider价格/usage变化按现有显式定价与未知用量规则处理，不把估价称账单硬cap。
- **版本/恢复**：新run绑定selector `0.3.0`与当前prompt/parser/模型配置；旧run输入版本不同必须具名冲突，不原地改旧hash。已完成版本覆盖不等于已有数据需要全量重算。
- **消费**：CWP公开`narrative-reference-request/1`与`narrative-read-request/1`；RF `scripts/narrative_source_preparation.py --company-wiki-catalog-config <隔离配置绝对路径> --operation read`（默认30s），输出`revenue-narrative-context/1`。验证真实bundle SHA/size、身份/期间/as-of、summary引用及原文locator；不写预测计算。
- **一次大节点收据**：model真实usage/未知预留、每阶段耗时、有限P4 RSS、重试/SQLite busy、summary原语言/coverage、raw+final+AUTO DB/WAL+logs+scratch总增量和峰值、恢复/幂等与独立目录清理。单final2MiB、persistent增量1GiB、scratch2GiB沿用现有cap；未知账本必须可继续核算，不因测试目录清理丢失。
- **停止规则**：具名失败/用量不明保留小收据，不编成功、不翻译、不自动下载；原件和用户`config/source_acquisition.yaml`不进入cleanup候选。暂不删除旧derived或span；RF默认SourceBundle迁移并验收后才进入S5/S6。

本交接不新增人工签收或逐helper审查。暂停期间不启动模型、Worker批次或其他仓改动。
