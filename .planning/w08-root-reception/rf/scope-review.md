# W08-RF-COMBOS ROOT 范围复核（只读，2026-10-12）

实际作者HEAD：4d5c9f05835c46cc445288f2883c6bf215c39348；尚未合并/安装，不改作者树或RF canonical WIP。

## 两项明确未闭环

1. C02：combinations.py 的 CaseSpec 声明 fiscal year 09-30、Q1=36/Q2=36，但原生输入只送年度驱动36/90，期待年度91/150.5；没有把dated acquisition/control窗口实际交给dated-composition。手排日期标签或引擎检查年结不是计算跨FY贡献的证据。两季各36的文字还与年度使用36不一致。不能把C02标CLOSED。ROOT须先选择已发布的真正dated-contribution接口，用固定日期/控制比例/窗口的独立手算输入和反例检验年度、季度及去重祖先；不直接改core或把expected换成actual。

2. C05：native.py 将 native_entry 记作 revenue_backtest.evaluate_snapshot，但实际调用 bootstrap 内新写的 evaluate_draft_scope。bootstrap.py 的 _error_record 把同一个 base_path[year] 同时当 forecast 和 actual，必然零误差；实际观测矩阵未入参。虽然复用了原生误差算术，这仍不等于真实actual/WAPE原生流程；报告入口名和“实际结果”不诚实，不能标CLOSED。ROOT须使用真实已发布快照/评估接口（在独立目录创建最低充分快照）或已存在原生draft评估入口，actual用独立常量，至少一项非零误差、部分缺失/全空null、按segment/year/scenario不能外推。若公共入口客观不支持则如实OPEN/PARTIAL，不能冒写原生entry或自造actual。

## 主线安排

先完成CWP当前正常push/精确CI；随后RF集中A/B/C接收节点优先修以上工具范围共因，实际验证另外三组和旧16向量/36断言后再整体并线。Audit包接收保持排他。不得新增人工签收/许可文件，元数据空commit字段由实际Git补，6SKIP按真实理由分类。

这是工程观测/覆盖问题，不据此宣称RF生产引擎已发现相同数学错误；需要真实原生复现来判定。
