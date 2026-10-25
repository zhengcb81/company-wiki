# PDF-C1：单一阅读边界实施与验收

2026-10-25。状态：**产品与源码独审通过；发布/精确CI收尾中**。本页只签C1，不关闭C2结构增强或C3正式摘要、缓存恢复、RF与holdout。

## 已实施

- 新`source_catalog/narrative_pdf_reading.py`作为PDF读取实现的唯一owner：成套recipe/read/select/material验证/replay，旧全表重读兼容策略下移。现代替身与原生实现收到同一WorkBudget、业务context与绝对deadline，不再按函数对象身份分支。
- AUTO composition向select、verify交同一owner；格式、generation、worker、重放经统一端口，不由上层挑SDK/options或解释坐标。旧callback参数仅兼容既有native测试端口，不代表可以独立注入不同producer冒充同一实现。
- PDF generation接受阅读层的opaque配方，包括实际PyMuPDF发行版本和owner源码SHA；禁用Docling的native配方不读取其已安装版本。配方在执行前冻结，不能执行后倒写。当前只启用native，Docling仍是C2待接线方案。
- 非PDF不提前加载可选PDF运行时；实际PDF缺依赖给具体原因。recipe不能泄露密钥/物理路径。单位必须与文档同源、同producer。旧已完成PDF的未知配方保持未知，只比较副本兼容；pending旧运行不能靠历史例外执行，原manifest不补签。
- 摘要继续使用现有共享阅读协议/数字引用检查和预算化模型端口；不新增客户端/数据库/常驻服务/逐材料审批。原件与W18/W19作者目录不改。

## TDD与独立审查

两项原始根因RED：替换parser丢预算/context；PDF generation忽略实际runtime配方。独审新增R1–R5（可选依赖污染、deadline、descriptor卫生、旧历史恢复、异源units）均修在原责任层，最终[独审](c1-independent-review.json)**0OPEN**，绑定最终源SHA。

- 最终产品定向包：153 passed /25.86秒，见`c1-final-runtime-receipt.json`。
- 历史恢复、source usability、版本恢复：104 passed /37.31秒，与153有重叠，不相加。
- 独立boundary包15 passed /2.69秒；独立历史7变体通过，源码运行前后SHA稳定。
- Ruff通过、mypy整个src376文件0错误、diff-check通过。正常提交/push仍运行既有hook，不绕过。
- 初期错误文件名导致0 collected，测试夹具先后漏canonical source ID/字符串输入/电话会起始头/metadata均保留原失败收据，纠正夹具后才算有效测试；不计作产品根因RED。

## 真实原件接缝回放

[最终收据](c1-real-owner-final-receipt.json)：金山云中报75页、中微IPO429页、北方华创年报233页原件完整native读取，只在冻结的5页构建明确partial分析视图。与同PyMuPDF1.26.7基线对照：25＋19＋15＝**59条选中证据逐dict完全一致，59/59原文重放通过**，保护的catalog/config/预算配置SHA未变；0付费、下载、原件副本。

此比较证明封装不改变既有证据；不代表两处缺组已经改善，更不是全429页selection验收。最终owner LF SHA：`35c1685105d3196fbc16c6a53300d97eaa77e6e663d883785b7b3b132ff5ad9d`。

第一次误用venv PyMuPDF1.28.2与Conda1.26.7基线比较，观察到structured metadata/span hashes不同；未删除这些字段凑相等。改回同版本严格比较通过，也说明绑定真实runtime有必要。

## 集成测试环境诊断

原两项隔离流程首轮1P/1F。失败表面是ACK10秒未到，实因深层TEMP生成的对象目标超过Windows旧式硬链接260字符，`os.link`抛FileNotFoundError，dispatcher正确返回retry_scheduled，没有ACK。独立直接短根调用原测试可通过；随后仓内48字符短根的沙箱运行仍1P/1F，诊断证实是沙箱禁止硬链接的WinError5；同一主机环境保留全部原断言/超时，最终**2 passed /5.83秒**，见[c1-integration-short-host-receipt.json](c1-integration-short-host-receipt.json)，临时根恢复不存在。沙箱失败收据`c1-integration-short-repo-receipt.json`不记绿。C:/tmp启动尝试无产物后取消，未复制原件或修改生产存储。

临时根由runner独占创建、核绝对parent后删除，并验证恢复不存在。此轮不改测试超时或生产storage。完整正式摘要/付费恢复仍由C3验收，mock的离线集成不能代签真实供应商质量。

## 下一步

正常提交推送与精确CI，随后实施[PDF-C2](implementation.md)：通用缺口分诊、严格native成员对齐、受界隔离热运行时。维持原生默认，不能把Docling字符直接覆盖canonical或将charspan冒充DICT坐标；A股历史三表由W19新浪API负责。
