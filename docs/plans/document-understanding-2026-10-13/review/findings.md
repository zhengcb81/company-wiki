# 深化复审发现

## 状态与证据边界

- 主线仍为 e802e8ac，原 DU 总计划记载“三线施工”；实际 profiles/structure/benchmark 都有 handoff，另有 root 整合分支 43e67e8e。交接与母计划有时间差，不能凭旧状态重复施工。
- root handoff 明确未接生产、未并 master、未安装；本次只读复审，不把离线整链接通当生产质量已验收。
- profiles 交接含 15 策略、7 真文档路由观察；benchmark 更新含 15 金标、176 事实。两者并不能证明每类策略已完成真实语义验收。
- 三个独立审查分别检查架构接线、策略组合与覆盖、基准的目标及有效性。新建议不修改旧 DU/1 或四个 worktree。

具体结论已写入 [report](report.md)、[覆盖矩阵](strategy_matrix.md)、[ROOT细则](root_implementation.md)；[evidence](evidence.json)记录三个ROOT复现及真实HTML独立探针。旧分数须在oracle/目标/格式入口修复后重算，不能当改进幅度。

## 施工卡独立试读

- 两数据卡补清了字面信号与说明文字、少量条件枚举、独立覆盖维度、真实locator或quote anchor、结构测试与未来语义执行的区别。避免交付不可执行DSL或自证测试。
- 布局卡补清表格父子/行列和表头脚注关系、正文分栏与表列区别、阅读顺序视图、细粒度输入前提。已有聚合行无法凭一个bbox恢复格子时返回needs_upstream，不要求模型猜测。
- 三包写入路径互斥；ROOT独占原benchmark修复/依赖闭包/策略接线。原DU/1没有变化，没有新增许可/签收或重复parser/oracle。
