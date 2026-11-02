# R7 invest CI：legacy版本夹具与测试环境根修

状态：**4文件冻结，待独立增量审查/ROOT正常发布**。基线 `a781288893adcd5ef6cc86c739a985b4950e098d`。只改两份 tests_support/revenue_fixtures.py、root conftest.py、新test_revenue_fixture_compatibility.py；实际runtime、RF兼容矩阵/crypto/config、全局技能、Git/index均未改。精确SHA见同名JSON。

## 共因与版本来源

远端CI `41427481853` 只报exit1，ROOT同集复现 **1F144P1skip/23.95s**。旧builder从当前run_forecast取结果，只把schema改为3.4，却沿用当前engine4.3.0。RF文档合同从来不支持这个pair；运行时正确拒绝，不能放宽validator。

已读RF公开 `SCHEMA_EMIT_ENGINES`、CHANGELOG来源说明与RF自身schema兼容测试。没有现成冻结的legacy forecast JSON；RF自己的历史兼容测试也使用明确历史pair的synthetic projection。本修复从固定legacy schema3.4的公开matrix确定历史emitter（现3.5.0），不引用移动的当前ENGINE_VERSION。注释明确：**这是synthetic read-only兼容投影，不是历史实物或执行旧binary的证明**。使用当前formatter后的receipt也按该synthetic schema/engine重新绑定并重算receipt/result hash，attestation仍真实unattested。

新测试另外发现，旧投影直接修改provider返回dict。现先deepcopy，未来provider/current版本标签与共享缓存都不会被legacy投影污染；public load_revenue_fixture保独立副本。不存在公司名/模型特例补丁。

## 测试环境旧残留

root conftest原有“registered+host_signed默认门”说明，并把sys.executable设为签名provider；这既不是真签名配置，也无必要。现collection前禁生产dotenv、去默认host signer，session仍隔离registry。显式签名/篡改测试自己配置有效签名路径；没有改签名真实性规则，未把unsigned标成signed。

首RED还暴露本机framework测试把HOME已安装skills插到sys.path前端，可能覆盖仓内invest_contracts。最终不靠临时launcher：root conftest统一先载canonical `invest-core/scripts/invest_contracts.py`，独立部署测试应使用明确fresh子进程。fresh probe确认canonical文件 SHA `50d4126b441dc4fe0734b92382d9155f6cd876ead5d71acbcdee28ac3b57802a`，该runtime未改；RF兼容owner来自canonical sibling，SHA `7aa6803b4567fb28d9797a406256a07834d6fe7ddddeaaae9b9f4f3f087ff9e5`。这只是测试代码选择，不是生产许可或全树clean门。

## 实际RED/GREEN

- 新fixture/默认环境＋旧失败点：**6F4P/2.32s**。包括两份真实无效pair、两份共享provider dict被改、旧伪signer、原framework失败。缓存副本和无效pair反控原已绿。
- canonical默认入口另1真RED：ModuleNotFoundError，**0.10s**；原先依赖其它测试先改sys.path或安装目录。
- 首实现 **7P3F/2.76s**：两项是测试误把flat `attestation_status`当嵌套结构；一项为synthetic receipt formatter仍写current engine。只改正确fixture字段和其receipt绑定，未动实际validator。历史日志保留。
- 最终直接普通pytest（不再临时preload）：**11P/1.43s**。两包有效版本pair、未来provider标签和共享dict、缓存副本隔离、无效pair重算hash仍拒、原framework明确legacy_read_only_validated均通过。
- 必要相邻core adapter/R7 adapter/三跳：**21P1skip/0.76s**。没有修改这些旧测试oracle，经济数字和跨层篡改继续拒绝。
- 四Python文件Ruff通过。没有重144/全十模块或冒远端CI已绿。

JSON保存命令、日志、canonical路径/SHA与matrix实值。原publish已签14路径中两fixture属本改动，其它12路径SHA均不变；RF四份既有assurance WIP前后SHA也不变。

## 交接与恢复

ROOT可独立审4文件增量后正常commit/push；不需要为测试夹具全量复制全局技能。Owned `C:/Users/郑曾波/Projects/company-wiki/tmp/r7iv` 初始absent，保存日志后核绝对parent containment与root/后代non-reparse，仅删除该已知目录：13文件/67,769字节，exists_after=false，已恢复初始absent；真实收据见JSON cleanup。不清理他人历史目录或原件。
