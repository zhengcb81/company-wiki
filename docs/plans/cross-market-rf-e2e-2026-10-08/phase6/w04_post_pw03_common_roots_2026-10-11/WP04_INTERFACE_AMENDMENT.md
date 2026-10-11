# ROOT WP04 serializer seam amendment

2026-10-11；封存WP04卡与ROOT_EXECUTION_OVERLAY原SHA不改。WP04提交24FAIL/2PASS真实RED，纯serializer责任层需要显式接口，ROOT增加排他写权：FF隔离tree `scripts/ff_v2_envelope.py`，限 `error_envelope` optional keyword与必要closed-validator import，原SHA `c83b92dddba7cad223f64bc1aa573e88312a0676a85e073e05c43f1b9fae9ed3`。其余函数和跨仓源码仍只读。

`request_diagnostic=None` 默认保持旧输出；只在验证typed schema/reason/field_path后由所属filing child serializer附安全copy。`fetch_filing`仅传异常typed属性，不事后patch envelope、不反向解析任意错误string。six-key upstream cause、旧code/status/usageunknown保持；未知reason/path拒绝，不导出request body或secret。额外两类没有sealed真实失败时明确为真实请求派生反例。

WP04自己记录该确定seam前/后SHA、RED/GREEN/diff和接口交接；ROOT不同时编辑FF。正常发布仍由ROOT集中，大节点一次FF→RF/audit联调，无每小步人工许可。
