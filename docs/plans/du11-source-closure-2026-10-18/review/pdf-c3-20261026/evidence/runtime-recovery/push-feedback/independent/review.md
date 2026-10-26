# Push feedback 独立工程审查

当前结论：**产品实现未见缺陷；1 个 P2 测试可靠性问题待 ROOT 修复**。不将重跑成功掩盖首轮真实 RED。

## 待修 GATE-IR-01（P2）

新增 test_timeout_stops_the_owned_grandchild_before_return 固定2秒包含冷启动。本独审获批正常shell首轮真实失败：gate如期返回124，但孙进程尚未发布PID，record.exists为False，未进入PID已死断言。原字节单例复跑通过，表明它依赖宿主启动负载而不是稳定验证清理不变量。ROOT已认可接手。应原子发布完整PID，并留合理有界冷启动窗口（ROOT拟8秒，孙进程自停止12秒）；保留孙进程确已启动、返回后立即dead、总时间有界断言，不允许等待其12秒自行退出后才称清理成功。

首轮另一个失败来自本独审自建probe只等文件exists，撞到write_text打开后PID未写完的空文件窗口。已在自有probe改原子发布，最小复跑通过；不归为产品缺陷。

## 产品与范围复核

- 原29 FAST及CURRENT_CI inventory的AST与HEAD完全相同。unit整文件覆盖同文件FAST节点，其余FAST保留，node只去精确重；非unit不得把FAST扩成整文件。
- daily只扩展小量受影响unit，wide/unknown/nonunit明确defer；非空范围仍跑全部原FAST，可信空范围明确tests_not_run而不意外全收集。CI workflow、selector、bounded_process/process_tree均未改。没有宣称所有非unit自动进入现有CI；它们仍须适用的独立大节点验收。
- daily共享180秒总deadline，显式full/FAST仍600秒；stdout4MiB/stderr512KiB加最多1探测字节，超限125/超时124/真实失败码不转绿。
- 复用既有_bounded_process屏障与OS树所有权，管道读写和关闭在同一生命周期，清理有2.5秒余量。启动、transport和cleanup异常通过dispatch非零；独立注入cleanup错误验证保留进度及notes且返回1。
- 子进程Git checkout上下文从env副本去掉，保留用户Git设置；TEMP/TMP/TMPDIR/SQLITE_TMPDIR均指独占scratch。实际venv→孙进程锁文件超时已在本轮PASS，返回前可删除scratch；实际exit7、双管超限均保留RED和进度。
- 独立额外cap/orphan探针先原子发布真实孙进程PID，孙进程使用DEVNULL而不继承管道；stdout超限返回125且孙进程已死，避免用管道EOF掩盖泄漏。

## 实测与证据

独立首轮12项10P/2F（其中1仓库flake、1独审harness时序错误），进程27.131秒；只重跑两条后2P/7.323秒。五源码SHA前后稳定，见targeted.json及rerun.json；完整trace/XML保留。owner交付40P/22.55秒、获批宿主真实Git30P/37.73秒日志已核收据，本独审未重复其全套或实际Gitpush。

两个owned outer PID终态均不可见；.c3pgir/.c3pgir2已清理。未改任何生产/测试源码、配置、ACL、标签、hook或其他WIP。先前P1历史frozen recipe与P2旧sections适配器问题另归各owner；daily deferral不算解决。

## 绑定

- `tools/pre_push_gate.py`：交付 raw SHA `4175973f5bfd2f727fdff54567f9f4361d5834bfe7c47bcbdc735e64148fc538`；当前 raw SHA `4175973f5bfd2f727fdff54567f9f4361d5834bfe7c47bcbdc735e64148fc538`
- `tests/unit/test_pre_push_gate.py`：交付 raw SHA `624d413e16236550188731feb4b6cb8b2673dbb578d9b2f3d67959490d065d96`；当前 raw SHA `624d413e16236550188731feb4b6cb8b2673dbb578d9b2f3d67959490d065d96`
- `tests/unit/test_pre_push_process_cleanup.py`：交付 raw SHA `d7a2d0bd5d18514280d48abf5a1100f95c1c9b81e9738deeb0b5bb5584000896`；当前 raw SHA `d7a2d0bd5d18514280d48abf5a1100f95c1c9b81e9738deeb0b5bb5584000896`
- `tests/unit/test_pre_push_temp_scope.py`：交付 raw SHA `ccf736630701507b431ba9e933f2189e3133c23977301d1adf926e0b1e88b7d3`；当前 raw SHA `ccf736630701507b431ba9e933f2189e3133c23977301d1adf926e0b1e88b7d3`
- `tests/unit/test_daily_push_policy.py`：交付 raw SHA `931871fea16df19129d972f5a87b09df92b95bf111f04201ce18a71163642efc`；当前 raw SHA `931871fea16df19129d972f5a87b09df92b95bf111f04201ce18a71163642efc`

本报告待ROOT的新test修复SHA与单例复核补充后闭环；并不签整次push或CI绿。
