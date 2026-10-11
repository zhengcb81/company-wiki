# W08 官方 JSON capture provenance：独立只读复核

日期：2026-10-11。结论：**主链和职责接受；一个非阻断 URL 分类细节需要定点修复。**

## 证据与范围

只读实际 import/writer 差异、新 public provenance 测试、owner HANDOFF 与原生日志。isolated CodeGraph 未初始化，未写索引；canonical CodeGraph 用于确认 writer/reader 结构，随后按已知实际文件读新源码。没有原件、配置、数据库、Git、安装、消费者、projection/P7/schema 或纯策略写入。只做两条小内存 helper probe；未复跑58测试、9秒 public case、pure122 或预推送。

HANDOFF SHA `b2f67bc8d20327b898a15916bec86bf94a7f83348a175e01354c7c2c0125b559` 与实际一致。原生 RED **6 FAIL/14.71s**，全由 placeholder 来源链接失败；集中 **57 PASS/1 FAIL/26.53s**，唯一后续失败是测试误认 persistent metadata 的顶层容器；改为实际 `metadata.acquisition.source_url` 后同公共 case **1 PASS/9.10s**。因此是58项职责的并集通过，**不是一个58PASS整包日志**。生产没有为错误测试容器而变化，没有 skip/xfail 或改低期望 URL。所有 owner 所列六个 log SHA 已逐一核对，Ruff、mypy 原生绿。

## 已接受

- `official_json_import._commit_shared` 唯一改用已验证 capture receipt 的 `_captured_source_url`；其余一次真实原文 SHA/size、结构识别、失败保留、恢复和一次入库路径保持。source_url 由 producer owning layer 提供，不要求消费者读 sidecar 或猜 issuer/body。
- 若现 receipt 直接包含 url，使用该直接观察；若 absent，读取原 capture observation，只有 content_sha256 与 response_bytes 对应本原件才将既有链接提升为 source fact。outer import request/actual bytes 的验证仍由原层完成。坏/未知 URL 以 None 表示，不因缺 URL 拒收原文，也不添加身份/权限门。
- canonical writer 只把两处 source_url 类型改为 nullable。已有 _SharedOriginal.to_dict/immutable sidecar → scanner acquisition metadata → describe_version → SourceExportBundleV2 足以公开 source_url，没有新增 schema/消费者补丁。
- 公共测试是真实 subprocess CLI：两个不同原件/两issuer project、persist、reopen、replay、export；来源URL、unknown publication/display_name；仅两份 shared raw，issuer各自 record IDs；同字节 reimport download_events=0、ref/export/原件/config不变。
- 无URL、userinfo坏URL、另页SHA、错误size都真实 import + public manifest 回归为 None，body_link 不用作 provenance。
- 提交失败保留实际 capture receipt 与原文字节，恢复走同 producer helper，completed recovery 返回同ref、清理 staging；真实 source open验证原字节。
- 旧placeholder记录通过旧writer真实建立；后来同SHA捕获真实URL，dedup仍保持旧immutable metadata、sidecar与原件。没有悄悄重写历史来源事实。本修复不宣称历史placeholder迁移或86真实页面/W09研究完成。

## 具体遗漏与原生反例

`official_json_import.py:205–207` 现仅排 `isspace() or ord(char)<32`，未排 ASCII DEL（U+007F）。两个纯内存probe见 `minimal-probe.json`：

1. 同SHA+size原nested observation中 `https://official.example/qa?page=2`，期望/实际均原真实URL。
2. direct receipt URL 为 `https://official.example/qa\x7f`。DEL控制字符无效，期望None；实际原字符串返回。

这属于**不将坏观察提升为来源事实**的小边界，不是许可/下载门。建议 owner 在该既有 bounded URL 分类中排DEL并补负控，仍返回None继续原文入库；不新增注册库、authorization、provider调用、HEAD校验或消费者适配。只定点跑新负控即可，不需重复58/public case。已将精确失败交ROOT；修复前不把“所有控制字符坏URL均未知”声明为已成立。

## 保护与冻结

5个精确文件（两producer/writer、独立test、TXT原件与生产config）运行前后SHA见receipt；不将另一owner正在变更的pure policy/test加入保护，不扫描全src。原log按原字节SHA核对，无重编码或改写。自身probe不创建TEMP/DB/HTTP服务；0 vendor/model/费用，0原件配置写。只写本自有evidence目录。

本报告冻结到当前 `83402ff4… /26d9c475… /84c1abf4…` 快照。未来修复另记补充结论，保留本轮真实反例。
