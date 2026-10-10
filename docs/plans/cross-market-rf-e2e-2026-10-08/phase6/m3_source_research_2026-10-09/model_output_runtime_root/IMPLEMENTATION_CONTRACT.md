# 共用模型生成配置与截断计量：实施接口草案

状态：配置投影候选已实施并局部通过，截断计量等后续责任未完成、生产配置未改变。此卡并入十二份公司审查后的共因施工，不另设人工签收节点。

## 事实与推断边界

M3 的 CN 半年报/IPO、HK 演示、US 电话会确实在配置的 8192 输出槽耗尽。旧记录没有 reasoning token 细项及完整失败正文，不能反推出精确原因或补成零。选择为空是另一根因，不能由生成配置解释。

当前 Config、SDK、urllib、NarrativeHTTPModel 的配置投影都遗漏 DeepSeek thinking/effort。2026-10-09 再查 [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)：默认 enabled/high，可明确 disabled；SDK thinking 放 extra_body，effort 为顶层参数。由此推断默认推理可能挤占最终答案槽，仍需真实复验。

当前 [MiMo 深度思考文档](https://platform.xiaomimimo.com/docs/en-US/usage-guide/passing-back-reasoning_content)说明的是 v2.5；不能据此擅改本机已配置的 mimo-v2.6-flash。本卡先明确配置 DeepSeek 叙述用途，MiniMax/MiMo 保持已配置行为；后续只按对应版本事实升级。

## 一、一个配置入口，按 provider 和用途取值

继续使用现有 config.yaml / scripts/config.py。不新增 profiles 文件、许可文件、配置数据库或运行时自动猜测。拟增加可选项：

```yaml
llm:
  # 已有 provider/model/base_url/max_tokens 等保留
  generation_policy:
    deepseek:
      narrative:
        thinking: disabled
```

这是用途配置，不是材料授权。不改变已有模型、端点、密钥来源、8192 上限、价格、预算、profile 或存储上限。

建议最小接口：

- `LLMConfig.generation_policy`：provider → purpose → 有限生成选项；默认空。
- `LLMConfig.generation_options(purpose="general")`：返回无密钥的新字典。只解析当前 `self.provider` 的 general，再叠加当前 purpose；不返回别的 provider 的选项。
- `Config.llm_for_provider`：主/备用/显式 provider 继续保持精确 model、endpoint、env 名；带着同一配置映射选择，不能把主 provider 的已解析 thinking 值直接复制给另一个 provider。
- `model_options_from_config(llm, purpose="narrative")`：从已加载的配置投影到现有 HTTP adapter，默认遗漏仍不发送。批次 wrapper 仍是唯一组合入口，不能让请求中旧的 model/thinking 覆盖真实配置。
- `LLMClient`：用已有 workload 选择同一配置，保存解析后的无密钥选项；SDK/urllib 从同一值投影。SDK 的 thinking 放 extra_body，urllib 放正文；DeepSeek effort 顶层传递。显式调用参数与现存无配置兼容入口的边界要测试，不顺手重启 legacy writer。

已读当前 legacy init 的相邻风险：传入 Config 且另选 provider 时仍直接复制 primary 的 model/key/endpoint；fallback 初始化又未传 Config，会回到1024/default temperature，并丢掉用途策略。这两项是代码调查发现，需责任RED确认后统一通过现有 `llm_for_provider` 选择；不能只修叙述 HTTP 路径。fallback 不增加新的 dispatcher 或预算，继续使用已配置 fallback、既有调用/费用责任。

初始允许配置 DeepSeek 的 enabled/disabled 与 low/high/max；省略保持省略。其他 provider 尚未核实的字段不得被继承或自动发送。现有显式 HTTP adaptive 兼容测试不因此被删掉，也不把 adaptive 宣称为 DeepSeek 的合法值。非法类型、拼写或矛盾选项在配置解析时具名报错，属于请求有效性，不是身份/审批门。

## 二、真实计量，不把未知推理量填零

在既有 response/error/attempt 的有限诊断中增加可选 `reasoning_tokens`，来源只允许供应商 usage 的 completion_tokens_details.reasoning_tokens。须为非负整数、不能大于真实 completion 总量；0 与未知/null 分开。

无细项时 input/output 的有效总量仍照常结算。错误细项不能污染总量或被猜成0；超配置输出的真实8194仍全额入账，不 clamp。保留具名诊断及原已知总量，不自动重试未知收费调用。

若纳入失败 final content 回查，仅保存有界最终答案、长度和SHA，通过既有 scratch/cap/清理机制；不保存隐含思维链，不另造失败资料库。截断 JSON 永不作为有效摘要发布。先明确各层 DTO 和持久化消费接口再改代码，不能仅在一个异常上挂字段而丢在下一层。

## 三、版本与复用

生成策略必须进入实际 wire request 和现有 request/gen pin。相同来源、相同策略的新 AUTO 默认零调用复用；策略改变只重做对应摘要，不重复下载或重复解析原件。旧 failed job/attempt、unknown 费用和旧摘要都保留，不能倒改历史或复活 terminal job。

原 source/parse identity 不因 thinking 改变。旧省略配置的 request bytes/pin 保持兼容；新启用配置改变实际策略身份。原模型 response identity、prompt/parser/selector版本仍由各自责任层负责。

## 四、TDD 验收包与实施顺序

1. 先在 tmp config 写 RED：主 provider、精确备用、显式 DeepSeek三种选择；general/purpose合并；遗漏不发送；不串 provider；错误字段/类型/矛盾值；model/endpoint/key-env/8192不变；生产配置SHA不变。
2. 统一配置解析后，先对 SDK kwargs、urllib JSON、Narrative HTTP JSON 做同一策略等值测试。未配置旧行为必须仍绿；API key 不出现在正文、options、日志或 pin。
3. 固化输出责任 RED：thinking-only满槽空content、mixed截断、正常短JSON、reasoning=0、reasoning缺失、错误细项、超槽实际计量。检查成功和失败的每一层 DTO/diagnostic/attempt 消费，不能仅单元属性存在。
4. 集成既有公共 batch/read/另AUTO复用、策略变化及 worker恢复；真实 POST 使用本机 fixture，禁止公网和收费，own TEMP恢复初始状态。输入请求及production config不能写穿。
5. 代码工程绿后，在 MAIN 配置中一次明确 narrative 的 DeepSeek disabled，并记录配置/实际wire/pin。这一步依据原配置入口，不由 executor 按单份材料临时填策略。相关短责任测试并入已有入口，不新增每commit全量suite/收费CI。
6. 一个大节点真实复验四个原失败材料及一个未见样本，沿累计USD20/2M及旧费用，使用独立AUTO和既有原件。比较可回放精选业务事实、完整JSON、重要限定、真实input/output/reasoning meter、耗时和费用；不只确认finish_reason。若选择/格式仍失败，分别回对应责任层，不重复收费试运气。

## 交接输出

源码提交/配置diff、RED和集中GREEN原生命令、有限usage DTO及消费者映射、pin/复用/恢复证明、隔离目录恢复证明、真实复验对照。每条新增重要风险再写入 revenue-forecast-audit 对应检查卡及可复现夹具。工程完成、配置实施、收费实际验收分别如实记状态，不用CI绿代替业务提取或买方研究质量。

## 已有 RED 基线（2026-10-09 21:43 UTC）

`test_generation_policy_probe.py.txt` 在自有 TEMP 运行：primary/fallback/explicit 三条配置投影真实3FAIL，遗漏与非目标 provider 兼容2PASS，6.73秒；尚未实现新接口。生产三配置SHA不变，源代码未改，无 provider/model 调用；TEMP恢复初始不存在。原始stdout与命令/恢复证据见 `RED-config-policy.log/.json`。

第一次 pytest 前受 sandbox 临时目录写权限拒绝，未产生产品测试或费用；随后按已有授权在自有普通 TEMP 运行并清除那个空目录。环境失败不算上述3个产品RED。

## 配置投影阶段实测与范围修正（2026-10-09T21:59:36.563250+00:00）

独立worktree基于13a7648c，原full RED17FAIL/2PASS保留；当前配置/SDK/urllib/叙述HTTP114PASS及相邻入口55PASS，共169PASS；ruff五文件和mypy两公共模块通过。每次own TEMP均恢复、三生产配置SHA不变，全部模型为local stub，未产生供应商或模型调用。

接口复查发现旧设计“其他provider未核实即拒绝显式选项”多加阻断，且与现存HTTP adapter已经接受enabled/disabled/adaptive冲突。修正规则：显式provider/purpose合法配置可透传，省略仍省略、不继承别的provider；DeepSeek已明确协议仍拒绝adaptive，其它provider保持adapter原有有限值能力；不新增证明文件/人工许可/供应商allowlist。真实不支持参数保留API具名错误。原RED及错误设计测试历史不改，追加MiMo等合法显式配置RED验证修正，再集中GREEN。

以上169PASS不等于全截断根修或研究通过；真实reasoning meter、失败final content消费者、AUTO策略复用与真实材料复验仍在本卡后续步骤。

## 输出观察DTO与消费者细则（2026-10-09T22:05:54.915288+00:00)

复用既有AUTO，不迁移/另建任务数据库。实施分为可回放计量与有界失败正文两部分，集中整合再验收：

1. HTTP只从供应商 `usage.completion_tokens_details.reasoning_tokens` 取可选整数；必须0<=reasoning<=真实completion。缺失/null保持未知；错误类型/范围记有限 `reasoning_usage_invalid`，有效prompt/completion照计。`NarrativeModelResponse` 与 envelope/truncated异常携带同一观察；hidden reasoning_content不保存。
2. 既有 `HandlerMetrics` 增加可选 reasoning_tokens / usage_diagnostic。None字段在to_dict省略，旧三字段及嵌套HandlerResult字节兼容；四位置replay和旧error构造仍兼容。BudgetedNarrativeCaller把观察投到既有metrics，费用仍只算input+completion，不二次加reasoning。总结handler成功/失败均通过同一个metrics消费者，AUTO attempt.result_json持久化，terminal compaction继续保留外层metrics。
3. 公共batch的每文档可选model_diagnostics从真实summary attempt读取，包含attempt_id、已观察的reasoning与有限诊断；旧无观察结果保持旧字节形状。恢复和只读completed读取同一结果，不因诊断触发模型/新的reservation；未知和0区分。重启发生在模型返回但attempt未完成时，不能补造丢失reasoning；已结算总费用不受影响。
4. 失败正文采用有限typed diagnostic，经现有异常→caller→失败HandlerResult.result→AUTO attempt→public batch贯通。只取最终content，至多16KiB UTF8前缀，并受32KiB JSON及现有output/persistent上限共同约束；记完整provider响应SHA、完整final content SHA/长度、截断标志。完整provider body及reasoning_content不复制。容量不足退为量/hash/有限原因，诊断失败不覆盖原错误，不发布无效summary，不自动付费重试。
5. 先写RED验证0/未知/非法/bool/大于completion/真正8194超8192、不重复计费、旧字节兼容及成功/length/envelope三条观察路径；再验证summary持久化、压缩、真实local HTTP公共CLI、AUTO0调用复用、换策略仅摘要重算和失败恢复。所有夹具own TEMP恢复，无公网/收费；原M3缺失字段不补写或变成0。

phase1配置候选已正常commit `272973ebf576162acc31daec8f544e5e84bd2c04`，hooks全部通过，尚未并入生产主线。本细则不把第一阶段完成称为完整根修；失败正文实现和真实材料复验仍未开始。

## 推理计量集中验收（2026-10-09T22:12:57.701601+00:00)

RED计量15FAIL/3PASS（当时未知keyword拒绝3项并非新接口验收），实现后144责任/兼容PASS；公共CLI新增2RED均因缺model_diagnostics，改接真实attempt后2实际local POST/各1次零POST恢复及29模型合同共31PASS/11.45秒。成功terminal compaction和失败attempt均保留reasoning；真8194不clamp、reasoning为completion子集不重复计费；旧HandlerMetrics省略新增None字段，旧字节形状保持。own TEMP恢复、保护原件/foreign jobs，公网/收费0。当前只完成计量贯通，16KiB失败final正文仍未实现，AUTO换策略/真实截断材料/研究复验仍待，不能称全根修或目标完成。

## 候选计量提交（2026-10-09T22:16:19.038580+00:00)

正常commit62770fea（9文件、hooks通过、8.19秒），尚未并main；branch正常push已启动。扩展mypy时发现StrictModel基类fields调用的3个类型错误，AST核对其基类源文本与已发布13a7648c完全相同；12具体模型均是frozen dataclass。把空基类也明确为frozen dataclass后，四公共模块mypy通过，29既有模型合同全部通过；未加ignore/放宽断言/新增字段门。原首次static失败日志保留，非新reasoning算法失败。

## 支线发布实测（2026-10-09T22:20:31.313704+00:00)

62770fea已通过正常git push发布到origin/codex/m3-generation-policy-20261009，随后git ls-remote核对准确SHA、本地工作树clean。首次记录程序以UTF8读取Windows git输出时UnicodeDecodeError，发生在communicate读取完成；原stdout未保留，不能补造prepush测试精确计数/耗时/returncode。远端状态另有原生只读查询回执candidate-generation-push-observation.json。未绕过hooks、未再次推送或收费重试。精确GitHub查询暂无该支线workflow，不能声称CI绿；CWP现main13a的独立精确CI成功仍有效，新源码尚未并main。

## 本地主线并入（2026-10-09T22:23:21.280615+00:00)

正常merge45533e881b98fe8782b0e496abf7a4bb2904114e，源62770fea，三production配置SHA不变，详细merge原字节/log/JSON已保存。远端main/精确CI仍待。只合已完成配置投影与计量观察，不宣称full model root或当前goal完成。
