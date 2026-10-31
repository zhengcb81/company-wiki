# P0 独立审查

结论：**PASS_P0_TEST_CONTRACT，0 OPEN**。仅签当前预算阶段/紧凑延期合同修复；不签远端CI成功、P1真实摘要/缓存或P2 RF采用。

审查人 /root/p0_contract_review 未参与实现，生产src diff为空；未改产品、共享PWF或父测试，未跑父39/101/3模块、全量、收费/下载。原根因是固定4/5/6预算在新增Q/A前缀观察就耗尽，未命中原lookahead阶段；原deferred示例ID断言不等于完整未分析状态。当前frontier0表示全部未分析，不能认定已经释放错误片段。

修改保留并增强保护：早停必须完整frontier0、无window/standalone、work不超界；真正进入witness-native和tail-geometry时在真实scoped账户注入拒绝，精确阶段entry且一次，未证明左片仍延期。实际可闭合source正对照防止故障夹具天然不可读。三个compact消费者case跑真正_candidates，不以示例ID代替完整range/frontier。

另做3个独立纯内存探针：frontier1只阻挡后两段而保留首段；中间range仅阻挡中段、保留前后；去掉ID样例后同range仍相同。这证明不是把任何partial整份丢弃来换绿，也没有遗漏延期源。探针输入全部为内存sourcecase，未修改原件/config。

唯一小夹具问题（range更换后计数仍沿用positive0）已告ROOT并修正；最终3消费者节点3P/11.22s。父初39P/19.22s、相关101P/16.09s日志均独立读取确认，计数有重叠不累加。最终文件raw/LF SHA见seal.json；规范输入、生产额度与原文没有改。

建议按现有PWF正常发布、观察精确CI；无需新增小门禁或第三次全量运行。
