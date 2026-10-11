# W08 来源 URL 控制字符补充：独立定点验收 PASS

2026-10-11。本结论对应 frozen import `604d62cefd2ceb8b566dae08cac9e1ad86e8ea285e88da84ff845b4bf93cf027`、writer `26d9c475442f5438b19b8ad6a1c8578d0f14cfd13660b5955fd04c75a798e70f` 和 test `3b1ff1c8dee0d4e48b1012d0fd468ff17191afa24d4119c740be437bcd71b6be`。原 REVIEW/receipt/minimal-probe 不覆盖。

完整读CONTROL_CHAR_SUPPLEMENT.md，SHA `2e2ec9567da36eca03a8034113181e3d2de2abda07987c18ef6f5bda4752ca1d` 与实际一致；核对新三份原生日志 SHA。真实 RED 为DEL/C1两失败、一条已被旧whitespace排除的C1正控通过，**2 FAIL/1 PASS/0.54s → 3 PASS/0.39s GREEN**，Ruff绿。没有重复58/public9秒/whole suite。

现 helper 以Unicode general category `Cc`识别C0/DEL/C1等原始控制字符，继续配合whitespace判定，返回None。writer nullable接口、原始capture、source bytes、publicexport/recovery和旧immutable行为没有再改，也没有新HTTP检查、permission、schema、consumer或手工签收。

本轮仅重新运行原始DEL反例：`https://official.example/qa\x7f` 期望None、实际None、**PASS**。完全内存helper、0TEMP、0网络/模型/费用；未扩更多URL边界样本。该通用数据分类修复解决原精确遗漏，先前已接受的主链职责继续成立。接受的是W08producer provenance此节点，不是86真实页面入库/经济研究/三家公司四审或整个PWF完成。

receipt记录本轮3精确源/test前后SHA均相同，并确认原独立review3文件与owner历史HANDOFF/RED/GREEN/定点GREEN原字节SHA保持。并行scope盘点和pure写集不纳入保护。本轮只在自有证据目录新增FOLLOWUP/receipt/native log；源码、测试、配置、原件、Git、安装零写。冻结交ROOT正常发布。
