# F3 独立审查：PASS

审查绑定 base HEAD `a8eef273a90ac1ddb0f79f8bdd36e7c47f8eb377` 上尚未提交的实现，五个源码/测试文件逐字节匹配 `source-freeze.json`，运行前后均未变化。最终完整 SHA 见本目录 JSON。

## 实际审查

- 已读 handoff、freeze、实际 runtime diff 和全部新测试，未仅依赖作者签收。
- `security_code.py` 是严格、按市场定义的唯一格式/等价 owner；resolver 和 candidate 投影共用。发现别名仍由原身份库承担，没有新登记库、RPC、许可或公司特判。
- `describe_candidate` 只用来源自身的 market/security 形成规范化投影；没有借用请求 market。`describe_version`、source facts、sidecar 和 raw 保持观察值。
- HK/CN 数字宽度有界，非 ASCII/超宽保持字面；US 只规范支持 ticker 的大小写，点/横线类股不被合并；未知/缺失市场不获得新别名。原字节/期间/as-of/冲突路径未被放宽。
- 独立运行 **37 PASS，13.20s pytest / 16.21s wall**：包含两次真实未改 FF CLI→实际 CWP 身份/查询、2 calls / 0 downloads；两方向代码表示复用、真实二进制 open/SHA、同大小篡改零字节拒绝、unknown/future publication 及错误身份/年份反控。
- pytest 自动迁移的有效 basetemp 日志确认 `removed=true`；外层独立 TemporaryDirectory 已删除；fixture 还核对 sentinel、恢复合成篡改并移除其 owned tree。源码 SHA 运行后仍一致。

## 结论与边界

未发现必须修复的实现或测试缺陷。F3 冻结实现可交作者正常提交、ROOT 接收。此次审查不等于整个真实 HK C 或 RF 消费链通过；ROOT 仍需用已有成功摘要/恢复资料重放失败 consumer 节点，不需要再发模型请求。

只执行此集中小包，没有全 Unit、大 PDF、下载、真实供应商、密钥或付费调用；没有改实现、FF 外包文件、生产配置或原件。完整执行命令、XML 与日志在本 review 目录。
