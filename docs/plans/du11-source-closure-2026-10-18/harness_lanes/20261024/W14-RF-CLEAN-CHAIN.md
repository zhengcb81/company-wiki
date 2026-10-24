# W14-RF-CLEAN-CHAIN：既有三仓E2E的干净离线重构

**可以立即开工，不等ROOT新摘要。** 独占工作目录 `C:/Users/郑曾波/Projects/revenue-forecast-w14-clean-chain`；分支 `codex/w14-rf-clean-chain-20261024`；RF基线 `599d17b89d8baee42ce203747496731ace2d0148`。设置 `PLAN_ID=w14-rf-clean-chain-2026-10-24`、`PWF_PLAN_ROOT=docs/plans`。完整读[共同接口](INTERFACES.md)。

## 已证实的问题与目标

`tests/test_cross_repo_chain_e2e.py`约42行仍以生产宁德时代PDF/sidecar/security master决定offline测试是否skip。`e2e/run_cross_repo_chain_e2e.py`约65行四份RF源码pin均不匹配当前LF源码；1133–1149行仍把已取消的prompt-injection人工审查拒绝当成成功期望。默认 `--live auto` 可能联网，且已有work-root会先递归删除。`test_ca301_clean_checkout.py`只是当前sibling仓对象检查，自称simulate，不能证明清洁部署。

修改**现有runner和现有测试**，得到真正运行当前冻结三仓代码、无需个人生产湖/密钥、可异地复现、0外网的工程E2E。不要新写一条只供交付而绕开旧坏入口的旁路。小型中性夹具不叫真实公司分析；真实公司质量仍由ROOT验收。

## 写范围

允许：`e2e/run_cross_repo_chain_e2e.py`、新增 `e2e/replay_support/**`、`tests/test_cross_repo_chain_e2e.py`；新增 `tests/test_w14_portable_chain_runner.py`、`tests/test_w14_portable_chain_cleanup.py`及`tests/fixtures/w14_chain/**`；`docs/plans/w14-rf-clean-chain-2026-10-24/**`、`delivery/w14/**`。新fixture≤1MiB，真实有效小PDF/TXT/JSON，禁止占位`%PDF fake filing`冒称解析验收。

禁止：RF `scripts/**`、`tools/**`、SKILL/references、CI/hooks、生产config、compatibility、assurance、output、旧delivery/w09、`tests/e2e_support/isolated_lake.py`和CA301旧合同；FF/CWP/ET/Dayu/IQS任意写入；母PWF/中央run/费用账/安装副本。W09已交付研究/经营桥不重开。RF主工区现有三份assurance WIP/output不动。新工区sparse省略旧tracked`.planning`，不要重新展开。

## 固定接口与要求

沿用 `python e2e/run_cross_repo_chain_e2e.py` 入口、原scenario ID；现有参数保留或给清晰迁移错误，不能静默改变用户目录。

| ID | 必须实现和证明 |
|---|---|
| E01 | 默认offline，即`--live never`；S1真实下载只显式`--live force`，本卡不跑。旧`auto`如保留则提示退役并按never处理，不据环境自动联网。S2成功准备、S3重复复用、S5错误filing、S6无公司和S4恢复全部实际执行，不因缺生产材料skip |
| E02 | 新增显式 `--rf-repo PATH --rf-commit SHA --cwp-repo PATH --cwp-commit SHA --ff-repo PATH --ff-commit SHA`；三仓生产源码/无密钥资源均从冻结Git对象部署到自有scratch后执行，新runner/support自身从作者最终版本运行。记录三仓实际import `__file__`/子进程源码根，加入污染PYTHONPATH/旧安装副本的反控。commit/脏路径是provenance而非固定hash许可；缺运行时/对象输出具体environment_unavailable并非零，不能PASS/skip |
| E03 | 通过现有生产公共RF→FF→CWP CLI/SourceRef链注册/准备/读取有效fixture，至少三个真实进程PID及执行源码根。不能mock掉关键FF/CWP边界或以自制DTO代替生产返回；生产投资结论/付费摘要不属于本包 |
| E04 | 小型有效PDF＋原语言TXT夹具、确定的临时公司身份/期间/as-of；分别记录PDF的真实source_prepare成功，以及TXT经实际本地companion/query/read消费的结果，不能只登记TXT不读取。正确SourceRef/SHA/locator来自实际入库读取。空/歧义身份、错误期间、缺文档和真实product错误保持各层原始原因，不重新要求prompt-review签收 |
| E05 | S3复用同一原件，provider/HTTP/新下载为0；raw目录前后hash及真实来源ID可核。离线子进程阻止外网并记录尝试；删掉API key只在子进程env副本进行，不能输出key |
| E06 | 不删除传入已有work-root；创建独占attempt子目录。evidence目录与待清scratch分离；成功/失败/timeout/启动异常均只清自己临时文件。已有sentinel、同名历史结果和原始资料保持，output冲突报错或新attempt，不覆盖 |
| E07 | 两个不同绝对目录实际跑同样场景，一个含中文/空格，从外部cwd启动并清除开发者PYTHONPATH/editable install干扰；屏蔽原生产湖，仍全部执行成功。稳定语义字段相同，只显式排除PID/临时路径/运行时间 |
| E08 | 重构为少量清晰support模块（fixture、部署/子进程、观察/清理）；不写公司名/个人目录/旧SHA特判，不创建第二来源库/预算账。旧源码pin和人工门期望由行为测试替代，历史收据原样保留 |

冻结只读输入：CWP仓 `C:/Users/郑曾波/Projects/company-wiki` 的 `a31300a70215319e6bcf3a03d32b2882bdf1aeaa`；FF仓 `C:/Users/郑曾波/Projects/filing-fetch` 的 `7f6a9268da90281c28b55d437860bc2d2b60106e`。不能直接导入其正在变化的工作区。部署资源根据现有实际依赖显式列明；CWP无密钥models/resource_budget配置的必要性已由最新Phase C根修验证，不能遗漏后把环境失败当产品错误。

## A/B/C和验收

A调查并以不访问生产湖的反例冻结E01–E08；B重构既有入口，实现两个目录和失败清理；C集中运行相关测试、直接runner双目录回放及已有日常工程gate一次，随后独立agent全面审查最终diff和实际调用链，全部修复/复审后交接。不等ROOT或用户再签A。

```powershell
python -m pytest -q --tb=short -p no:cacheprovider tests/test_cross_repo_chain_e2e.py tests/test_w14_portable_chain_runner.py tests/test_w14_portable_chain_cleanup.py
python -m ruff check e2e/run_cross_repo_chain_e2e.py e2e/replay_support tests/test_cross_repo_chain_e2e.py tests/test_w14_portable_chain_runner.py tests/test_w14_portable_chain_cleanup.py
python tools/pre_push_gate.py
```

直接入口示例（新参数按本卡实现，使用本工区自有父目录；再次运行不得删除旧evidence）：

```powershell
python e2e/run_cross_repo_chain_e2e.py --live never --scenarios S2,S3,S5,S6,S4 --rf-repo C:/Users/郑曾波/Projects/revenue-forecast-w14-clean-chain --rf-commit 599d17b89d8baee42ce203747496731ace2d0148 --cwp-repo C:/Users/郑曾波/Projects/company-wiki --cwp-commit a31300a70215319e6bcf3a03d32b2882bdf1aeaa --ff-repo C:/Users/郑曾波/Projects/filing-fetch --ff-commit 7f6a9268da90281c28b55d437860bc2d2b60106e --work-root .test-scratch/w14-first --evidence-dir delivery/w14/replay-first
```

第二次用绝对中文空格根，从工区外部cwd实际启动。测试须验证产品真失败能使整个工程E2E非零；E01离线场景的not_executed/skip属于未完成，不能与S1有意未执行混在一起。跨范围产品缺陷提交ROOT具体触发和原始错误，不能窄化断言绕过。

## 交接

`delivery/w14/handoff.md/json`、双目录实际收据、`review.md/json`。每场景写命令/exit/status/cause/PID/来源根/SourceRef/hash/locator；实际Git版本、fixture SHA、阻止的网络尝试/provider/download计数、生产写入和清理前后hash。报告明确“合成夹具的真实代码跨仓E2E”，不宣称真实下载/公司分析通过。独审绑定最终代码/fixture SHA并独立新scratch重放；完成后可推自己的codex支线，主线并线归ROOT。
