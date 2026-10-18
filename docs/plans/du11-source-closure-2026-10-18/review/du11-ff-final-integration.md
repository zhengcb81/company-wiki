# DU11 FF 修复与 CWP 配套接口：独立最终复审

## 结论：PASS（有限工程接收）

原接收报告的两项必修问题均已闭合。可以进入 ROOT 的正常提交、并线和大节点回归。此结论不表示全部项目或真实内容质量 C 已完成。

## 实际绑定

- FF ROOT 工区基线 `8a83e27863269b14c897dc2c7ba953f3b9102ef1`；未改作者工区。
- CWP ROOT 工区基线 `f5a26b48c8facfe8e9ad8ecdda2099e340c41a18`，只覆盖实际冻结的两个 reader 文件进行接线验证。
- FF transport SHA：`4bb18006bb608c3dc706a6ca3f70e77fe03513798ff815b464aad208a8f33026`。
- FF 新测试 SHA：`9ab30a5ba0f02c0753fb785b45b571cac6c5009b757827eb2d5213e959ca8318`。
- CWP reader SHA：`89cbc7ef9d6c99ab9bac743b17505b66328edc4cfb4f1125ae7bd5d6795eea63`。
- CWP reader CLI SHA：`7510ae0244a61cee61a201a32dff1a21ee637518d8b2e916271414dd6e101876`。

上述四项在自有测试快照和执行前后原工区均精确匹配；没有用旧依赖库通过记录冒称新接口已通过。

## 静态复审与原问题闭合

1. **发布日期误复用已修。** 最终 manifest 的 None 不再回填旧查询日期；当前日期使用既有 ISO 校验及 as-of 比较。未来、无效和新未知日期均不能再生成 `reused/as_of_cutoff_verified=true`，且不触发下载。
2. **跨市场去零已移除。** FF 消费 CWP `source-canonical-identity/1`；证券格式转换仍只由 `security_code.canonical_security_code` 负责。US `0MSFT` 不等于 MSFT；合法 HK 数字补位经来源 owner 明确投影，而 observed manifest 不变。
3. **显式 provider 保留真实约束。** 当前 manifest provider 未知或不匹配时返回失败、零 provider 调用，不伪造 FMP 来源。
4. **读取保持一个观察。** CLI 使用 `open_described_version`，same manifest 提供身份、scope qualification 和政策指纹；sentinel 区分“未观察”与已观察的“不适用”，避免 filing_reuse 重复 describe。有效旧 lineage 不变成人工许可；malformed pin 仍拒绝。默认无新 flag 的 CLI 保持原 receipt。

## 独立执行证据

在自有源码归档快照内执行，原作者和 ROOT 产品文件均只读：

- **28 项通过**：24 个新增边界控制与 4 个此前独立失败反例。覆盖未来/无效/未知日期、缺日期字段、有效截止日/闰日、US 错码、HK/CN canonical 投影、损坏投影及显式 provider 未知反控。
- **1 条真实跨仓联调通过**（pytest 14.477 秒；含归档准备 21.83 秒）：临时登记 HK TXT，实际 CWP scan/query/reader → 实际 FF companion/transport；观察代码 `9896` 保留，canonical 为 `09896`，原文 SHA 匹配，复用成功，**ET 调用为 0**。
- 同一联调验证：不传新 flag 的旧 receipt 无 canonical 字段且可正常读取；传 flag 获得真实投影；刻意篡改原文字节被真实 CWP/FF 子进程拒绝，随后恢复 SHA/mtime。

这是跨次执行共 **29 个唯一通过用例**，不是一次 29-PASS 运行。没有重跑已接收的 102 大组。Gold 34 PASS 和 ROOT 59 PASS/37.37s 的实际日志仅作为绑定版本的已有证据复用，不列为本审查独立执行。

## 两个自有测试问题如实留证

首轮 28 PASS / 1 FAIL 是最小环境未给 USERPROFILE，既有配置读取的 Path.home 在 scan 前失败；自有环境改为 Temp 内合成 USERPROFILE，未继承真实用户环境。第二轮真实复用与接口验证已成功，但篡改反控错误地只期待 ValueError，实际 bounded transport 正确抛 ChildFailed；修正自有测试期望后，该真实联调通过。两个失败日志、XML、收据完整保留，未改产品源码迁就测试。

## 清理与边界

所有轮次网络尝试 0，最小环境没有继承凭证，不加载 dotenv 或自动插件，使用 -B、no:cacheprovider、独立 basetemp。所有自有 Temp 已删除，sentinel 未变；临时原文字节及 mtime 恢复，作者仍干净，四项受审源字节不变。未读取真实密钥或原件，未访问收费 API，未修改生产配置或安装技能，未提交/合并/推送。

仍 OPEN：ROOT 正常发布与大节点回归、真实供应商运行、摘要内容质量 C、跨页与指代、完整 PWF 其余任务。语言偏好不是现 companion 请求字段；本次证明原语言复用，不额外声称实现偏好筛选或所有并发崩溃恰好一次保证。

精确命令、归档 SHA、运行结果及清理状态见同名 JSON 和 `du11-ff-final-run.json`；独立控制和可重放隔离运行器也保留在此目录。
