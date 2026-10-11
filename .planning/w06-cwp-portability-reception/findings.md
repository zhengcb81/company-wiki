# ROOT W06-CWP-PORTABILITY 当前发现

已关闭两组工具共因：初始化/清理只处理本次创建物；保留CLI原始结果，直接实读完整输入SourceRef，typed判定覆盖必需场景。后来独审发现“检测到expectation_unmet却汇总PASS”；现用显式Finding outcome、默认FAIL、None诊断和单调severity聚合，判定不依赖code前缀。

最终69PASS/1SKIP；七场景实际Reader/CLI成功；非作者53案0意外，原4反例输入SHA一致。11产品、8producer、旧FAIL及scratch均保持。仅Windows合成接口验收，不能认证POSIX、真实云、OCR、LLM或投资研究质量。

原FAILED报告完整保留于 intake/、independent-final/；其pending只代表当时状态。当前依据 independent-verdict-final/ 和 local-main-integration.json。正常commit前的额外diff-check曾因原pytest日志尾空格退出；原日志未改，正常仓库hooks通过。

发布完成：main/origin/master6dd7a119；精确CI38145427297 success，正常push3305PASS212.82s。干净ROOT checkout正常移除，branch/worker/历史FAIL保留；详细事实见 publication.json。
