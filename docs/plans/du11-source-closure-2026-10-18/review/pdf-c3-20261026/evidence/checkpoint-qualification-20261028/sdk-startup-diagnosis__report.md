# 单次SDK冷启动只读诊断

本轮无文档cold进程在首个 `docling.document_converter` 导入中达到30秒deadline。8/16/24秒三次独立定时栈都停留在Transformers导入的全局distribution元数据扫描，尚未到Options、DocumentConverter构造或页面转换。这是本地导入工作的实测证据；**不等于已证明生产120秒整段超时的唯一根因**。

ROOT已核真实v4 `phaseC-090-9f3f43873512` 的selection观察：ChildTimeout、last_stage IMPORT、120.0252秒、completed=[]、requested=[12,13,17]，0 POST/0费用。生产worker只有IMPORT和CONVERTER_READY两个外层标记，前者包含四条SDK import、Options及converter构造。本报告将此前不透明的范围缩小到一次无文档探针的首条import，并非将该生产运行重跑。

## 精确运行和观测

唯一命令：`C:/Miniconda/python.exe -B -X utf8 .planning/c3-20261028/sdk-startup-diagnosis/run_probe.py`。controller包含已消费的single-attempt marker，禁止重复执行。`cold_probe.py`是实际子脚本，SHA、实际白名单环境和原始stdout/stderr SHA见 `probe.json`；完整结构化报告见 `report.json`。

沿用runtime-4g-v2.json的Conda3.13.9、Docling2.96.0、既有模型目录和配置SHA；6个运行版本与配置相符。Transformers版本5.18.0。与生产相同offline/CPU flags、CPU4、4GiB Windows Job，既有bounded_process总树ownership，30秒deadline；未给PDF或转换请求。原全局缓存和配置没有修改。模型config.json实际SHA与配置一致，171,658,996bytes权重只stat未再次全读，model/environment SHA引用原部署绑定，没有声称本轮重算完整环境hash。

| 时刻 | 阶段 | 进程CPU累计 | Job峰值commit | 进程other I/O操作累计 |
|---|---|---:|---:|---:|
| 0.002秒 | BEGIN IMPORT_DOCUMENT_CONVERTER | 0.109秒 | 9.69MiB | 3,905 |
| 8.027秒 | 仍在首import | 5.609秒 | 181.49MiB | 126,634 |
| 16.045秒 | 仍在首import | 11.766秒 | 183.50MiB | 202,375 |
| 24.072秒 | 仍在首import | 18.875秒 | 194.52MiB | 280,632 |
| 28.087秒 | 仍在首import | 22.047秒 | 201.36MiB | 317,573 |

父层30.018203秒结束并回收全树，状态ChildTimeout。没有END import或后续阶段事件。3次faulthandler主线程栈为同一链：

`document_converter:21 → asciidoc_backend:20 → base_models:38 → pipeline_options:17 → asr_model_specs:9 → pipeline_options_asr_model:8 → pipeline_options_vlm_model:9 → Transformers → transformers/utils/import_utils.py:51 → importlib.metadata.packages_distributions:1045-1046`。

三个快照分别展示metadata读取、top_level.txt读取和 `_top_level_inferred → Distribution.files → skip_missing_files → Path.exists/stat`。源码绑定证明Transformers在模块顶层执行 `PACKAGE_DISTRIBUTION_MAPPING = importlib.metadata.packages_distributions()`；Python3.13的该函数枚举所有可见distribution，缺top_level.txt时通过RECORD推断，并在files属性对路径逐个exists检查。这些调用发生在离线SDK导入阶段，先于模型或PDF处理。

只读stat库存显示单个Conda site-packages下426个带RECORD的dist-info目录，其中179个没有top_level.txt，RECORD合计9,304,802bytes；最大无声明项mkdocs_material的RECORD约1.61MB。这里仅记录潜在扫描规模，**未证明当时停在某个特定distribution，也未把这些目录计数冒充完整sys.path分布数**。没有第二次运行packages_distributions来计时。

## 可以据此判断与不能外推的部分

首import会跨入ASR/VLM/Transformers，再扫描广泛本地distribution；因此“只有PDF、离线、无OCR”并不保证SDK导入仅访问PDF相关模块。28秒时CPU与metadata操作仍持续增长，且观测峰值远低于4GiB；本次证据支持导入元数据枚举的活动耗时，不支持网络等待、配额、模型权重加载或PDF内容导致当前30秒失败。没有提升120秒或内存上限的依据。

生产120秒时没有该定时栈，不能证明其120秒内一直停在此函数、不能排除后续torch/native导入或构造另有耗时，也不能把本次约30秒当作未插桩的准确耗时。审计钩子对open路径解析及4秒采样会增加开销；child环境只继承安全定位变量并显式设置相同offline/CPU变量，其余父进程环境未复制。探针的目的为定位调用链，不是性能基准。没有到达Options和converter构造，故其耗时仍未知。

此次未实施产品修复。后续若要处理该瓶颈，责任层应先检查配置的SDK部署/依赖闭包如何避免不相关distribution枚举成本，并先设计中性可验证边界；不能通过猴子补丁全局metadata、隐藏依赖、长驻无界worker、提高预算或换provider宣称解决。ROOT的原生几何同段闭合调查可独立继续，本证据不替其做语义结论。

## 只读与回收

Python审计钩子拒绝网络和自有TEMP以外写入，实际GUARD_REJECTED事件为0；没有PDF/秘密配置输入、收费调用、下载、持久cache或配置写入。该钩子是Python事件保护，不能声称完成了所有native DLL文件/网络系统调用审计；Windows进程I/O计数也包含stdout/stderr管道，不能全部视作磁盘读写。

观测child PID22120结束后alive=false，既有bounded_process回收所属树，独占 `.c3sdk28` 已恢复不存在。四个已独审PDF文件逐一核验LF SHA全部不变。仅本诊断目录写入计划、脚本、日志与报告；没有tracked产品或ROOT PWF/index写入。
