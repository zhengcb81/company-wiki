# W11 实施细则

## 最小公共接口

在现有 `capture` 增加可重复 `--freeze-input <file>`；这些选项放在已有 `--` 之前。仅显式指定模型/请求JSON等小型输入，不自动遍历公司库或扫描所有argv路径。每次call的新UUID目录保存原字节input快照；记录original path、frozen path、SHA256、byte_size、observed UTC，未配置freeze兼容原调用。输入内容不打印到CLI/stdout/event。

freeze必须发生在实际启动子进程之前；运行argv中的原输入路径替换为已冻结路径（独立path arg或flag=path，支持相对cwd与空格/Unicode），而不是仅复制却继续运行易变draft。只替换明确定义的输入路径参数，禁止对任意Python代码/字符串做子串替换。显式输入未找到对应参数时有限本地错误，不假称已运行。重复同物理输入只copy一次；两个不同输入即使同basename也无碰撞。

沿现有capture资源限制再加 `--max-input-bytes`，默认总共4MiB，独立于输出每流1MiB；流式copy/hash，超限不启动、不留可当成功用的半截文件，当前call保留有限错误/UTC。不得复制raw/PDF/凭证、不得隐藏地把上限按单文件倍增。无credential文件或外部正文需求；输入JSON不按RF业务规则预解析，非法JSON同样应可留证并交原生validator失败，原字节不能经json roundtrip。

本次实际python版本、平台、capturer源码SHA记录在pre-call元信息；工程安装/config指纹沿用协调员已冻结的非秘密scope/runtime artifact引用与SHA，不对所有仓库重复跑身份或读盘验真。MAIN M3生成该一次冻结context，再由每call引用。未提供context的旧call诚实空缺；不得猜历史版本/UTC。

在 `command_started` 先持久记录输入快照、原始脱敏argv和实际执行脱敏argv；finished沿用exit/timeout/output_complete/known or null cost语义。启动失败/非零/timeout仍留下相同快照。若快照本地失败，有限失败记录明确child未启动，usage未知/零是否能证明沿现有规则，不抹掉错误。新文件逻辑write-once，不加OS权限/人工许可机制。录制目录由本call专属，关闭handles后只清理它自己的未完成中间文件。

## TDD先写的责任测试

- 先写失败draft、调用原生validator失败，后改同draft再成功；两call快照不同SHA且第一份仍是原非法字节。
- actualchild打印它实际读取的文件内容/SHA：启动前draft被另线程改写，child仍消费冻结副本；确认不是‘只保存’。
- Unicode/空格/relative/flag=path、多file同basename、重复file、零字节/非法UTF8/非法JSON；保留精确原byte，不json重编码。
- 未声明freeze保留旧行为；未匹配argv/不存在file/超过总cap/输入copy中断与变化：不启动子进程，有限错误，未完成副本不冒充成功。
- 非零nativeexit、启动失败、真实短timeout与stdoutcap同时保留input、UTC、output_complete=false、usage/cost=null。不要把冷启动耗时误认为业务deadline bug。
- 环境/argv synthetic secrets继续现有redaction；原始draft不被修改，测试所有文件在独立TEMP，结束恢复不存在。

## RC23交付责任

现有RF trust generator/contract先只读核对。若代码已经符合，不新增生成器；用实际renderer构建TRUST_BOUNDARY.md+真实JSON并验证一致。资料document matrix建立actual request/call/result引用索引：请求即使失败也允许，但不能指向不存在/旧已被新版取代且未说明的产物。registered IPO结果和来源引用同request；融资金额不是营收。修新attempt authoring流程，不改旧封存文档、不对历史补造文件。

## 大节点验收与发布

一次集中run audit仓全unittest与skill-creator quick_validate；跨仓离线原生RF验证/计算/渲染/assurance，至少原历史缺口类型+不同公司的合成authoring输入。独立agent只读复验原字节、真正消费frozenpath、真时间/版本、错误路径、两个交付状态。保留RED/GREEN/准确命令/退出/清理；无外部HTTP/收费。

正常commit，仅同步本次接受的实际差集到已有.agents/.claude技能物理根，保存before/after SHA与unselected drift0；不替换整目录/配置/output/unknown。无remote不创建远端；MAIN原三家M3使用新capture，独立storage/process再验收。旧原字节/首次未知费用不可恢复的事实永久单列。

2026-10-09独立major审查：既有11测试绿仍有真实P1输入/输出同路径覆盖历史，以及P2声明清理错误遮蔽主故障，暂未验收。新增4控验真实1FAIL/3ERROR→15focused PASS/2.263s。实现显式argv位置/歧义不启动、原字节历史与执行副本隔离、公共atomic writer保留主故障、post-call有限输入完整性且child真实exit保留。旧重复读入正例用明确实际input indices，未降断言。第一次写测试仅CRLF marker定位失败，故原日志重命名prior_tests_only，不冒称RED；真正review_residual_red保留。下一步完整suite、新版本native联调和独立复审，一次大节点通过后commit/install；零外部费用。


## 独立审查后的输入绑定修正

同一路径在 command argv 只出现一次时自动绑定；出现多次（例如 --input 与 --output 同名）必须重复 --freeze-arg-index <整数> 指明实际输入 token。索引按 -- 后的实际 command 计数，exe为0且不可选择，flag=path整体为一个token。未明确的输出保留原 argv；每份 selected 输入至少有一个合法绑定。歧义/错误索引记录有限失败而不启动 child，这只是命令参数含义，不是人工许可。

frozen_path 是本 call 的原字节历史，consumed_path 是从已验证历史副本生成的同 SHA 执行副本；executed_command使用后者。只有逻辑输入总字节计入既有4MiB，录制产生的两份物理副本合计最多8MiB（2×显式上限），没有扫描/复制 raw。运行后有界观察 consumed 是否改变；改变时 input_complete/output_complete=false、保留具名诊断和 child真实exit，timeout等主失败不被覆盖。不能用当前 consumed 冒称原输入，历史副本仍保留。

公共原子写入与输入清理均保留 primary failure；次要 cleanup_failures单列，不以清理异常替换根因。正常成功不再对已rename的临时文件做无用清理。
