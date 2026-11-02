# H1 v3：观察器记录失败，不能签来源验收

基线fa8ef38e已经T3独审和完整CI通过。真实H1仅运行一次，worker从execute返回至编码时，旧脚本发现记录大于300,000B后直接ValueError，写文件之前结束；目标h1-t3-r2-v3.json不存在。源选择/12unit/9context及原文/DB/runtime前后证明未持久化，不能声称本次通过，也不能把它当产品算法失败。精确耗时和旧ignored观察器SHA未捕获，均未知，不能事后补造。

根因是观察器复制完整调试/重复正文并在末端才检查记录上限，没有独立checkpoint。现canonical观察器迁到tools/source_case_runner.py与pure source_case_receipt/checks；历史命令变薄shim。300KB不提高：先校验编码器，RUN_START/来源打开前/RESULT_READY持久小checkpoint，atomic own writes，编码失败/溢出显式OBSERVATION_INCOMPLETE，parent超时保已提交结果与checkpoint。只保固定source引用与当前主体引介原始excerpt，不复制全部112段正文。observer/source版本前后绑定。

纯编码18项从16RED到绿；完整合成/新进程/原子写/错误恢复最终29P4.54s，自有tmp恢复初始absent；尚待独审，不再跑真实原件直到观察器可用。新一次真实H1只修复后单例，不跑整批，不提高16M/112/90s，不调用模型或下载。
