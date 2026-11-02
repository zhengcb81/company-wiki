# R6 source observer — 有界收据编码根修

状态：**FROZEN_FOR_ROOT_INDEPENDENT_REVIEW**。仅新增`tools/source_case_receipt.py`与`tests/unit/test_source_case_receipt.py`；ROOT负责ignored runner接线、原子保存与最终独审。本线未改src、配置、原件、模型、数据库、Git/index或主PWF。

根因是旧观察器在真实select返回后，将完整大记录一次indent JSON并检查300,000字节；超限直接异常，整份前后验证与关键上下文都丢失。问题属于验收收据表示，不是来源选择失败，也不能给丢失的v3运行补造PASS。本次不重读任何原件、不重跑真实公司/模型。

## API与责任

`encode_source_receipt(record: dict, *, max_bytes: int = 300_000) -> bytes`，仅stdlib；ROOT先jsonable。非法cap（非严格int/bool或<1024）前置ValueError；可在source前用空记录预检。默认300k不提高。结果始终为不超过有效cap的UTF-8 JSON。

成功编码保producer全部顶层字段，附独立`receipt_representation`元数据；该元数据明确`complete`或`compacted`只是编码表示，不升级source coverage/processing_complete或producer status。原status/error不改。

超限时仅删除`span_original_member_index`重复raw_text，保span ID、locator、native_members、valid_slice、既有hash与其他索引，并给出实际UTF-8 bytes/chars/SHA。若同名producer计数/hash已存在也不覆盖；独立计算另在omission记录中保留，避免偷偷修证据。`source_excerpt_units`（ROOT采集required12+原9context）及required/context checks、view/closure/source package索引不裁剪。

`reading_context_observations`只允许省略大于4096 canonical bytes且名称表明trace/deferred/diagnostics/debug的可选观察。独立omissions记录完整path、canonical流式SHA、bytes、count；小complete/coverage/count/status原状态保留，debug内部小状态放独立`retained_observation_states`路径清单，不用摘要冒充producer原trace对象。其它未知大字段不擅删。

canonical完整记录SHA/bytes以sorted compact JSONEncoder.iterencode累计，不构造整份大JSON字节副本。stdlib可能把单个巨字符串作为一个chunk，此边界明确保留；不宣称编码器对任意输入是常量内存。成功正常记录/省略项/入参均不修改，重复结果确定。

若必需信息仍超cap、存在非JSON值/NaN/循环/非法Unicode或元数据命名冲突，返回`status=OBSERVATION_INCOMPLETE`，另保存`source_status`，`encoding_error`只给code/type，不repr任意对象或泄露异常body。`integrity_checkpoints`先保最终unchanged布尔，再尽量完整保存source/runtime/DB/original前后值和校验、所需索引/摘录。无法全留字段明确列`unretained_fields`；最小cap连字段清单也放不下时明确枚举不完整并留identity，绝不静默截断必需摘录/伪称完整。原不可hash记录明确full_record.available=False。ROOT应按saved OBSERVATION_INCOMPLETE退出，不能按source_status放行。

## TDD及有界结果

12类、18项纯合成控制：小记录确定性/无mutation与canonical身份；大量重复raw；巨trace及状态；真实UTF-8字节；mandatory巨量fallback；FAILED保留；非JSON且repr禁止；NaN/Inf；循环；非法Unicode key；既有hash不覆盖；非法cap前置拒绝。

- `receipt-red.*`：16F，0.88s，真实功能RED（新API stub），非collection错误。
- `receipt-green.*`：16P，0.51s。
- `receipt-final.*`：18P，1.07s，额外Unicode/hash反控。
- Ruff两新文件通过；mypy工具文件通过。18P后仅加list类型注解，Ruff/mypy再次通过，未重复全量检查。

证据在`.planning/architecture-quality-20261101/real-acceptance/receipt-{red,green,final}.log/xml`，各hash、精确JUnit时间见同名JSON报告。所有数据内存合成，没有新原始文件或需要恢复的测试资料目录；仅保少量有意收据日志，无下载/收费/模型调用。

## 冻结与交接

- `tools/source_case_receipt.py` SHA256 `c260f64dd530315517a44aa940ffe73290f2e6d331981c56260ae0d98d50315a`
- `tests/unit/test_source_case_receipt.py` SHA256 `c9b4f81eca3618d9d3b2160c72b51fb0c7288c69305f8eb2b7c9a27945cd81f8`

源码现STOP。ROOT后续独审两文件及ignored runner集成，完整真实验收不能由本纯合成节点代签。
