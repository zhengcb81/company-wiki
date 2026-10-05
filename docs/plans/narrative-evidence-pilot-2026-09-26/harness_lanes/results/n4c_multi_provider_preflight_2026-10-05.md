# N4C：配置驱动的 MiMo / DeepSeek 验证

## 已完成

正式入口：`python scripts/narrative_batch_configured.py --llm-provider mimo|deepseek`，其余有限批次参数按既有CLI。没有该选项时仍使用主配置。所有模型/地址/凭证/8192输出限额/温度由`Config.load`提供；MiMo用已配置fallback，DeepSeek用loader已有provider defaults；不覆写生产config.yaml或.env。

| 供应商 | 现有配置 | 真实只读探测 | 摘要实测 |
|---|---|---|---|
| MiniMax | MiniMax-M3 / api.minimaxi.com/v1 | 此前清单200 | run04无效envelope，P04未产出final；旧usage未知不退款 |
| MiMo | mimo-v2.6-flash / token-plan-cn.xiaomimimo.com/v1 | 正式配置 `/models`200，模型存在 | 等待旧试点token cap调整答复，尚未POST |
| DeepSeek | deepseek-flash / api.deepseek.com | dotenv覆盖环境密钥已修复；正式配置 `/models`200，模型存在 | 环境密钥有效，尚未POST |

135项Unit +4真实CLI/Worker/loopback HTTP测试：139 passed /35.14s。覆盖现有loader、三家wire参数、明确fallback选择、无效响应已知usage保留、静态安全错误阶段、原件和foreign jobs不变、重复运行零额外HTTP。Ruff/diff-check通过。配置选择不等于自动故障切换，未实现的自动fallback不标完成。

## 接下来怎么跑

1. 旧累计58,523tokens/33,884microUSD（含未知最坏账）；另保留2,764microUSD历史FX余量。询问累计token cap提高到160k、美元仍0.10；未批准前不突破60k。
2. MiMo先跑同一P07中文IR记录、T01英文原电话会TXT和synthetic English policy。前两份只发精选业务证据，policy应零模型skip。DeepSeek跑相同样本。输入、引用、原语言、质量/缺失标记一致，模型结果与费用分别记录。
3. 每家独立run/账本，执行前将原旧账、run02、run03、run04及全部后续正式收据累计进同一美元/token cap。拒绝覆盖已有报告/run ID，失败也先保存费用，不退款重试。实际调用逐家进行，模型并发1；失败不盲重试。
4. 单批最多480秒；每次HTTP沿用既有有限CLI传输上限与60秒请求期限。独立测试目录只复制样本，原件SHA/size/mtime、生产fingerprint、RF owner及用户配置前后一致；退出删除新增样本、DB、final和导出模块，仅留小型收据。
5. 在首次模型POST前，从`RF main@8a153f3387ae75fb172e70f8ab63ffd38100779a`按AST导出六文件依赖闭包；本次CLI help退出0，scratch恢复，零模型调用。真实final通过已有CWP public read与RF N3a reference/read消费，验证receipt、每条claim引用/locator replay和语言，不写RF预测状态。整批相同run恢复应零额外模型调用。

## 计量依据与配置维护

- MiMo当前专用Token Plan endpoint消耗Credits，不能将PAYG费用代理冒称现金扣款。按[国内公开价](https://mimo.mi.com/docs/en-US/price/pay-as-you-go)Flash的1/2 CNY每百万输入未缓存/输出、CNY/USD保守下限6，作0.166667/0.333334 USD预算代理；如有效usage返回，另外记录Token Plan按Flash输入未缓存100、输出200 Credits/token的上界。[Credit规则](https://mimo.mi.com/docs/en-US/price/token-plan)。不购买、不切到PAYG地址。
- DeepSeek按[国内峰价](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)2/8 CNY、同一FX下限6，作0.333334/1.333334 USD预算代理，不先吃缓存或闲时折扣。使用用户指定的官方canonical `deepseek-flash`；模型身份仍严格验证，不借供应商别名说明取消校验。
- 项目YAML、脚本Config/LLMClient defaults、typed config备用默认原本仍是旧Pro/旧DeepSeek别名；按用户纠正已统一Flash。不得在Worker/driver里另设模型或切Key；DeepSeek环境密钥优先，MiniMax/MiMo继续项目受管凭证。

## 未完成边界

两家真实模型摘要、真实final引用质量、消费者实读、自动额度切换尚未验收。模型清单成功与本地E2E成功都不能替代这些验收。N4C/S5/S6没有标完成；三个P5外包写集保持独占。
