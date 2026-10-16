# ROOT：统一准备、预算与生产接线施工记录

2026-10-16；承接 `du4_production_integration.md`，不是新的许可链。DU5 三包实现已接收；当前母计划仍未完成。

## 当前共因与责任边界

- `pipeline.understand_units` 是组合 owner：一次 adapter 投影，内部复用已有来源材料，不重复下载、解析原文件或验证来源身份。
- 工作预算沿现有 `layout_hints.contract.WorkBudget` 传递；探测单位/字符、选择数量、HTTP/token/费用是不同限制，不能混用或新增账本。
- 当前 layout 在预算前 deepcopy/组页，layout parser 在预算外全量验证和复制，bridge 耗尽时再次扫全结构，route/profile 重建 UnitRef。必须用真实访问/复制反例修根因。
- 完整公开 observation 的基础 O(N) 物化与可选增强分开记录。零增强预算不能同时保证完整独立输出和不读取输入长尾；组合入口允许薄 partial，保留上游原件和 parser 原单位，未读不写成“没有业务”。旧 standalone 正值 limits 规则不机械放宽。

## 实施顺序（只有原 A/B/C 大节点）

### A：先测试固定边界

固定零预算正文访问、深复制、route/profile 重复准备、统一预算对象、耗尽诊断不再全量扫描；保护同 parent、QA 闭包、旧输入不变与 standalone 结果。确认真实调用者如何消费 partial，不编造可用端口。测试目录只新增 ROOT 自有范围。

### B：共同 owner 和生产组合

1. 复用已有不可变 profile Observation；route 和 policy 用同一准备结果，不增加第二 canonical schema 或授权文件。
2. layout 建模和 context binding 接受同一 WorkBudget；内部结果只为改变的字段建立 overlay，旧 standalone 保持独立可变返回语义。预算先于长循环/正则/复制；耗尽保留已知来源、明确未读，不续预算。
3. pipeline 建立唯一工作所有权和可复查 partial；source-level 准备只执行一次。结构中尚未实际计费的工作必须明确标出，不能把估计称硬限制。
4. 统一准备后依原细则接 FORM→STATE→TABLE 和 v4 runtime。旧 v3/paid 历史 wire 保留，v4 不在未知质量下切默认。

### C：集中工程与真实摘要

集中单元/集成、worker→loopback→decode/verify/outbox→公共读→RF 离线链，以及现配置供应商真实摘要。保留原错引/遗漏/召回分母，逐 claim 和方向覆盖审查；原件/配置/已有 registry 与测试 sentinel 保持，测试 Temp 删除。正常提交/推送，精确 SHA CI；只在大节点审查。

## 并行分包原则

ROOT 独占 CWP src、预算/来源准备/三组件/v4/恢复与总 PWF。新包优先 RF 数值目标责任、AUDIT 公开 bundle 的审查包适配、FF 可隔离责任；必须先核实际代码与冻结现有接口，再给独占目录和白名单。外包不改 ROOT 入口、不写其他仓、不安装技能、不合主线。

## 实施日志

- 2026-10-16：已恢复细则和已发布源码。CodeGraph 已用于结构入口定位；只读调查和施工卡范围研究进行中。此前错误猜测的 `tests/unit/test_document_understanding_pipeline.py` 不存在，已改为实际 `tests/unit/document_understanding_root/test_du_root_pipeline.py`；未据此推断产品问题。尚未把设计写为实现完成，尚无新增 API 调用。
