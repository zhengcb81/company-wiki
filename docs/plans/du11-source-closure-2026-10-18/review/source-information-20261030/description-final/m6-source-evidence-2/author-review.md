# M6 Confidence共同计票根因修复 — 作者交接

状态：实现完成，等待ROOT安排独立审查；未提交/推送/安装。仅4个Python文件，SHA见同名JSON。

同一个来源的重复引文原来同时改变freshness与混合role quality的权重。source-evidence/2现在按每used parameter分别计票：freshness是distinct origin，quality是distinct(origin,support_type)。origin使用既有validated capture.snapshot_sha256，旧资料缺capture时回退source_id。原claims/独立测量/角色不删，也没有新身份库或许可门。

同SHA别名同role不加票；真正新capture或新role仍有作用。日期冲突取最早known publication并披露，全未知origin给0freshness信用，availability只证明可得性不冒充publication。真实M1完整trace/2.2 availability、pub=None先通过source合同，进入native confidence不再崩溃。

新输出默认source-evidence/2，历史stable-fsum/1保持原来逐claim算法。强复算先读observed revision再选同owner算法；无marker才使用原64ULP兼容，两个有marker版本都严格exact。null/unknown/list/dict明确拒绝。engine4.3.0与schema未改，旧输出/签收hash不重写。

TDD原17F/6P留存；最终117P/6.38s，4文件ruff通过，confidence单文件mypy通过。revenue_report整文件12个既有mypy错误已和HEAD提取基线逐项对照一致，没有扩大本次修改。测试含同源/alias/独立角色、新资料、日期未知与冲突、旧版本strong native receipt重放、各版本tamper和64ULP边界。两次早期GREEN的失败是新测试先改published payload或只改component总数，随后让历史算法在native receipt之前生成并同时改score做真正复算负例；未放宽产品断言。

真实复算只读RF v3保存input/output，不读原件，不调用模型。旧baseline/consumed confidence逐字段复现65.38058062293638与65.39469303281442；新两份native draft/strong validation均通过并完全一致65.38058062293638，freshness8.679411732699949。参数trace、经济路径、敏感度不变。新draft只存RF自有m6，不发布、不写registry；不能表述成新的实际RF采用。最初replay因检查不存在的parameters键失败，原log保留，改为真实parameter_trace后成功。

RF证据：.planning/source-quote-adoption-20261030/m6/{real-replay.json,baseline-source-evidence-2-native-draft.json,consumed-source-evidence-2-native-draft.json}。三份原有WIP SHA未变，output未写。CWP这里只保留技术报告/测试日志，不持有正式公司分析输出。下一步由ROOT独立复验上述4文件和证据后收口。
