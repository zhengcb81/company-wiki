# N4C 配置遵从修正

## 已完成

实际请求的传输字节/超时caps继续沿用，不会因配置组合而变大。

真实入口：`python -B scripts/narrative_batch_configured.py`，沿用有限batch参数 `--project-root --catalog-config --automation-db --work-dir --request`。request仍列明确SourceRef、profile、时间/token/费用及版本化pricing；model可以省略，配置入口总是使用既有 `Config.load()` 的模型设置。已有纯DTO模块CLI是底层组合口，不作为后续真实试点的配置入口。

| 设置 | 来源及当前正常账号核对 |
|---|---|
| model/base_url | `config.llm`：MiniMax-M3、国内api.minimaxi.com/v1 |
| key | 既有Config/.env规则；只把api_key_env传给child；存在性true，值未输出 |
| output/temperature | 配置8192/1.0，实际请求使用已有max_completion_tokens策略 |
| reasoning | 配置reasoning_split=true；没有配置的thinking保持省略 |
| 可恢复身份 | 使用实际配置后的batch input hash；改配置不会偷偷复用旧run |

配置单元14 passed；集中节点104 passed（包含前7项配置case），不同case合计111；实际spawned Worker通过本地HTTP验证配置、同run恢复零重复请求、预算/产物不变，独立fixture配置与原件恢复。Ruff与diff-check绿。纯帮助命令及正常账号Config.load成功。本节点没有外部模型调用、下载或生产配置改写。

## 尚未完成

- N4C真实摘要/final与RF公开读取仍未通过；旧收据不冒充成功。
- 旧unknown与run02合计33,660 tokens/16,580 microUSD保留；下一真实批最多26,340/$0.083420，费用为估算/预留而非账单。
- 按8192输出及完整配置重新量离线请求准入，再实施citation私有投影压缩；价格与policy fixture路由仍待证据。原件与完整精选正文不因额度缩小而删改。
- P5三个外包已由用户开工，写集仍按总包互斥；本次没有跨入它们的责任目录。
