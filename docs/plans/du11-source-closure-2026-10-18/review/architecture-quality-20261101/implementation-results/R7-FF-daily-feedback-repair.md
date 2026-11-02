# FF 日常反馈与配置旧期待收口

已冻结，等待ROOT独立审查。只改5个工程/测试文件：hook、pre_push_gate、共享ci_tests、原调度测试和原配置质量测试；**18个FF生产script源码（包含此前已审FF文件的生产实现）和4RF assurance WIP均不变**。

## 根因与设计

旧正常pre-push实际用了 `--ci-tests`，在已经做过commit静态检查后，又重复mypy/compile/host扫描/三仓doctor/plan/BOM/安装drift，再跑CI40文件：这次真实push116.55s、933P2旧配置oracleF。它不是小smoke。

现在hook只 `--push-checks`：**一次Ruff＋一次固定11个已有纯unit节点**。不读生产/sibling配置，不运行完整CI、不做安装/部署/全树clean。共享runner提供同一Git上下文清理、UTF8、独占临时目录、完整失败输出、真实退出码和subprocess超时。失败phase不会继续另一个phase，timeout仍非零/清理，未知错误不会打印成GREEN。仅为 `local_fast_pass`，不冒完整CI通过。

CI_TESTS原40表与当前Git HEAD AST逐项完全一致，完整CI保原900s、生产runtime依赖检查和所有原检查；显式 `--ci-tests`/`--run-tests`也保原完整模式。日常180s是实际子进程deadline，不是表示cap或人审许可；`--push-checks`是执行模式，不是授权flag。

## 两项旧配置oracle

不改已经正确的FF配置reader。原“合法config大于64KiB要拒绝”改为完整读取并解析到正确root、原字节不变，再在旧边界后放坏UTF8仍须config_error；原“read必须指定65537以内参数”改为有效JSON主体放在70,000空格之后，必须完整读才能成功。删除实现镜像参数要求，保真实UTF8/物理root错误反控，没有删除用例或截断config。

## 实测

- 新调度tests-first＋旧2oracle：**8RED /0.86s**，原始JUnit/log保留。
- 修后共享工程域＋2配置迁移＋UTF8/root反控：**22P /2.11s**，包含真实合成pytest失败节点/退出码、timeout清理、Git上下文和不调用doctor/install/fullCI控制。
- 4个改动Python文件Ruff通过；新增测试最初2处E701/E702格式问题已修，未改产品行为掩错误。
- 真实 `tools/pre_push_gate.py --push-checks`：**11P/0.29s，总1.0187098s，exit0**，一次Ruff＋一次smoke，无隐藏其它阶段。不同机器耗时会变；没有把1秒当承诺或新门禁。

本作者未重新跑CI40/全仓、没commit/push、没更新主PWF，没调用真实模型/下载/原件或全局技能部署。ROOT须独审后正常提交推送、查看精确CI。全部5SHA、CI40原表、原始log/XML和保护数据SHA在同名JSON。自有临时目录恢复absent，原生临时pytest目录也由测试核恢复；不靠全仓干净签收。
