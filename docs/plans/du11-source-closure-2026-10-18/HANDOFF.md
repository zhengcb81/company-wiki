# 当前交接 — 先补齐D4解耦遗漏

PLAN_ID=du11-source-closure-2026-10-18；唯一状态[CURRENT_STATUS](CURRENT_STATUS.md)，原目标[MAINLINE_LOOP_GOAL](MAINLINE_LOOP_GOAL.md)保持。

1. 先读[2026-11-02复核与D4实施细则](review/decoupling-recheck-20261102/README.md)及三份独立报告。六项OPEN，本轮只审计/改PWF，未修产品。五张互斥写域的实现卡已备妥，尚未派发，见[D4_PACKAGES](review/decoupling-recheck-20261102/harness_lanes/D4_PACKAGES.md)；不要依据旧D3报告启动RF/AUDIT业务计划。
2. D3实际公开端口、原文预算、39项组合/安装验证与[发布记录](review/decoupling-20261102/release.md)保留；只重验D4新增影响，不能把选择集通过当全仓独立。
3. 五张包各按原卡先写反例；Stock CWP接口+StockWiki同卡负责，RF/CWP解析层/CWP wire/FF stderr分别独占写域。ROOT 不外包最后一哩测试：读 [ROOT-D4-final-integration](review/decoupling-recheck-20261102/harness_lanes/ROOT-D4-final-integration.md)，收齐交付后归位 AUDIT 并做一次组合。
4. RF/AUDIT仓内业务PWF均为DEFERRED_UNTIL_D4_CLOSURE，未派发。D4关闭后恢复T4/SEM与真实摘要/cache/RF采用；固定公司loop未完成。
5. 保原件/旧R4/生产配置/库和RF四assurance WIP、CWP hook模式WIP。旧RF日检仍可能追加诊断，当前计算/发布不依赖它；不要把旧not-ok当当前结果或声称任务已退休。

正常宿主C:/Miniconda/python.exe -B -X utf8；若用现有PowerShell PWF resolver，它需要清除不兼容的相对PWF_PLAN_ROOT并传-PlanRoot绝对docs/plans和PLAN_ID，解析出的当前目录必须与本页一致，不能落回旧根计划。此为工具调用参数差异，不改全局技能。

StockWiki/AUDIT无remote，如实本地交付；Dayu/IQS/Dashboard不动。定点部署保配置/output，不新增逐材料许可。
