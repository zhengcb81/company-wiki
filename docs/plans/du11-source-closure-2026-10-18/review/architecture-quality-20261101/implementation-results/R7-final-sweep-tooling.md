# R7 工具/工程入口最终遗漏扫查

已完成只读复核。**发现1个当前有效P2，另3个低优先级简化候选。** 未发现逐材料授权、人审签收、private/public、全仓dirty许可或隐式全局部署重新进入正常工具路径。已完成R7不重复报问题。

## 需要直接根修：付费成功后的观察器仍有128KiB否决

`tools/document_understanding_benchmark/phase_c_runner.py` 的 `successful_model_observation`916/960/966行仍用兼容常量 `MODEL_RESPONSE_MAX_BYTES=128KiB` 读取gzip已保存结果，超限或因只读前缀导致hash不同，抛 `PHASE_C_CAPTURE_IDENTITY_DIFFERS`。

实际链：显式phase_c_runner.main → run_pair → _run_pair_in_owned_root；native batch已code0、付费/usage持久化后，1531行调用该观察器。异常被1692行统一捕获，整对实验变FAIL，后续public bundle/缓存/consumer验收被跳过。并无证据说当前自动重发，但这个假失败会诱导重跑。合法配置/已持久结果不该被历史表示阈值重新否决。

ROOT已接受本项：下一步在同一owner流式完整解压/hash/count/UTF8检查，不只提高阈值；真实SHA/event、解压/I/O/编码错误诚实记录，独立区分observer incomplete与native成功，不伪成功或付费重发。用>128KiB合成结果和真实失败控制TDD，保实际deadline/传输资源预算。

## 低优先候选，不冒充主流程阻断

|项目|实际状态|建议|
|---|---|---|
|final_material默认4MiB文本、512行/组、4096unit，调用方只可降低|公开库导出，当前tools/scripts未找到内建CLI/生产caller；不是source/PhaseC活跃入口|若保留为受支持observer，删除默认表示限制、保真实work；否则明确退役，不能静默缩分母|
|CI重复Unit targets|全Unit后同一fast inventory再执行13个显式Unit节点（35targets的一部分）；不能把节点数冒参数展开case数。显式full local模式也有重叠|CI专用入口减掉已覆盖Unit，日常push仍保固定smoke；不增加job/新门禁|
|PDF cold probe固定rev5且既有marker拒绝任何重跑|只在显式历史W21诊断工具，无自动业务/部署caller|若维护成通用工具，用fresh attempt目录与基线诊断；保内存/线程/真实deadline、防覆盖；否则标历史退役|

## 保留的检查及原因

- commit仅静态检查、push固定smoke一次（docs0）、完整模式显式、CI全Unit。实际lint/type/test/配置错误仍非零；已确认没有安装/同步/部署的隐式调用。JUnit/console只压缩展示，保存结果不按大小失败。
- legacy writer与6工程shell是永久退役/来源层职责边界，不是可签收恢复的材料权限。当前有限批次和package CLI不依赖它们的许可。
- holdout的exact `--producer-commit` 是当前显式请求版本；冻结gold基线不锁修复后引擎，dirty只诊断，不要求全树clean。
- identity audit16MiB约束请求输入；RAW-DUP字节预算约束真实读；OCR内存/线程/时间与批次配置额度约束实际工作。它们不同于report/log体积否决。不能全局删除实际资源边界。
- optional semantic review缺失保NOT_EVALUATED而不是阻断资料处理；显式提交坏review不伪装已经审查。来源/gold分母一致检查保真实比较。
- secret_audit代码中历史重写的authorization标签仅为可选审计结果，无自动rewrite/业务许可，generate照常返回。破坏性远端Git历史操作仍是独立动作。本次没有读取.env或密钥值。
- consumer-spy保留最多200条open样本但所有raw_non_reader计数仍累计，不会因为日志大阻断；可以后补sample_limited标记，不新增gate。
- 原文字节/身份/期间/asof由单owner校验，实际I/O/JSON失败不能伪保存；不覆盖无关文件属资料保护，不是签收许可。

## 证据和范围

同名JSON绑定39个当前工具/入口/相邻常量源SHA、真实caller与行号。使用CodeGraph结构查询加已打开具体文件的调用分支；没有初始化索引、跑测试/原件/模型/网络、读取密钥或历史运行材料，没有改源码/测试/他人WIP/Git/主PWF。报告之后ROOT已要求本作者只实施P2窄根修，低优先项仍仅报告。
