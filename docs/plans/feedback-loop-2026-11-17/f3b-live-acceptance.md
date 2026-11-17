# F3b 真实摘要、缓存及 RF 采用验收

2026-11-17。运行 `phase_c_runner` 的 live、registered_readonly、单 selector 0.9.0 和 activation recovery，使用配置中的 `mimo-v2.6-flash` 与 `reading-model-input/7`。全程用各自原语言。分别按来源所有者的已配置根登记冻结半年报与投资者关系原件。原件、作者底稿、历史运行和生产库保留原样。

| 样本 | 正式运行与新摘要 | 恢复、引用和用量 |
|---|---|---|
| 药明康德 2026 半年报 | `phaseC-090-61bd1c2d7409`；artifact `19b31f23473d56fc2e8fcfc9c6c471033d8adf93cdf6f90b7334f35219ddf13d`。自动业务视图 63 个支持范围，覆盖冻结 12/12。 | 112 个 locator 验真；1 次 POST，24,312 tokens，估算 $0.004919；同 run 激活和重启、跨 run 复用均新增 0 次 POST。 |
| 万润股份 2026-05-15 投资者关系记录 | `phaseC-090-055cb1ed2cd7`；artifact `85404e5a5218084002090c2a16fbc1b9d6eb51254155d3378c3a915e68095119`。自动业务视图 16 个支持范围，冻结 8/8。 | 38 个 locator 验真；1 次 POST，9,999 tokens，估算 $0.001917；同 run 激活和重启、跨 run 复用均新增 0 次 POST。 |

先停在付费响应已存、产物待激活的位置，再恢复原尝试。读取恢复和跨 run 作业自己返回的原件及摘要 ID、SHA 与大小，从实际缓存返回的 pin 经公开接口重新读取。首次激活与缓存读取的解压字节完全相同。两个公开业务视图均能按本身视图 SHA 核对，原件和临时库清理通过。总控的新增检查分别记录零 POST、返回版本和缓存 locator 验真。相同零 POST、错 SHA 的回归会发布版本偏差。两次真实尝试共新增 34,311 tokens、估算 $0.006836。现有母账为 2,009,602 tokens、$0.770708，含原 7 项和后 8 项未知记录的占额。

## RF 实际消费

用 RF 已发布 `51b26dcf0b168964b34366eff66fe6f1aca1aaea` 的隔离源码和原作者输入 SHA `56b9e02a049cb210f48a90cf3626de8a1978bafa4f9d738b4862ea7eecab2e74`。CWP 在临时库登记已实际恢复的同 SHA 摘要，RF 通过公开 transport 读取。单独保存作者输入、引用与下游数值的核验，各仓负责各自的产物。

| 新摘要中的证据 | RF 实际使用 |
|---|---|
| `t13-1`，第 12 页第 2 段，TIDES D&M 服务客户及分子的增幅和期间 | `tides_base_2026_activity`，基准情景增长率，驱动 TIDES 确认收入 |
| `t42-2`，第 11 页第 21 段字符范围由 locator 绑定，小分子 D&M 管线规模及各阶段口径 | `r4_dm_base_h2_net_delivery`，基准情景增长率，驱动非 TIDES 化学业务确认收入 |

RF 引擎 4.3.0 执行正式计算、输出验证、报告和快照。采用审计确认两个摘要 claim 和两个支持 span 都真实进入公式依赖，报告保留引用。181 个原有参数数值及币种、单位、口径、情景定义和信息日期一致。新计算 SHA `4581b4cc9d1874487268bc2ef4f118e6fd258953eff00ea7e8572f49b2dee3e1`，报告 SHA `e91e8ae022f5e730e0ec46c64a6dd0c8bec183f25069b3a05db5259c7b6cc187`，快照 ID `b9012e6d52fee291422a3ac598a0679dffb93b9d90d694a54b7aa8e56fb0a480`。本步新增下载和模型调用均为零，临时 CWP 读库、RF 源码与发布登记已清理。

## 独立复核与后续问题

独立审查通过真实摘要发布、缓存恢复、两份原文视图及两条 RF 实际采用。独审从两份真实原件和冻结检查点核对覆盖，从 CWP 公开响应复算视图 SHA，从 RF 使用报告、作者底稿及快照核对实际依赖。两份材料的来源覆盖仍为 `partial`，模型草稿质量为 `needs_review`。正式可定位的自动视图使用完整支持句，提问仍在上下文。草稿漏掉领域范围、较弱的主体表述和余留套话进入[本仓未关闭问题](issues/cwp-draft-scope-and-focus.md)。

定向回归包含错缓存哈希、错 run、公开 CLI 无手工 claim ID 的自动选择、财务片段和提问角色反控。21 项缓存故障/环回通过，用时 98.12 秒。另一批 320 项通过，三项在本地 `.venv` 缺少项目声明的 `nltk` 时得到语法不可用。换到已有声明依赖的本机 Python 后，相关四项全部通过，用时 14.16 秒。52 项来源 owner 边界及摘要测试通过，用时 11.97 秒。临时测试根均已清理。

完整本机收据位于 `.planning/shared-reading-production/f3-feedback-20261117`。两个 `overall.json` 的 SHA 分别为 `9c79fe22c5695b678dc110dcbf1dbe8cfa7a705e8ce0450e447ee325685ce4fc` 和 `58e5a8ba4b760612f8c30b4ce297eb691d216ebf2cdb38e92671058c57706785`，RF 和公开视图汇总 `rf-and-public-views/acceptance.json` SHA 为 `1b103ceff48c434e38882b2a6f403e1d72ee58246e26a4b8e8a70eb3f3deaee7`。恢复命令和原生回执随本机运行留存。`rf-and-public-views-driver.py` 复用这些真实字节，重放时无需模型。两次付费的 runner 源文件哈希各自记录在 `harness-fingerprint.json`。随后对保存的原生 activation、restart、cross-run 收据用最终版本绑定函数复验，再经公开读取并做 RF 正式组合。
