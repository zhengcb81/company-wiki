# ST-A02 实际来源与消费路径调查（进行中）

2026-10-25读取封存的原公司初次执行输入`revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/execution/forecast/timed-final-input.json`，字节SHA为`dde8dce38b0c0b203eb4a0a9facaaa981debeea61559a9cab3e7be8285526150`。

该输入schema3.10、CNY million、base2025；`reported_total_2025`为45,456.16577418百万，定义明确包含持续与终止经营；历史2023/2024/2025收入均绑定同一官方原件source_id。`discontinued_base_2025`为2,035.342百万，引用原文p13万元口径，保留该页精度。不能据此推成已取得精确持续收入或可比期重述。

这改变下一步调查顺序：先核对已有完整原文摘录、公共来源读取与实际执行证据，再决定是否需要金融API或新的结构化表格能力。不能因为叙述切片的精确数字partial，就假定RF没有其他合格原文路径。旧FMP402记录仅针对历史电话会端点，不足以证明当前财务接口可用或不可用。

此时只证明旧输入里存在这些声明，尚未核验claim引句/输出绑定，更不证明当前新attempt已采用。annual14仍8通过/6部分/0缺失，当前正式摘要/RF验收仍OPEN。原文件只读，未新增模型/API/下载。

## 已完成的只读核实

`verify_source_route.py`已通过生产SourceVersionReader describe/open实读并验SHA，配置/目录库SHA前后不变，未初始化可写store。第7/13/183/184/235页原文及48条表行保存在最小收据；三条旧RF claim的来源SHA、引句SHA与逐页文字吻合，旧结果的canonical input hash与旧输入吻合。已核实的是reported_total_2025、discontinued_base_2025（保持万元原精度）与history_2024，不能由此声称全部口径或当前新attempt已经通过。

来源收据SHA `f2fab288e592843c291047825b7a2c722fb79cae597e8a62d58f6e040a1ef48a`；FMP本轮未调用。当前财务精确值可按需走已有完整原文路线，W16另负责口径通用代码；不能为补叙述金标重复建设财务全文切片。
