# DU9：三条排他施工线

状态：READY；实际工区/分支/干净状态/当前imports及相对hooks均已核对。必须独立agent全面审查、全部发现修复并复核PASS，才能交接。

|卡|工作目录|施工卡|
|---|---|---|
|DU9-CWP-GEOMETRY-POLICY|C:/Users/郑曾波/Projects/company-wiki-du9-geometry-policy|[策略](du9_cwp_geometry_policy.md)|
|DU9-CWP-GEOMETRY-PLANNER|C:/Users/郑曾波/Projects/company-wiki-du9-geometry-planner|[调度](du9_cwp_geometry_planner.md)|
|DU9-ET-LEGACY-COMPARISON|C:/Users/郑曾波/Projects/earnings-transcripts-du9-legacy-comparison|[兼容比较](du9_et_legacy_comparison.md)|

三条可以同时开工。前两条同CWP但只写不同子包/目录，固定接口和自有fixture使作者彼此不等待；ROOT独占生产port/章节匹配装配。第三条只写ET parser兼容比较，ROOT暂不再写ET这部分。现DU8 RF/FF/AUDIT三工区不变，所有作者不进入兄弟目录。

[统一接口、独立审查与交接格式](INTERFACES.md)。每工区自带施工卡、INTERFACES、task_plan/findings/progress；ROOT统一接收、生产真实E2E、并线/推送。所有工区共享Git历史而非复制资料湖；实际基线/seed/大小/启动检查见launch.json。无需等ROOT当前工程发布即可按各自已提交基线实施。
