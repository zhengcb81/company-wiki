# 定点安装器 ROOT审查

通过本窄幅工程范围。原canonical安装器新增--file，保留显式full/check兼容，不在Git hook隐式部署。ROOT独立读实现与13项实际TDD反控后发现canonical alias可能将snapshot旧bytes写回已更新源；作者新1RED证实，增加same path/file保护后相邻3P/0.36s。当前605beabf/77281bd8两文件与报告绑定，ROOT复读确认先sameSHA零写，再拒canonical变更，无stage、不改源或链接。不重新跑13组或创第二安装器。

仅接受工程与合成测试范围；真实全局部署待ROOT按显式文件子集执行、前后配置/目标SHA/重复零写核对。原文、其他组件config/output不可覆盖。没有新的权限分类、手工签收、任意字节门或目录clean要求。
