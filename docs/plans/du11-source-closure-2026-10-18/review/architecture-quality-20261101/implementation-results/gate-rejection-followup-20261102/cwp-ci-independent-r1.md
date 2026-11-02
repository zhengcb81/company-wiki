# CWP CI迁移独立审查R1

**NEEDS_ROOT_FIX：CWP-TEST-P2-CURRENT-INPUT-HASH。** 原CI7失败与作者各次运行不倒签、不重77。

唯一archive helper只要求当前input_sha256不等于旧值。独立纯公开helper反例：prompt/instruction/data保持真实当前值，只将current hash改成f×64仍被接受。允许quota变化导致hash改变，不等于允许当前绑定任意值；这是测试迁移削弱，不是已证产品请求错误。

修复需使用真实request owner与selected/version重建完整身份：raw还包含citation/group/selection/subject等，scoped还含source_view，不能只重算三个显示字段，也不复制hasher/patch decoder。已将精确probe与责任路径交作者；修复冻结后只做必要增量。

其余已读：升级只移明确20或2/6、280字段与精确旧指令/advisory；非quota字段保全文比较。所有旧64hex常量保留，四生产owner和atomic fixture与作者原SHA相同；二进制gzip与HEAD逐字节一致，文本JSON仅有checkout换行表示区别。没有重写原gzip/paid capture或修改产品算法。

补充归档核验：gzip与HEAD二进制完全相同；文本JSON可能仅checkout CRLF表示差异，非内容改写，atomic还绑定作者精确raw before/after SHA。初次把文本HEAD LF当working-tree字节做断言未过，已明确区分，不修改换行或归档。

完整反例、原5路径manifest、真实hash字段责任、归档/旧常量证据见同名JSON。0付费/原件/网络，不改作者源码、测试、历史、Git/PWF。自有tmp/cq7留证待R2增量后清理，未宣称现在目录已恢复。
