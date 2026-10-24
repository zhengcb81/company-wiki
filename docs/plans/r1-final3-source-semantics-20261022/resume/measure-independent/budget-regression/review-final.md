# Fanout预算修复：最终独立复审

结论：**PASS_BOUNDED_BUDGET_FIX**。本节点已复现的资源预检回归修复通过；不代表整份来源或全产品质量通过。

- 当前 narrative_reading.py SHA：`a70436b70fa66c0934b4dfb794ead63564d78e0aae89f69efe91a291c0a72780`。
- 原未改测试 `[0,1,1000]`：**3P / 0F，实际exit0**，stdout/JUnit保留。
- 独立观察：0/1档body/context均0次；1000档body32/context64，used708、exhaustedtrue，原始units各次未变。
- 默认足额新旧完整候选输出snapshot相同：96 candidates、32 eligible、complete、0 withheld。
- 显式足额新旧输出snapshot也相同，总work均43882；所有原始units未变。

对照使用内存中的精确旧函数：把现行完全相同charge块在内存反移后，整模块字节SHA精确重建为已诊断旧值 `5bb37ff8672fc2c54bc805310c252187043cd24f5660666bfe5e356a052726ce`，再仅编译旧 `_prose_reading_packages` 函数到隔离namespace。未写生产回滚或源码副本。这个精确哈希检查证明本次源码差别仅为该块时序移动。

修复使超额fanout在typed-table第二次body扫描前拒绝，保留原≤一次输入扫描断言、所有预算额度、足额路径语义与总扣款。所有独立检查通过，源码观察前后SHA一致。

证据：`probe-final.json/stdout`、`original-final.xml/stdout`。旧RED、charge-order及首轮报告继续保留。Ruff/mypy、ROOT formal239及更广typed-table/suite属于ROOT native gate独立证据，本复审未把它们计作自己运行。

既有pytest basetemp插件对本次与原RED创建的自身临时目录均返回removed=true；自有请求tmp与pycache不存在，见cleanup-final.json。无产品/tests/外部harness/原件/Git写入、无原件读取或外部调用。
