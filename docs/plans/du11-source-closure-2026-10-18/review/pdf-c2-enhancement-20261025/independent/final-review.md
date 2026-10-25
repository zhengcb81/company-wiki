# PDF-C2 最终独立质量审查

结论：**PASS，0 OPEN**。只对同名 JSON 中的最终 8 个源码、3 个测试及 pyproject.toml 的 LF SHA 快照生效。没有批准发布、手工权限或代签精确 CI。

## 根因闭环

- **F1 几何证据**：中心点准入已由完整原块覆盖证明替代；字体四分之一 em、2–3pt 的有界 padding 保留严格来源、页、frame、字符、顺序和唯一连续成员检查。2pt 细条反例拒绝。
- **F2 DTO 边界**：response/items/provenance/bbox 的错误结构均转为显式原生回退，私有错误文本不进入持久观察。
- **F3 需求路由**：复用 native continuity 排除已闭合边，删除第二业务词典。全 HK 原件自然需求 12/13/17 页包含真实缺口；IPO 的两个独立事实原本已完整，未冒称新增召回。
- **F4 配方身份**：模型、config、直接 SDK/Python 与 worker/调度/对齐源码 SHA 均绑定。终审又识别固定依赖名单漏掉 docling-parse/transformers 的共因，ROOT 已用整个可选 ML 环境的 distribution 名称/版本指纹根修，worker 在 import SDK 前核对、response 同绑定；新增漂移反例通过。该策略会保守失效，不要求逐包人工维护。
- **F5 实际状态持久化**：增强成功、无需执行、timeout 回退、坏 JSON 回退四条生产读取路径均写入 reading_context，经真实磁盘 JSON 和正式 `_reading_context` 校验恢复后完全一致；重放不启动模型。

## 独立验证与证据口径

独立 33 项 focused 测试通过；最终环境身份修复后只补 1 项漂移反例和稳定源码 probe，没有重复重模型实验。ROOT 的 229/33/36 与本轮测试重叠，不能累加；最终新增 34 项收据另行绑定。

按原收据的 Python 3.13.9 / PyMuPDF 1.26.7，从只读原件独立核验 final-frozen-v4 的 29+19+15 个 span，以及 live-v5 的 HK 29 个 span，全部原文、来源和 locator 通过。实际 summary task 的 support/text/locator 引用逐项一致，无瞬态 membership 残留。最初误用 PyMuPDF 1.28.2 时 HK 12 个 span 不一致，已保留反例；不同 native runtime 应使旧 generation 失效，不能只凭 parser semver 声称跨版本一致。

真实 live-v5 收据证明全原件自然 12/13/17 页由一个 Docling converter 完成、3 个接受组，81.1026 秒低于 120 秒，Job committed memory 峰值 3,327,328,256 字节低于显式 4GiB cap。它早于最终 F5/环境身份/Python3.10 流式 SHA 兼容补丁；这些窄改由静态审查和中性验证覆盖，没有声称最终 SHA 又跑过一次模型。

旧八项仍保留 6→7/8，IPO 跨独立事实旧组仍 false；版本化逐事实 8→9/9 单列。五页暴露样本不能冒充新盲测。默认纯 native、显式配置增强、单 read 多页热复用的边界清楚；跨文档 warm pool、正式 LLM 语义、C3/cache 恢复/RF 及发布 CI 未代签。

本审查 0 模型调用、0 下载、0 原件副本，未改生产源码/config/PWF/作者工区。生产 config、catalog 和预算文件 SHA 保持不变，独占短临时目录全部恢复 absent。所有源码、测试和现成收据 SHA 详见 `final-review.json`；验证过程见 `probe-result.json`、`tests*.log` 与四份 `state-*.json`。

## 静态类型收窄补充

正常全 src precommit mypy 发现 paragraph_index 的 int | None 推断。ROOT 只新增 first_paragraph 局部变量及严格 int guard，再供 range 使用。原 any 检查已通过短路拒绝同一非 int 集合，因此准入行为不变。独审通过精确反向补丁重建先前已审 SHA，证明只有这处变化；其余 11 个绑定文件不变。最终 JSON 已更新源码 LF SHA，细节见 `supplement-type-narrowing.json`。没有重复整包、模型或原件回放；原验证证据与范围限制继续有效。
