# W04 LLM 配置责任层交接（STOP）

## 结果

Config.load_llm(config_path=None, *, llm_provider=None) -> LLMConfig 已实现；摘要 CLI 只加载 LLM。完整 Config 与新接口共用 YAML/default dotenv 读取、provider/profile 构建、显式选择和参数验证。新接口始终严格验证所选运行凭证，pytest marker 不再放松；缺主密钥不会自动改用备供应商。LLM-only 不构建、不检查 search/wiki/schedule 等不参与摘要的配置。

## TDD 和主要节点

- RED（产品未改）：26失败/2通过，主要是 load_llm 尚不存在。发现新测试 raw_paths 字典迭代错误，产品改动前修正；另存真实 CLI RED：NARRATIVE_MODEL_CONFIG_INVALID。
- 初次兼容节点：101通过/1失败；唯一原因是 sparse checkout 缺 config.yaml。ROOT 授权补 exact HEAD blob，不改生产配置或测试期望；内容与 canonical 相同，仅 LF/CRLF 不同。
- 最终节点：102通过，17.75秒（进程墙钟20.699秒）；新责任层测试28例。Ruff PASS，git diff --check PASS。13条既有 unit marker 警告如实保留。
- 真实子进程无 TAVILY/pytest marker、Wiki路径不存在仍正常运行；本机假 HTTP 与有限子进程 Worker 完成原语言摘要，一次请求，artifact_ref 有值，合成实际账92 tokens/111 microUSD、未知/未结算为0，原字节和配置未变。隔离 run 删除后保留原有 keep.txt。

## 精确范围

- scripts/config.py：共享 _read_config / _build_llm / _select_llm，LLMConfig 参数验证与 load_llm。有效配置的模型、URL、凭证来源、generation_policy 不变；非法 bool/string/NaN 数值、非bool reasoning_split/enabled、非正 max_document_chars 改为明确拒绝。None temperature/max_tokens 保持旧Config兼容，HTTP适配器仍负责线协议要求。
- scripts/narrative_batch_configured.py：入口从完整 Config.load(...).llm 改为 Config.load_llm(...)。
- 新 tests/unit/test_w04_llm_config_scope.py：真实生产反例、严格凭证、精确profile、环境规则、无自动fallback、非法参数、LLM-only依赖隔离、完整Config兼容和本机假HTTP。
- 获ROOT授权的既有 test_narrative_model_config.py：仅两个参数化mock入口 load→load_llm、返回Config→LLMConfig；断言完全保留。

没有 commit/push。新测试未跟踪，tracked_changes.patch不包含它；ROOT需同时接收四个文件。产品SHA和全部真实日志收据见handoff.json/bounded_manifest.json。

## 未执行

0外部HTTP/provider/model调用，0真实费用/token，0生产config/原件/注册表/AUTO/安装/其他仓/共享PWF/旧run改动；已完成只读准备目录保持STOP。没有新policy、purpose flag、授权文件或人工门禁。真实G2运行与母账分配仍由ROOT负责。
