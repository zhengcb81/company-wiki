# W06-CWP-PORTABILITY outcome汇总第二轮交接

READY_FOR_INDEPENDENT_REVIEW，未commit/并线/安装/push。原独审
FAIL_NEW_ORACLE_EXPECTATION_CLASSIFICATION和首次冻结证据原样保存。

## 根因与统一修复

检测阶段产生expectation_unmet后，旧汇总只凭false_pass前缀或两个白名单code升级FAIL，
丢掉了明确的硬契约失败。Finding现有显式outcome：强制检查默认FAIL，None仅诊断；
一处单调汇总将finding投射到对应场景，再汇总总状态：
INVALID_RECORD > FAIL > PARTIAL > UNKNOWN > PASS。
未知outcome返回结构化INVALID，不静默降级。不会按公司、四个字段或错误名称特判。
现有cleanup未完成但没丢字节仍显式PARTIAL；准确UNKNOWN/PARTIAL保持，普通ID关系/
policy变化/blocked socket/测试warning/SKIP仍诊断，不增加许可门。
run输出finding含outcome，便于审查真实分类。

## TDD与最终节点

- 正式8 FAIL + 3合法正控，0.56s：原4硬条件、S3旧ref分类、S4synthetic-only、
  S5恢复实读及新无特殊code前缀的硬contract。正控为真实诊断/UNKNOWN/cleanup PARTIAL。
- 另测显式None诊断（即使code含false_pass）、UNKNOWN→PARTIAL→FAIL单调优先级，
  输入status map不改写。旧断言保留。
- 本轮唯一最终节点69 PASS / 1 host-symlink SKIP / 1 disabled-asyncio-plugin warning，
  9.07s，ruff PASS；真实7场景Reader/CLI PASS 4.051s。现有文件/空目录与原8producer
  SHA不变，测试临时根absent。实际调用/外发/费用0；blocked socket观测保持可见。
- 作者额外重放独审原4 FAIL：逐一JSON patch，规范化输入SHA与独审四个原SHA完全一致，
  当前对应S2状态和overall均FAIL；未覆盖独审原始FAIL，不作自己独立签收。

## 冻结写集与接口

原11产品范围内仅3文件变化：oracle.py、run.py、本卡unit测试。
另更新本卡PWF/handoff。没有其他工具文件、producer/src/config/旧生产测试/CI变更。
fix/verdict-aggregation/final-node.json、real-run-report.json、
original-fail-replay.json、product-freeze.json、manifest.json为最新接口。
旧fix/product-freeze.json和fix/final-refresh是历史，不能再用其SHA校验本轮3文件。
同源作者STOP；ROOT安排非作者仅重放原FAIL/合法controls，然后正常commit并线。

范围仍仅Windows synthetic Reader/catalog/CLI/工具层，4doc_key共3逻辑ref；
S4证明备用physical。未扩大到真实云、Dayu/Dropbox、OCR、LLM、投资质量或POSIX。
