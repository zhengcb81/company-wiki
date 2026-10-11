# ROOT W06-FF-MATRIX 当前发现

真实联调41case为19PASS/21FAIL/1PARTIAL。九份三市场2024财报由真实CWP公共ensure入库，同期复用正确；缺2025/2026时供应商未启动，多数ET场景受primary失败前置影响，不能判为ET内部错误。

已独立确认CWP共因：resolver排除旧期后，local_reconcile把同实体同类型来源重新纳入；canonical已验入库事实没有steady correction assertion，缺patch被无条件当目标缺口，阻断新下载。需在所属来源层统一可信事实和相关性，保留目标字节/身份/期间/as-of及预算；不增加人工签收或许可。

工具最终独审另发现3反例：删22失败案例并同步自报集合、删cutoff expected、把CN请求改HK并重算请求SHA，均可假PASS。ROOT要求单一CaseSpec权威、完整请求和覆盖核对，不能只加3字段特判或仅数41条。旧报告、ZIP、freeze及输入SHA保持。

完整证据：intake/初始错误；fix/冻结34测试与真实矩阵；independent-final/权威缺口；root-cause-review/生产根因；新修复 fix/case-authority/ 与 producer-scope-fix/分别归属不同目录。
